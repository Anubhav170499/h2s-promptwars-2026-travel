import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from travelpilot.api import create_app
from travelpilot.repository import get_repository, InMemoryRepository


@pytest.fixture(autouse=True)
def mock_gemini_client():
    """Mock the Google GenAI client completely in tests to avoid actual API requests."""
    with patch("google.genai.Client") as mock_client_class:
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        # Setup mock response objects
        mock_itinerary_resp = MagicMock()
        mock_itinerary_resp.text = """{
            "destination": "Paris",
            "adaptation_reasoning": "Why this step: System matched beginner orientation.",
            "daily_plans": [
                {
                    "day_number": 1,
                    "theme": "Historical Highlights",
                    "activities": [
                        {
                            "name": "Eiffel Tower Cultural History Stroll",
                            "description": "Walk around Eiffel Tower with a local history guide, reviewing architectural history.",
                            "time_slot": "Morning",
                            "estimated_cost": 25.0,
                            "cultural_significance": "Most famous architectural icon in Paris."
                        }
                    ]
                }
            ]
        }"""

        mock_checklist_resp = MagicMock()
        mock_checklist_resp.text = """{
            "items": [
                {
                    "task": "Review basic French greetings",
                    "category": "Etiquette",
                    "is_completed": false
                }
            ]
        }"""

        mock_budget_resp = MagicMock()
        mock_budget_resp.text = """{
            "is_feasible": true,
            "estimated_total_cost": 25.0,
            "analysis_reason": "Cost of $25.0 is feasible for budget $500.0",
            "saving_tips": ["Use local metro", "Eat local street food"]
        }"""

        mock_diagnostic_resp = MagicMock()
        mock_diagnostic_resp.text = """{
            "questions": [
                {
                    "id": "q1",
                    "question": "When greeting someone in Paris, what is the standard custom?",
                    "options": ["A firm handshake or la bise (cheek kisses) depending on familiarity", "A deep bow from the waist", "A fist bump followed by a chest tap"],
                    "correct_option": "A firm handshake or la bise (cheek kisses) depending on familiarity",
                    "topic": "Greeting & Social Etiquette"
                },
                {
                    "id": "q2",
                    "question": "When dining at a French restaurant, which behavior would be considered rude?",
                    "options": ["Asking the sommelier for wine recommendations", "Placing bread directly on the table rather than using a bread plate", "Rushing through your meal and asking for the check immediately"],
                    "correct_option": "Rushing through your meal and asking for the check immediately",
                    "topic": "Dining & Food Customs"
                },
                {
                    "id": "q3",
                    "question": "What should you do before entering Notre-Dame Cathedral or similar churches in Paris?",
                    "options": ["Ensure shoulders and knees are covered and silence your phone", "Purchase a special visitor pass from a nearby kiosk", "Remove your shoes at the entrance"],
                    "correct_option": "Ensure shoulders and knees are covered and silence your phone",
                    "topic": "Sacred Sites & Dress Code"
                }
            ]
        }"""

        # Make generate_content return appropriate mocked outputs based on input content
        def mock_generate_content(model, contents, config=None):
            if "diagnostic" in contents.lower() or "etiquette diagnostic" in contents.lower():
                return mock_diagnostic_resp
            elif "itinerary" in contents.lower() or "trip" in contents.lower():
                return mock_itinerary_resp
            elif "checklist" in contents.lower():
                return mock_checklist_resp
            elif "budget" in contents.lower():
                return mock_budget_resp
            return mock_itinerary_resp

        from unittest.mock import AsyncMock
        mock_instance.models.generate_content.side_effect = mock_generate_content
        
        mock_instance.aio = MagicMock()
        mock_instance.aio.models = MagicMock()
        mock_instance.aio.models.generate_content = AsyncMock(side_effect=mock_generate_content)
        yield mock_instance


@pytest.fixture(autouse=True)
def clean_repository():
    """Ensure each test runs with a fresh clean repository instance."""
    repo = get_repository()
    if isinstance(repo, InMemoryRepository):
        repo._storage.clear()
        repo._question_cache.clear()
    yield repo


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
