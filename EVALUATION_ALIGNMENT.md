# Evaluation Alignment

TravelPilot is designed to score strongly against the PromptWars hackathon rubric. This file gives judges a direct map from each criterion to implemented evidence.

## Summary Matrix

| Criterion | Evidence in submission |
| --- | --- |
| Code Quality | [Pending] Modular FastAPI services, typed Pydantic contracts, typed Next.js API client, isolated Gemini and repository layers |
| Security | [Pending] Firebase ID token verification, owner-scoped sessions, strict CORS, bounded request models, safe Gemini prompting, API/frontend security headers |
| Efficiency | [Pending] `gemini-2.5-flash`, deterministic fallback, no vector/runtime-heavy dependencies, bounded Cloud Run deployment, request timeouts |
| Testing | [Pending] Backend tests for core flows, invalid input, auth edge cases, mocked Gemini, and security headers; frontend production build/type check |
| Accessibility | [Pending] Labels, fieldsets, keyboard-focus states, visible text statuses, non-color-only indicators, checklist checkboxes |
| Google Services | [Pending] Gemini, Firebase Auth, Firestore-ready repository, Cloud Run docs, Secret Manager docs, Cloud Logging hooks |
| Problem Alignment | [Pending] Captures travel style preferences & constraints, builds tailored itineraries & cultural experience lists, provides activity substitutions, checks budget feasibility, exposes “why this changed,” persists/resumes sessions |

## Code Quality

*Project code quality specifications to be implemented:*
- `backend/travelpilot/api.py` contains only app creation, middleware, and route registration.
- `backend/travelpilot/models.py` defines all request/response/session/Gemini schemas with Pydantic validation.
- `backend/travelpilot/service.py` orchestrates sessions without embedding Gemini, auth, or persistence details.
- `backend/travelpilot/adaptive.py` contains schedule, budget, weather, and venue substitution adaptation logic and reasoning.
- `backend/travelpilot/gemini.py` isolates structured JSON Gemini calls behind `safe_call`, making generation mockable.
- `backend/travelpilot/repository.py` abstracts in-memory and Firestore persistence.
- `frontend/lib/api.ts` mirrors backend contracts with TypeScript types.

## Security

*Security mechanisms to be implemented:*
- Secrets are read from environment variables or Secret Manager; no server secret is committed.
- Firebase ID tokens are verified server-side when `FIREBASE_PROJECT_ID` is configured.
- Signed-in sessions are owner-scoped; another user receives `403`.
- Guest sessions do not accept client-provided user IDs.
- Request models enforce bounds on preferences, dietary/cultural restrictions, budget ranges, confidence, and session ID shape.
- Gemini prompts explicitly treat traveler input as untrusted and forbid prompt/secret disclosure.
- API responses include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and HTTPS HSTS on Cloud Run.
- Frontend responses disable the Next.js powered-by header and add defensive browser headers.
- CORS is restricted with `ALLOWED_ORIGINS`.

## Efficiency

*Performance & efficiency design patterns to be implemented:*
- `gemini-2.5-flash` is the default model for latency and quota reliability.
- Gemini calls request structured JSON directly, reducing parsing and retry overhead.
- The adaptive engine is deterministic and lightweight; no vector index or large model is loaded in-process.
- The frontend API client uses request IDs and a 60-second timeout to prevent indefinite waits.
- Firestore is optional locally and enabled in Cloud Run with `USE_FIRESTORE=true`.
- Cloud Run deployment settings cap CPU, memory, max instances, and concurrency.

## Testing

Current verification commands:

```bash
# To be set up during environment initialization
.venv/bin/ruff check .
.venv/bin/python -m pytest
npm --prefix frontend run build
```

*Backend tests to cover:*
- Guest session creation and deterministic fallback.
- Mocked Gemini structured responses.
- Itinerary generation, cultural experiences list, activity substitutions, and budget feasibility.
- Schedule adaptations (tight schedule vs leisure) and budget overrun adaptations.
- Invalid flow handling before session initialization.
- Invalid request payloads and unsafe session IDs.
- Signed-in owner scoping.
- API security headers.

*Frontend build to cover:*
- TypeScript contract correctness.
- Next.js App Router compilation.

## Accessibility

*UI accessibility standards to be implemented:*
- The preferences input flow uses a real form, labels, fieldsets, legends, and buttons.
- Keyboard focus is visible and high contrast.
- Itinerary choices and substitution triggers are text buttons, not color-only controls.
- Travel checklist items use clear accessible checkboxes with associated label text.
- Error messages use `role="alert"` where shown.
- Status/loading regions use visible text with animated indicators.
- The UI avoids hidden instructions or marketing-only first screens; the user lands directly in the travel planning workflow.

## Google Services

*GCP features and Google services to be integrated:*
- Gemini API generates itineraries, cultural experiences, substitutions, budget feasibility, and checklists.
- Firebase Auth provides optional Google Sign-In while preserving guest-first reviewer access.
- Firestore persistence is implemented behind `FirestoreSessionRepository`.
- Cloud Run deployment is documented for both backend and frontend.
- Secret Manager is documented for `GEMINI_API_KEY`.
- Cloud Logging hooks are implemented with `ENABLE_CLOUD_LOGGING=true`.

## Problem Statement Alignment

*Destination Discovery & Cultural Experiences Specifications:*
- Capturing daily travel preferences (travel style, cultural interests, budget tier, duration, excluded zones/factors).
- Generating a comprehensive itinerary (daily schedules, destinations, activities).
- Structuring a complete travel packing checklist or destination-specific etiquette task list.
- Providing budget estimates and verifying feasibility.
- Providing substitution options for destinations/activities based on constraints (weather, budget overrun, closure).
- Displaying the adaptation reasoning (e.g. why specific itinerary items or substitutions were chosen).
- Persisting/resuming travel planning sessions.
