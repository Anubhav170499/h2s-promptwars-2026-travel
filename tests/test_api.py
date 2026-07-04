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
            "excluded_factors": ["hiking"]
        },
        "diagnostic_answers": [
            {
                "question_id": "q1",
                "user_answer": "A gentle bow or polite handshake, avoiding prolonged intense eye contact",
                "confidence": 5
            },
            {
                "question_id": "q2",
                "user_answer": "Sticking your chopsticks vertically into a bowl of rice",
                "confidence": 4
            },
            {
                "question_id": "q3",
                "user_answer": "Shoulders and knees must be fully covered, and shoes removed before entering",
                "confidence": 5
            }
        ]
    }
    
    # 1. Initialize session as Guest (no Auth header)
    response = client.post("/api/session/init", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["session_id"].startswith("tp_")
    assert len(data["session_id"]) == 17 # tp_ + 14 hex chars
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
            "excluded_factors": []
        },
        "diagnostic_answers": [
            {
                "question_id": "q1",
                "user_answer": "Incorrect Option",
                "confidence": 1
            }
        ]
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
            "excluded_factors": []
        },
        "diagnostic_answers": [
            {
                "question_id": "q1",
                "user_answer": "A gentle bow or polite handshake, avoiding prolonged intense eye contact",
                "confidence": 5
            }
        ]
    }
    init_resp = client.post("/api/session/init", json=payload)
    session_data = init_resp.json()
    session_id = session_data["session_id"]
    
    # Find original activity name
    original_act_name = session_data["itinerary"]["daily_plans"][0]["activities"][0]["name"]
    
    # Request substitution due to rain/weather
    sub_payload = {
        "day_number": 1,
        "activity_name": original_act_name,
        "reason_for_substitution": "heavy rain and bad weather"
    }
    
    sub_resp = client.post(f"/api/session/{session_id}/substitute", json=sub_payload)
    assert sub_resp.status_code == 200
    updated_session = sub_resp.json()
    
    # Check that original activity is replaced
    new_activities = updated_session["itinerary"]["daily_plans"][0]["activities"]
    assert any(act["name"] == "Indoor Cultural Heritage Museum & Tea Tasting" for act in new_activities)
    assert not any(act["name"] == original_act_name for act in new_activities)
    assert "Why this changed: System swapped" in updated_session["itinerary"]["adaptation_reasoning"]

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
            "duration_days": 20, # Max is 14
            "excluded_factors": []
        },
        "diagnostic_answers": []
    }
    resp = client.post("/api/session/init", json=payload_invalid_days)
    assert resp.status_code == 422 # Unprocessable Entity

    # 2. Invalid budget ge/le bounds
    payload_invalid_budget = {
        "preferences": {
            "destination": "Kyoto",
            "travel_style": "Cultural",
            "cultural_interests": ["Food"],
            "budget_tier": "Mid-range",
            "budget_limit": 5.0, # Min is 10.0
            "duration_days": 3,
            "excluded_factors": []
        },
        "diagnostic_answers": []
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

