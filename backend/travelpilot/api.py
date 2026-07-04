import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List

from travelpilot import config
from travelpilot.models import (
    DiagnosticQuestion, SessionInitRequest, SessionResponse, 
    SubstitutionRequest
)
from travelpilot.auth import get_current_user, verify_session_owner, UserContext
from travelpilot.repository import get_repository
from travelpilot.adaptive import score_diagnostic, adapt_activity_substitution, DIAGNOSTIC_QUESTIONS
from travelpilot.gemini import generate_itinerary, generate_checklist, evaluate_budget_feasibility
from travelpilot.utils import generate_session_id

logger = logging.getLogger(__name__)

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        return response

def create_app() -> FastAPI:
    app = FastAPI(
        title="TravelPilot API",
        description="GenAI-powered adaptive travel and cultural experience recommendations",
        version="1.0.0"
    )

    # CORS configuration
    origins = config.ALLOWED_ORIGINS
    if not origins:
        origins = ["*"]
        
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True if origins != ["*"] else False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Repository reference
    repo = get_repository()

    @app.get("/api/diagnostic-questions", response_model=List[DiagnosticQuestion])
    async def get_questions():
        """Retrieve cultural diagnostic baseline questions."""
        return DIAGNOSTIC_QUESTIONS

    @app.post("/api/session/init", response_model=SessionResponse)
    async def initialize_session(
        payload: SessionInitRequest,
        current_user: UserContext = Depends(get_current_user)
    ):
        """Create a new travel planning session, score diagnostic, generate itinerary and budget check."""
        try:
            # 1. Generate session ID
            session_id = generate_session_id()
            
            # 2. Score diagnostic answers -> Choose Adaptation Path
            adaptation = score_diagnostic(payload.diagnostic_answers)
            
            # 3. Generate tailored itinerary and checklists using Gemini (with deterministic fallbacks)
            itinerary = generate_itinerary(payload.preferences, adaptation)
            checklist = generate_checklist(payload.preferences, adaptation)
            
            # 4. Check budget feasibility
            budget = evaluate_budget_feasibility(payload.preferences, itinerary)
            
            # 5. Build session state
            session_data = {
                "session_id": session_id,
                "owner_id": current_user.user_id,
                "preferences": payload.preferences.model_dump(),
                "adaptation": adaptation.model_dump(),
                "itinerary": itinerary.model_dump(),
                "checklist": [item.model_dump() for item in checklist],
                "budget_feasibility": budget.model_dump()
            }
            
            # 6. Persist session
            repo.save_session(session_id, session_data)
            
            return SessionResponse(**session_data)
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize travel session: {str(e)}"
            )

    @app.get("/api/session/{session_id}", response_model=SessionResponse)
    async def get_session(
        session_id: str,
        current_user: UserContext = Depends(get_current_user)
    ):
        """Retrieve existing session state. Enforces ownership check."""
        session_data = repo.get_session(session_id)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
            
        verify_session_owner(session_data["owner_id"], current_user)
        return SessionResponse(**session_data)

    @app.post("/api/session/{session_id}/substitute", response_model=SessionResponse)
    async def substitute_activity(
        session_id: str,
        payload: SubstitutionRequest,
        current_user: UserContext = Depends(get_current_user)
    ):
        """Substitute a selected activity due to constraints, updating the stored session."""
        session_data = repo.get_session(session_id)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
            
        verify_session_owner(session_data["owner_id"], current_user)
        
        # 1. Run adaptive engine substitution logic
        sub_resp = adapt_activity_substitution(
            day_number=payload.day_number,
            activity_name=payload.activity_name,
            reason=payload.reason_for_substitution,
            challenge_level=session_data["adaptation"]["challenge_level"]
        )
        
        # 2. Modify the stored session's itinerary activities
        itinerary = session_data["itinerary"]
        day_found = False
        activity_substituted = False
        
        for day in itinerary["daily_plans"]:
            if day["day_number"] == payload.day_number:
                day_found = True
                for i, act in enumerate(day["activities"]):
                    if act["name"].strip().lower() == payload.activity_name.strip().lower():
                        day["activities"][i] = sub_resp.new_activity.model_dump()
                        activity_substituted = True
                        break
                break
                
        if not day_found:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Day {payload.day_number} not found in itinerary"
            )
        if not activity_substituted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Activity '{payload.activity_name}' not found on day {payload.day_number}"
            )
            
        # 3. Update the adaptation reasoning with the substitution reasoning
        session_data["itinerary"]["adaptation_reasoning"] = sub_resp.adaptation_reasoning
        
        # 4. Re-evaluate budget feasibility with updated costs
        # Re-parse preferences model
        from travelpilot.models import TravelPreferences, TripItinerary
        prefs = TravelPreferences(**session_data["preferences"])
        updated_itinerary = TripItinerary(**session_data["itinerary"])
        updated_budget = evaluate_budget_feasibility(prefs, updated_itinerary)
        
        session_data["budget_feasibility"] = updated_budget.model_dump()
        
        # 5. Persist the updated session
        repo.save_session(session_id, session_data)
        
        return SessionResponse(**session_data)

    @app.post("/api/session/{session_id}/checklist/toggle", response_model=SessionResponse)
    async def toggle_checklist(
        session_id: str,
        task_name: str,
        is_completed: bool,
        current_user: UserContext = Depends(get_current_user)
    ):
        """Toggle the completion status of a checklist task."""
        session_data = repo.get_session(session_id)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
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
                detail=f"Task '{task_name}' not found in checklist"
            )
            
        repo.save_session(session_id, session_data)
        return SessionResponse(**session_data)

    return app
