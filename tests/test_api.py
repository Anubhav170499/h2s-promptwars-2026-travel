from fastapi.testclient import TestClient


def test_security_headers(client: TestClient):
    """Verify that required API security headers are included in all responses."""
    response = client.get("/api/diagnostic-questions")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Strict-Transport-Security" in response.headers


def test_get_diagnostic_questions(client: TestClient):
    """Verify endpoint to fetch standard baseline diagnostic questions."""
    response = client.get("/api/diagnostic-questions")
    assert response.status_code == 200
    questions = response.json()
    assert len(questions) >= 3
    assert questions[0]["id"] == "q1"
    assert "question" in questions[0]
    assert "options" in questions[0]


def test_session_initialization_flow(client: TestClient):
    """Verify complete flow of session initialization, diagnostic evaluation, and GenAI matching."""
    payload = {
        "preferences": {
            "destination": "Kyoto",
            "travel_style": "Cultural Immersion",
            "cultural_interests": ["Traditional Arts", "Zen Gardens"],
            "budget_tier": "Mid-range",
            "budget_limit": 1000.0,
            "duration_days": 3,
            "excluded_factors": ["hiking"],
        },
        "diagnostic_answers": [
            {
                "question_id": "q1",
                "user_answer": "A gentle bow or polite handshake, avoiding prolonged intense eye contact",
                "confidence": 5,
            },
            {
                "question_id": "q2",
                "user_answer": "Sticking your chopsticks vertically into a bowl of rice",
                "confidence": 4,
            },
            {
                "question_id": "q3",
                "user_answer": "Shoulders and knees must be fully covered, and shoes removed before entering",
                "confidence": 5,
            },
        ],
    }

    # 1. Initialize session as Guest (no Auth header)
    response = client.post("/api/session/init", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["session_id"].startswith("tp_")
    assert len(data["session_id"]) == 17  # tp_ + 14 hex chars
    assert data["owner_id"] == "guest"
    assert data["adaptation"]["challenge_level"] == "Advanced"
    assert "Why this step:" in data["adaptation"]["reasoning"]

    # Check itinerary and checklist structure from mock
    assert data["itinerary"]["destination"] == "Kyoto"
    assert len(data["itinerary"]["daily_plans"]) >= 1
    assert data["budget_feasibility"]["is_feasible"] is True
    assert len(data["checklist"]) >= 1


def test_get_session_by_id(client: TestClient):
    """Verify session fetching and owner security checks."""
    payload = {
        "preferences": {
            "destination": "Rome",
            "travel_style": "Historical",
            "cultural_interests": ["Archeology"],
            "budget_tier": "Budget",
            "budget_limit": 500.0,
            "duration_days": 2,
            "excluded_factors": [],
        },
        "diagnostic_answers": [
            {"question_id": "q1", "user_answer": "Incorrect Option", "confidence": 1}
        ],
    }
    init_resp = client.post("/api/session/init", json=payload)
    session_id = init_resp.json()["session_id"]

    # Fetch session
    fetch_resp = client.get(f"/api/session/{session_id}")
    assert fetch_resp.status_code == 200
    assert fetch_resp.json()["session_id"] == session_id

    # Try fetching with invalid session id pattern
    invalid_fetch = client.get("/api/session/tp_invalidid123")
    assert invalid_fetch.status_code == 404


def test_activity_substitution(client: TestClient):
    """Verify adaptive engine substitution when requested due to constraints like weather."""
    payload = {
        "preferences": {
            "destination": "Tokyo",
            "travel_style": "Urban",
            "cultural_interests": ["Tech", "Anime"],
            "budget_tier": "Mid-range",
            "budget_limit": 1000.0,
            "duration_days": 3,
            "excluded_factors": [],
        },
        "diagnostic_answers": [
            {
                "question_id": "q1",
                "user_answer": "A gentle bow or polite handshake, avoiding prolonged intense eye contact",
                "confidence": 5,
            }
        ],
    }
    init_resp = client.post("/api/session/init", json=payload)
    session_data = init_resp.json()
    session_id = session_data["session_id"]

    # Find original activity name
    original_act_name = session_data["itinerary"]["daily_plans"][0]["activities"][0][
        "name"
    ]

    # Request substitution due to rain/weather
    sub_payload = {
        "day_number": 1,
        "activity_name": original_act_name,
        "reason_for_substitution": "heavy rain and bad weather",
    }

    sub_resp = client.post(f"/api/session/{session_id}/substitute", json=sub_payload)
    assert sub_resp.status_code == 200
    updated_session = sub_resp.json()

    # Check that original activity is replaced
    new_activities = updated_session["itinerary"]["daily_plans"][0]["activities"]
    assert any(
        act["name"] == "Indoor Cultural Heritage Museum & Tea Tasting"
        for act in new_activities
    )
    assert not any(act["name"] == original_act_name for act in new_activities)
    assert (
        "Why this changed: System swapped"
        in updated_session["itinerary"]["adaptation_reasoning"]
    )


def test_invalid_requests_and_safety_checks(client: TestClient):
    """Verify validation boundary violations and invalid payloads are rejected."""
    # 1. Invalid duration ge/le bounds
    payload_invalid_days = {
        "preferences": {
            "destination": "Kyoto",
            "travel_style": "Cultural",
            "cultural_interests": ["Food"],
            "budget_tier": "Mid-range",
            "budget_limit": 500.0,
            "duration_days": 20,  # Max is 14
            "excluded_factors": [],
        },
        "diagnostic_answers": [],
    }
    resp = client.post("/api/session/init", json=payload_invalid_days)
    assert resp.status_code == 422  # Unprocessable Entity

    # 2. Invalid budget ge/le bounds
    payload_invalid_budget = {
        "preferences": {
            "destination": "Kyoto",
            "travel_style": "Cultural",
            "cultural_interests": ["Food"],
            "budget_tier": "Mid-range",
            "budget_limit": 5.0,  # Min is 10.0
            "duration_days": 3,
            "excluded_factors": [],
        },
        "diagnostic_answers": [],
    }
    resp = client.post("/api/session/init", json=payload_invalid_budget)
    assert resp.status_code == 422


def test_root_endpoint(client: TestClient):
    """Verify that the root endpoint '/' returns a healthy status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "TravelPilot API"

    # Verify that HEAD request to '/' also returns 200 OK
    head_response = client.head("/")
    assert head_response.status_code == 200


def test_session_id_validation(client: TestClient):
    """Verify that invalid session ID formats return a 404 Not Found error early."""
    # 1. Incorrect length (short)
    response = client.get("/api/session/tp_abcdef123")
    assert response.status_code == 404

    # 2. Missing prefix
    response = client.get("/api/session/xp_abcdef12345678")
    assert response.status_code == 404

    # 3. Non-hex characters
    response = client.get("/api/session/tp_abcdef1234567g")
    assert response.status_code == 404

    # 4. Substitute endpoint with invalid ID
    response = client.post(
        "/api/session/tp_short/substitute",
        json={
            "day_number": 1,
            "activity_name": "Test",
            "reason_for_substitution": "test reason",
        },
    )
    assert response.status_code == 404

    # 5. Checklist toggle endpoint with invalid ID
    response = client.post(
        "/api/session/tp_nonhex1234567g/checklist/toggle?task_name=Test&is_completed=true"
    )
    assert response.status_code == 404


def test_dynamic_diagnostic_questions(client: TestClient):
    """Verify that destination-specific diagnostic questions are generated and cached securely."""
    response = client.get("/api/diagnostic-questions?destination=Paris")
    assert response.status_code == 200
    questions = response.json()

    # Should return exactly 3 questions
    assert len(questions) == 3

    # Each question ID should be prefixed with a group ID (format: q1:qg_<14 hex chars>)
    for q in questions:
        assert ":" in q["id"], f"Question ID should contain group prefix: {q['id']}"
        base_id, group_id = q["id"].split(":", 1)
        assert base_id in ("q1", "q2", "q3")
        assert group_id.startswith("qg_")
        assert len(group_id) == 17  # qg_ + 14 hex chars

    # correct_option should be stripped (empty string) for client-side security
    for q in questions:
        assert q["correct_option"] == "", "correct_option must not be sent to client"

    # Questions should have proper structure
    for q in questions:
        assert "question" in q
        assert "options" in q
        assert len(q["options"]) == 3
        assert "topic" in q


def test_dynamic_questions_end_to_end_flow(client: TestClient):
    """Verify full flow: fetch dynamic questions, submit answers, and initialize session."""
    # Step 1: Fetch destination-specific questions
    q_response = client.get("/api/diagnostic-questions?destination=Paris")
    assert q_response.status_code == 200
    questions = q_response.json()
    assert len(questions) == 3

    # Step 2: Submit answers using the prefixed question IDs
    payload = {
        "preferences": {
            "destination": "Paris",
            "travel_style": "Cultural Immersion",
            "cultural_interests": ["Art", "History"],
            "budget_tier": "Mid-range",
            "budget_limit": 1200.0,
            "duration_days": 3,
            "excluded_factors": [],
        },
        "diagnostic_answers": [
            {
                "question_id": questions[0]["id"],
                "user_answer": questions[0]["options"][0],
                "confidence": 5,
            },
            {
                "question_id": questions[1]["id"],
                "user_answer": questions[1]["options"][0],
                "confidence": 4,
            },
            {
                "question_id": questions[2]["id"],
                "user_answer": questions[2]["options"][0],
                "confidence": 5,
            },
        ],
    }

    response = client.post("/api/session/init", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["session_id"].startswith("tp_")
    assert "adaptation" in data
    assert "Why this step:" in data["adaptation"]["reasoning"]
    assert data["itinerary"]["destination"] == "Paris"


def test_default_questions_backward_compatible(client: TestClient):
    """Verify that fetching questions without destination returns the original defaults."""
    response = client.get("/api/diagnostic-questions")
    assert response.status_code == 200
    questions = response.json()
    assert len(questions) >= 3
    assert questions[0]["id"] == "q1"
    # Default questions should include correct_option (non-empty)
    assert questions[0]["correct_option"] != ""

