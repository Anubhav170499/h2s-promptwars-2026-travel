# TravelPilot – Destination Discovery & Cultural Experiences

AI-powered travel planning app built for **Hack2Skill Google PromptWars Indore 2026**. Users describe their travel preferences and the system generates tailored itineraries, cultural experience lists, packing checklists, budget feasibility checks, and activity substitutions — all powered by **Gemini 2.5 Flash**.

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python · FastAPI · Pydantic v2 · google-genai SDK |
| Frontend | Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 |
| AI | Gemini 2.5 Flash (structured JSON output) |
| Auth | Firebase Auth (optional Google Sign-In, guest-first) |
| Persistence | In-memory (default) · Firestore (production) |
| Deploy | Cloud Run · Secret Manager |

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
# Create .env with at minimum:
#   GEMINI_API_KEY=<your-key>
python main.py                                    # runs on :8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                                       # runs on :3000
```

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | Yes | Gemini API key |
| `ALLOWED_ORIGINS` | No | CORS origins (default `http://localhost:3000`) |
| `FIREBASE_PROJECT_ID` | No | Enables Firebase auth verification |
| `USE_FIRESTORE` | No | `true` to use Firestore instead of in-memory storage |

### Tests

```bash
cd backend && .venv\Scripts\activate
ruff check .
python -m pytest
cd ../frontend && npm run build
```

## Project Structure

```
backend/
  travelpilot/          # FastAPI core package
    api.py              # Routes & middleware
    service.py          # Orchestration layer
    gemini.py           # Gemini API adapter
    adaptive.py         # Itinerary adaptation engine
    models.py           # Pydantic request/response schemas
    repository.py       # Persistence (in-memory / Firestore)
    auth.py             # Firebase token verification
    fallback.py         # Deterministic fallback generators
    config.py           # Environment configuration
  main.py               # Entrypoint
frontend/
  src/app/page.tsx      # Main travel planning UI
  src/lib/api.ts        # Typed API client
tests/
  test_api.py           # Backend integration tests
  conftest.py           # Test fixtures & Gemini mocks
```

## Evaluator Login

No login required — the app is **guest-first**. All features are accessible without signing in.
