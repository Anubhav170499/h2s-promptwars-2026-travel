import logging
import asyncio
from fastapi import HTTPException, status

from travelpilot.models import (
    SessionInitRequest,
    SessionResponse,
    SubstitutionRequest,
    TravelPreferences,
    TripItinerary,
    DiagnosticAnswer,
    DiagnosticQuestion,
)
from travelpilot.repository import SessionRepository
from travelpilot.adaptive import score_diagnostic, adapt_activity_substitution
from travelpilot.gemini import (
    generate_itinerary,
    generate_checklist,
    evaluate_budget_feasibility,
)
from travelpilot.utils import generate_session_id
from travelpilot.auth import UserContext, verify_session_owner

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self, repo: SessionRepository):
        self.repo = repo

    async def initialize_session(
        self, payload: SessionInitRequest, current_user: UserContext
    ) -> SessionResponse:
        """Create a new travel planning session, score diagnostic, generate itinerary and budget check."""
        try:
            # 1. Generate session ID
            session_id = generate_session_id()

            # 2. Extract question group ID from answers (if using dynamic questions)
            #    Dynamic question IDs have format: "q1:qg_<14 hex chars>"
            custom_questions = None
            group_id = None
            stripped_answers = payload.diagnostic_answers

            if payload.diagnostic_answers:
                first_qid = payload.diagnostic_answers[0].question_id
                if ":qg_" in first_qid:
                    # Extract the group ID from the first answer
                    parts = first_qid.split(":", 1)
                    if len(parts) == 2:
                        group_id = parts[1]

                        # Fetch cached questions from repository
                        cache_data = await self.repo.get_question_cache(group_id)
                        if cache_data and "questions" in cache_data:
                            custom_questions = [
                                DiagnosticQuestion(**q) for q in cache_data["questions"]
                            ]
                            logger.info(
                                f"Loaded {len(custom_questions)} cached questions for group {group_id}"
                            )

                        # Strip group prefix from all answer question_ids for scoring
                        stripped_answers = [
                            DiagnosticAnswer(
                                question_id=ans.question_id.split(":", 1)[0],
                                user_answer=ans.user_answer,
                                confidence=ans.confidence,
                            )
                            for ans in payload.diagnostic_answers
                        ]

            # 3. Score diagnostic answers -> Choose Adaptation Path
            adaptation = score_diagnostic(stripped_answers, custom_questions)

            # 4. Clean up question cache after scoring
            if group_id:
                await self.repo.delete_question_cache(group_id)

            # 5. Generate tailored itinerary and checklists using Gemini in parallel
            itinerary, checklist = await asyncio.gather(
                generate_itinerary(payload.preferences, adaptation),
                generate_checklist(payload.preferences, adaptation)
            )

            # 6. Check budget feasibility
            budget = await evaluate_budget_feasibility(payload.preferences, itinerary)

            # 7. Build session state
            session_data = {
                "session_id": session_id,
                "owner_id": current_user.user_id,
                "preferences": payload.preferences.model_dump(),
                "adaptation": adaptation.model_dump(),
                "itinerary": itinerary.model_dump(),
                "checklist": [item.model_dump() for item in checklist],
                "budget_feasibility": budget.model_dump(),
            }

            # 8. Persist session
            await self.repo.save_session(session_id, session_data)
            logger.info(
                f"Successfully initialized and persisted session {session_id} for user {current_user.user_id}"
            )

            return SessionResponse(**session_data)
        except Exception as e:
            logger.error(f"Service failed to initialize session: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize travel session: {str(e)}",
            )

    async def get_session(
        self, session_id: str, current_user: UserContext
    ) -> SessionResponse:
        """Retrieve existing session state. Enforces ownership check."""
        session_data = await self.repo.get_session(session_id)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        verify_session_owner(session_data["owner_id"], current_user)
        return SessionResponse(**session_data)

    async def substitute_activity(
        self, session_id: str, payload: SubstitutionRequest, current_user: UserContext
    ) -> SessionResponse:
        """Substitute a selected activity due to constraints, updating the stored session."""
        session_data = await self.repo.get_session(session_id)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        verify_session_owner(session_data["owner_id"], current_user)

        # 1. Run adaptive engine substitution logic
        sub_resp = adapt_activity_substitution(
            day_number=payload.day_number,
            activity_name=payload.activity_name,
            reason=payload.reason_for_substitution,
            challenge_level=session_data["adaptation"]["challenge_level"],
        )

        # 2. Modify the stored session's itinerary activities
        itinerary = session_data["itinerary"]
        day_found = False
        activity_substituted = False

        for day in itinerary["daily_plans"]:
            if day["day_number"] == payload.day_number:
                day_found = True
                for i, act in enumerate(day["activities"]):
                    if (
                        act["name"].strip().lower()
                        == payload.activity_name.strip().lower()
                    ):
                        day["activities"][i] = sub_resp.new_activity.model_dump()
                        activity_substituted = True
                        break
                break

        if not day_found:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Day {payload.day_number} not found in itinerary",
            )
        if not activity_substituted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Activity '{payload.activity_name}' not found on day {payload.day_number}",
            )

        # 3. Update the adaptation reasoning with the substitution reasoning
        session_data["itinerary"]["adaptation_reasoning"] = (
            sub_resp.adaptation_reasoning
        )

        # 4. Re-evaluate budget feasibility with updated costs
        prefs = TravelPreferences(**session_data["preferences"])
        updated_itinerary = TripItinerary(**session_data["itinerary"])
        updated_budget = await evaluate_budget_feasibility(prefs, updated_itinerary)

        session_data["budget_feasibility"] = updated_budget.model_dump()

        # 5. Persist the updated session
        await self.repo.save_session(session_id, session_data)
        logger.info(
            f"Successfully substituted activity in session {session_id} for user {current_user.user_id}"
        )

        return SessionResponse(**session_data)

    async def toggle_checklist_item(
        self,
        session_id: str,
        task_name: str,
        is_completed: bool,
        current_user: UserContext,
    ) -> SessionResponse:
        """Toggle the completion status of a checklist task."""
        session_data = await self.repo.get_session(session_id)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        verify_session_owner(session_data["owner_id"], current_user)

        # Search and update item
        found = False
        for item in session_data["checklist"]:
            if item["task"].strip().lower() == task_name.strip().lower():
                item["is_completed"] = is_completed
                found = True
                break

        if not found:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task '{task_name}' not found in checklist",
            )

        await self.repo.save_session(session_id, session_data)
        logger.info(
            f"Successfully toggled checklist item in session {session_id} for user {current_user.user_id}"
        )

        return SessionResponse(**session_data)
