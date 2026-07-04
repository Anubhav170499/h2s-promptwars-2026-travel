import logging
import secrets
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List, Optional

import re
from travelpilot import config
from travelpilot.models import (
    DiagnosticQuestion,
    SessionInitRequest,
    SessionResponse,
    SubstitutionRequest,
)
from travelpilot.auth import get_current_user, UserContext
from travelpilot.repository import get_repository
from travelpilot.service import SessionService
from travelpilot.adaptive import DEFAULT_DIAGNOSTIC_QUESTIONS
from travelpilot.gemini import generate_diagnostic_questions

logger = logging.getLogger(__name__)

SESSION_ID_PATTERN = re.compile(r"^tp_[a-f0-9]{14}$")
QUESTION_GROUP_PATTERN = re.compile(r"^qg_[a-f0-9]{14}$")


def validate_session_id(session_id: str) -> None:
    if not SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )


def generate_question_group_id() -> str:
    """Generate a unique question group ID for caching generated questions."""
    return f"qg_{secrets.token_hex(7)}"


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="TravelPilot API",
        description="GenAI-powered adaptive travel and cultural experience recommendations",
        version="1.0.0",
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

    # Repository and Service reference
    repo = get_repository()
    service = SessionService(repo)

    @app.api_route("/", methods=["GET", "HEAD"])
    async def root():
        """Root endpoint for health checks and service status."""
        return {"status": "healthy", "service": "TravelPilot API", "version": "1.0.0"}

    @app.get("/api/diagnostic-questions", response_model=List[DiagnosticQuestion])
    async def get_questions(
        destination: Optional[str] = Query(
            None, min_length=2, max_length=100,
            description="Target destination for generating culturally relevant questions"
        ),
    ):
        """Retrieve cultural diagnostic baseline questions.

        When a destination is provided, generates destination-specific questions
        via Gemini and caches them server-side for secure grading. The correct_option
        is stripped from the response to prevent client-side cheating.
        When no destination is given, returns default questions (backward compatible).
        """
        if not destination:
            return DEFAULT_DIAGNOSTIC_QUESTIONS

        # Generate destination-specific questions
        questions = await generate_diagnostic_questions(destination)

        # Create a question group ID and cache the full questions (with correct answers)
        group_id = generate_question_group_id()
        cache_data = {
            "destination": destination,
            "questions": [q.model_dump() for q in questions],
        }
        await repo.save_question_cache(group_id, cache_data)

        # Prefix each question ID with the group ID and strip correct_option for the client
        client_questions = []
        for q in questions:
            client_questions.append(
                DiagnosticQuestion(
                    id=f"{q.id}:{group_id}",
                    question=q.question,
                    options=q.options,
                    correct_option="",  # Never send to client
                    topic=q.topic,
                )
            )

        return client_questions

    @app.post("/api/session/init", response_model=SessionResponse)
    async def initialize_session(
        payload: SessionInitRequest,
        current_user: UserContext = Depends(get_current_user),
    ):
        """Create a new travel planning session, score diagnostic, generate itinerary and budget check."""
        return await service.initialize_session(payload, current_user)

    @app.get("/api/session/{session_id}", response_model=SessionResponse)
    async def get_session(
        session_id: str, current_user: UserContext = Depends(get_current_user)
    ):
        """Retrieve existing session state. Enforces ownership check."""
        validate_session_id(session_id)
        return await service.get_session(session_id, current_user)

    @app.post("/api/session/{session_id}/substitute", response_model=SessionResponse)
    async def substitute_activity(
        session_id: str,
        payload: SubstitutionRequest,
        current_user: UserContext = Depends(get_current_user),
    ):
        """Substitute a selected activity due to constraints, updating the stored session."""
        validate_session_id(session_id)
        return await service.substitute_activity(session_id, payload, current_user)

    @app.post(
        "/api/session/{session_id}/checklist/toggle", response_model=SessionResponse
    )
    async def toggle_checklist(
        session_id: str,
        task_name: str,
        is_completed: bool,
        current_user: UserContext = Depends(get_current_user),
    ):
        """Toggle the completion status of a checklist task."""
        validate_session_id(session_id)
        return await service.toggle_checklist_item(
            session_id, task_name, is_completed, current_user
        )

    return app
