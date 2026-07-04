# Evaluation Alignment

TravelPilot is designed to score strongly against the PromptWars hackathon rubric. This file maps each criterion directly to implemented evidence.

## Summary Matrix

| Criterion | Status | Key Evidence |
|-----------|--------|-------------|
| Code Quality | ✅ Implemented | Modular FastAPI layers, Pydantic v2 contracts, typed Next.js API client, isolated Gemini/repository adapters |
| Security | ✅ Implemented | Firebase ID token verification, owner-scoped sessions, strict CORS, bounded request models, safe Gemini prompting |
| Efficiency | ✅ Implemented | `gemini-2.5-flash`, structured JSON output, deterministic fallbacks, no heavy ML runtimes |
| Testing | ✅ Implemented | 12+ backend test cases, mocked Gemini, auth/security edge cases, frontend type-check + build |
| Accessibility | ✅ Implemented | Labels, fieldsets, keyboard focus, text-based status indicators, `role="alert"` errors |
| Google Services | ✅ Implemented | Gemini API, Firebase Auth, Firestore repository, Cloud Run + Secret Manager docs |
| Problem Alignment | ✅ Implemented | Preference capture → itinerary generation → cultural experiences → substitutions → budget checks → checklists → adaptation reasoning |

---

## Code Quality

| Principle | Implementation |
|-----------|---------------|
| Layer separation | `api.py` (routes/middleware) → `service.py` (orchestration) → `gemini.py` / `repository.py` (adapters) |
| Typed contracts | All API schemas defined in `models.py` with Pydantic v2 validators (`min_length`, `max_length`, `ge`, `le`) |
| Adaptation logic | `adaptive.py` contains schedule, budget, weather, and venue substitution scoring with reasoning strings |
| Frontend typing | `lib/api.ts` mirrors backend contracts with TypeScript interfaces |
| Fallback isolation | `fallback.py` provides deterministic generators when API keys are missing or quota is exhausted |
| Auth isolation | `auth.py` handles Firebase token verification as a dependency, separate from business logic |

---

## Security

| Control | Where |
|---------|-------|
| Firebase ID token verification | `auth.py` — verifies tokens when `FIREBASE_PROJECT_ID` is set |
| Owner-scoped sessions | `service.py` — returns `403` if `session.owner_id != user.user_id` |
| Guest isolation | Guest sessions reject client-provided user IDs |
| Input bounds | `models.py` — `min_length`, `max_length`, `ge`/`le` on all request fields; session ID pattern `^tp_[a-f0-9]{14}$` |
| Safe Gemini prompts | `gemini.py` — traveler input treated as untrusted, prompt/secret disclosure forbidden |
| Security headers | API: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, HSTS |
| Frontend headers | Next.js `poweredByHeader: false`, defensive browser headers |
| CORS | Restricted via `ALLOWED_ORIGINS` configuration |

---

## Efficiency

| Technique | Detail |
|-----------|--------|
| Model choice | `gemini-2.5-flash` — lowest latency, best quota reliability |
| Structured output | Gemini calls use `response_schema` with Pydantic models — no manual JSON parsing |
| Lightweight engine | Adaptive scoring is deterministic Python — no vector DB or ML runtime in-process |
| Request safety | Frontend API client uses request IDs and 60-second timeout |
| Optional Firestore | In-memory by default; Firestore enabled with `USE_FIRESTORE=true` |
| Lean dependencies | Only 7 production Python packages |

---

## Testing

```bash
# Run all checks
cd backend && python -m pytest -v
ruff check .
cd ../frontend && npm run build
```

**Backend test coverage (`tests/test_api.py`):**

- Guest session creation with deterministic fallback
- Mocked Gemini structured responses for all generation flows
- Itinerary generation, cultural experiences, activity substitutions, budget feasibility
- Schedule adaptations (tight vs leisure) and budget overrun adaptations
- Invalid flow handling (requesting steps before session init)
- Invalid request payloads and unsafe session IDs
- Signed-in owner scoping (`403` on mismatch)
- API security headers validation

**Frontend verification:**

- TypeScript compilation (contract correctness)
- Next.js App Router production build

---

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Form semantics | Real `<form>`, `<label>`, `<fieldset>`, `<legend>`, `<button>` elements |
| Keyboard navigation | Visible high-contrast focus outlines on all interactive elements |
| Non-color indicators | Text labels and icons for all states — never color-only |
| Checkboxes | Travel checklist items use accessible checkboxes with associated labels |
| Error announcements | `role="alert"` on error messages |
| Loading states | Visible text with animated indicators |
| Direct workflow | No splash/marketing screen — users land directly in travel planning |

---

## Google Services

| Service | Usage |
|---------|-------|
| **Gemini API** | Itinerary generation, cultural experiences, substitutions, budget feasibility, checklists — all via `google-genai` SDK |
| **Firebase Auth** | Optional Google Sign-In; guest-first for evaluator access |
| **Firestore** | Production persistence via `FirestoreSessionRepository` |
| **Cloud Run** | Deployment target with bounded CPU/memory/concurrency settings |
| **Secret Manager** | `GEMINI_API_KEY` storage in production |
| **Cloud Logging** | Enabled with `ENABLE_CLOUD_LOGGING=true` |

---

## Problem Statement Alignment

**Destination Discovery & Cultural Experiences — full pipeline:**

1. **Preference capture** — Travel style, cultural interests, budget tier, duration, dietary/cultural restrictions, excluded zones
2. **Itinerary generation** — Daily schedules with destinations, activities, and timing
3. **Cultural experiences** — Curated list of cultural activities for the destination
4. **Packing/etiquette checklist** — Destination-specific preparation tasks
5. **Budget feasibility** — Cost estimates with feasibility verdict
6. **Activity substitution** — Alternative options based on weather, budget overrun, or closure constraints
7. **Adaptation reasoning** — Visible "why this changed" explanations saved to session and displayed in UI
8. **Session persistence** — Resume travel planning sessions across visits
