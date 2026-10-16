# Connecting the Frontend to the Backend

Agent-to-agent handoff. The frontend (`Frontend/`) is fully wired to a
service layer and expects a running FastAPI backend (`backend/`). Read this
before changing any fetch call or endpoint path.

## 1. How to run both sides

- Backend: `cd backend && uvicorn app.main:app --reload` (see `backend/app/main.py:14`).
  Health check: `GET /health` → `{"status": "ok"}`.
- Frontend: serve `Frontend/` over HTTP (e.g. `python -m http.server` from
  `Frontend/`). Do NOT open via `file://` — `js/shared/router.js` fetches
  page HTML and falls back to full loads.
- API base resolution (`services/config.js`): `<meta name="api-base">` →
  `window.__VOTEX_API_BASE` → same-origin. CORS defaults in
  `backend/app/config.py:57` allow only `http://localhost:5500` and
  `http://127.0.0.1:5500`; serve the frontend from one of those ports or set
  the `CORS_ORIGINS` env var on the backend.
- Rate limiting: 20 req/min per scope (`backend/app/config.py:58`). Login and
  receipt-verify are limited — don't hammer them in loops or tests.

## 2. Where frontend↔backend traffic lives

All backend calls go through `Frontend/services/`. Page scripts must never
`fetch()` the API directly.

| File | Purpose |
|---|---|
| `services/config.js` | `API_BASE`, `apiUrl()`, timeout, token key |
| `services/http.js` | `request()` wrapper: JSON, Bearer from `sessionStorage`, timeout/abort, `ApiError` (`status` + `details`), `Idempotency-Key` support. Never log bodies. |
| `services/auth.service.js` | register / login / me / logout (token in `sessionStorage` only) |
| `services/elections.service.js` | election catalog (paths match backend) |
| `services/ballot.service.js` | ⚠️ path does NOT match backend — see §5 |
| `services/receipt.service.js` | ⚠️ paths do NOT match backend — see §5 |
| `services/results.service.js` | ⚠️ path does NOT match backend — see §5 |
| `js/shared/session.js` | `requireAuth()` (protects app pages), `redirectIfSignedIn()`, `wireSignOut()`, safe `?next=` handling (same-folder `.html` only) |

## 3. Auth (works end-to-end)

Backend: `backend/app/api/auth.py`, schemas `backend/app/schemas/auth.py`.

- `POST /auth/register` ← `register(regno, password)`. Backend's identity field
  is a single `student_id`, so the frontend sends the **registration number as
  `student_id`**; `full_name` is optional server-side (defaults to `""`) and
  the school email is kept client-side only (profile recap + OTP display).
  409 = ID already registered.
- `POST /auth/login` ← `login(id, password)`. 401 uses the generic
  "incorrect" message (never reveal which IDs exist).
- `GET /auth/me` ← `me()`. Returns `{ id, student_id, full_name, role }`;
  the frontend only reads `student_id`.
- `POST /auth/logout` exists server-side but the frontend only clears the
  local token. Call it from `logout()` if server-side revocation matters.

## 4. Endpoints that already match

| Frontend call | Backend route | Notes |
|---|---|---|
| `GET /elections` | `GET /elections` (`backend/app/api/elections.py:32`) | `ElectionOut`: `{ id:int, title, status: upcoming\|open\|closed, opens_at, closes_at, positions: string[], key_fingerprint, tallied, results_published }`. Frontend tolerates extra/missing display fields. |
| `GET /elections/{id}` | `GET /elections/{id}` | `id` is an **int** — the frontend's `"student-council-2026"` slug in `election.js` must become a real int id (e.g. from `?id=`). |
| — (not called yet) | `GET /elections/{id}/candidates` → `[{ id, election_id, full_name, position, manifesto }]` | Election candidates are still hardcoded in `election.html`; render from this when ready. |
| — (not called yet) | `GET /elections/{id}/me` → `{ election_id, eligible, has_voted }` | Never reveals *how* someone voted. Use it to gate the ballot page. |

## 5. Mismatches to fix before connecting (frontend will 404/422 otherwise)

1. **Voting.** Frontend posts `POST /ballots { election_id, selections }`.
   Backend expects `POST /elections/{id}/vote { choices: { "<Position>": <candidateId:int> } }`
   (`backend/app/schemas/vote.py:6`, `backend/app/services/voting.py` enforces
   eligibility + window + one-vote). Success returns
   `{ receipt_code, ballot_hash, status: "pending", message }` — show
   `receipt_code` **once**. Rewrite `ballot.service.js` + the `election.js`
   submit (positions currently send names/abstain strings, backend wants
   candidate-id ints; decide how abstain is encoded first).
2. **Receipt verification.** Frontend does `GET /receipts/{code}`. Backend is
   `POST /receipts/verify { code }` — deliberately POST so codes never land in
   URLs or access logs (`backend/app/api/receipts.py:13`). The frontend's GET
   violates that design; switch to POST and drop the offline demo table once
   connected. Response: `{ valid, message, election_id, election_title,
   ballot_hash, status, block, merkle_proof, counted }`.
3. **`GET /receipts/mine` does not exist.** `my-receipts.js` falls back to demo
   cards. Either add the backend route or persist receipts client-side from
   vote responses (they contain the only full `receipt_code` copy).
4. **Results.** Frontend does `GET /results`. Backend is
   `GET /elections/{id}/results`, 404 until an admin publishes
   (`backend/app/api/elections.py:61`). Rewrite `results.service.js` +
   `results.js` rendering (current code expects a foreign shape; use
   `results_view()` output in `backend/app/services/tally.py`).

## 6. Per-page wiring state (`Frontend/js/pages/`)

- `sign-in.js` — live (`login()`, safe `?next=`, generic 401).
- `sign-up.js` — live `register()`; email verification is UI-only
  (no `POST /auth/verify-email` exists — see future-endpoint comment in
  `verify-email.js`).
- `dashboard.js`, `my-receipts.js`, `results.js` — API-first with static demo
  fallback: they render from the API only on success and keep demo HTML when
  the server is unreachable. After fixing §5, remove or gate the fallbacks.
- `election.js` — two-step Review → Confirm → submit; countdown stays
  client-side (placeholder 18:00 — replace with `closes_at` from the API).
- `verify-receipt.js` — API-first; offline demo table applies on network
  failure only.
- `profile.js` — confirms ID via `me()`; password change is an honest demo
  note (no endpoint).

## 7. Rules (from the README + privacy design)

- Server enforces everything (eligibility, window, one-vote, tally).
  Frontend validation is UX only — the backend revalidates.
- Never store, log, or return a voter→choice link. Tokens in `sessionStorage`
  only (never `localStorage`/URL). Receipt codes prove counting and never
  reveal the choice.
- Render server data with `textContent`/`createElement`, never `innerHTML`.
- Keep generic auth errors; clear the password field on 401.
- Don't add `requireAuth()` to pre-auth pages (`sign-in`, `sign-up`,
  `verify-email`, `sign-up-done`, `index.html`).
