# Blockchain Online Voting System (Student Council) — Simplified Plan

> Simplified from *System Specifications Document v1.0*. This file covers **what we're building**, **the project structure**, and **how we'll build it together with AI agents**.

---

## 1. What We're Building (in plain words)

A website where students vote for student council candidates.

- Students sign in, and the system checks they're allowed to vote.
- Each student gets **one vote per election**.
- Votes are protected so nobody (not even admins) can see who voted for whom.
- Each vote is recorded in a **tamper-evident blockchain**, so nobody can quietly change results.
- After voting, the student gets a **receipt code** to check their vote was counted, without revealing their choice.
- When the election closes, votes are counted automatically and results are published.

**Works on:** phones and computers through the browser (a native mobile app is a later phase).

---

## 2. Who Uses It

| Role | What they do |
|---|---|
| **Student (Voter)** | Sign in, see open elections and candidates, vote once, get a receipt, verify it |
| **Election Admin** | Create elections, add candidates, set the voter list and open/close times, publish results |
| **System Admin** | Keep the server, backups and settings running. Cannot edit votes or see who voted for whom |
| **Auditor / Observer** | Look at audit logs and blockchain evidence without seeing anyone's choice |

---

## 3. Must-Have Features (MVP)

**Critical (the system is useless without these):**
1. **One person, one vote.** Repeated or simultaneous requests must not create a second vote.
2. **Ballot privacy.** Identity and vote choice are stored separately, with no link between them.
3. **Vote protection.** The vote is encrypted or committed before recording. Plaintext choices never go on the blockchain.
4. **Close election.** Votes are rejected after the closing time.
5. **Tally.** Votes are counted correctly after closing.

**High priority:**
- Sign-in and eligibility check
- Election status (upcoming / open / closed) and candidate pages
- Ballot validation (server-side)
- Blockchain recording with a transaction reference
- Receipt code and receipt verification page
- Admin panel for elections, candidates and voters
- Result publishing
- Audit log (no secret votes or passwords in logs)
- Clear error messages (never say "vote recorded" until it truly is)
- Responsive design

---

## 4. Quality Rules (Non-Functional, short version)

| Area | Rule |
|---|---|
| Security | HTTPS only; hashed passwords; role-based admin access |
| Privacy | No voter→choice mapping anywhere (DB, logs, blockchain) |
| Integrity | Admins have no "edit/delete vote" function |
| Performance | Normal pages under 2 s (95th percentile); vote submit may show "pending" |
| Usability | Clear language, confirm step before final submit |
| Accessibility | Keyboard friendly, labelled forms, good contrast |
| Maintainability | Separate UI / business rules / database / blockchain code; secrets outside source code |
| Backups | Regular DB backups; backups never used to rewrite blockchain history |
| Correctness | Counting tested with ties, invalid ballots and zero-vote candidates |

---

## 5. Tech Stack

| Layer | Choice |
|---|---|
| Frontend | HTML5, CSS3 + Tailwind CSS, JavaScript |
| Backend | Python — **FastAPI** (recommended, see Section 9) |
| Database | PostgreSQL |
| Blockchain | Start with a simple custom hash-chain in Python (prototype). Upgrade path: a real network or smart contract later |
| API | REST over HTTPS |
| Version control | Git + GitHub |

---

## 6. How It Works (Data Flow)

```
Student ──► Website ──► Backend API ──► PostgreSQL (users, elections, candidates, eligibility)
                            │
                            ├─► Check: signed in? eligible? election open? already voted?
                            ├─► Validate ballot + enforce one-vote atomically
                            ├─► Protect the vote (encrypt / commitment)
                            ├─► Blockchain layer (record protected vote, keep tx reference)
                            └─► Return receipt code ──► Student
Election closes ──► Tally ──► Publish results
```

---

## 7. Project Structure

```
voting-system/
├── README.md
├── docs/
│   ├── simplified.md              # this file
│   ├── System_Specifications.docx # original spec
│   ├── decisions.md               # every design decision + why (DECISION LOG)
│   ├── api.md                     # endpoint list / contract between frontend & backend
│   └── protocol.md                # vote privacy, receipt and tally design
│
├── backend/
│   ├── app/
│   │   ├── main.py                # app entry point
│   │   ├── config.py              # settings (reads env vars, no secrets in code)
│   │   ├── api/                   # routes: auth, elections, candidates, vote, receipt, admin, results
│   │   ├── services/              # business rules: eligibility, voting, tally, receipts
│   │   ├── models/                # DB tables (users, elections, candidates, eligibility, ballots, receipts, audit)
│   │   ├── schemas/               # request/response shapes
│   │   ├── crypto/                # vote protection, commitments, receipt generation
│   │   ├── blockchain/            # chain logic: blocks, hashing, verify chain
│   │   └── core/                  # security, auth, role checks, logging
│   ├── migrations/                # DB migrations
│   ├── tests/                     # unit + integration tests (tally, one-vote, privacy)
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── pages/                     # login, elections, candidates, ballot, confirmation, receipt-check, results
│   │   └── admin/                 # admin dashboard pages
│   ├── src/
│   │   ├── js/                    # api client, page logic
│   │   └── css/                   # Tailwind input
│   ├── tailwind.config.js
│   └── package.json
│
├── scripts/                       # seed data, test-election generator, run helpers
├── tests/
│   └── e2e/                       # full flow tests (sign in → vote → receipt → results)
├── agents/                        # AI agent instructions (see Section 8)
│   ├── AGENTS.md                  # shared rules every agent must follow
│   ├── backend-agent.md
│   ├── frontend-agent.md
│   ├── blockchain-crypto-agent.md
│   ├── test-qa-agent.md
│   └── review-security-agent.md
├── docker-compose.yml             # app + PostgreSQL for local dev
├── .env.example                   # variable names only, never real secrets
└── .gitignore
```

---

## 8. How We Will Build It (Collaboration + AI Agents)

### 8.1 Principles
1. **Humans decide, agents draft.** AI agents write code, tests and docs. Teammates review and merge. Nothing merges unreviewed.
2. **One owner per area.** Each workstream has a human owner and an AI agent that helps them.
3. **Contract first.** `docs/api.md` is agreed *before* frontend and backend start, so both sides build in parallel.
4. **Decisions go in writing.** Anything decided goes into `docs/decisions.md`, so agents and teammates read the same truth.
5. **Small, frequent merges.** Short branches, small PRs.

### 8.2 Workstreams and agents

| Workstream | Human owner | AI agent | Output |
|---|---|---|---|
| Backend and database | _Teammate A_ | Backend agent | API, DB models, business rules |
| Frontend and UX | _Teammate B_ | Frontend agent | Pages, Tailwind styling, API client |
| Blockchain and vote protocol | _Teammate C_ | Blockchain/Crypto agent | Chain logic, vote protection, receipts, tally |
| Testing and QA | _Shared / rotating_ | Test/QA agent | Tests for all critical requirements |
| Review and security | _Shared / rotating_ | Review/Security agent | PR review, privacy and security checks |

_(Fill in names. If we're only two people, combine workstreams: one takes Backend + Blockchain, the other takes Frontend + QA.)_

### 8.3 Rules every AI agent follows (`agents/AGENTS.md`)
- Read `docs/simplified.md`, `docs/decisions.md` and `docs/api.md` **before** writing code.
- Only touch files in your own workstream folder. Ask before changing another area.
- **Never** log, store or return plaintext vote choices, passwords or tokens.
- **Never** create a link between a voter and their choice.
- All security checks happen **on the server**, not just in the UI.
- No real secrets in code. Use `.env`; update `.env.example` with names only.
- Every feature ships with tests.
- If a requirement is unclear, add a question to `docs/decisions.md` instead of guessing.
- At the end of each task, write a short summary: what changed, what's untested, what's open.

### 8.4 Git workflow
- Branches: `main` (always working) → `dev` → `feature/<area>-<short-name>` (e.g. `feature/backend-vote-endpoint`).
- One feature = one branch = one pull request.
- Commit messages: `area: short description` (e.g. `backend: add one-vote constraint`).
- **Every PR needs:** one human reviewer + a Review/Security agent pass + passing tests.
- Pull `dev` at the start of every work session. Never push directly to `main`.

### 8.5 Day-to-day loop
1. Pick a task from the board (GitHub Projects, or a simple `TODO` table).
2. Create a branch.
3. Give your agent the task plus the files to read (spec, decisions, API contract).
4. Review what the agent wrote. Run it. Fix it. Make sure you understand it.
5. Agent writes tests, then you run them.
6. Open a PR → Review/Security agent comments → teammate reviews → merge.
7. Update `docs/decisions.md` if anything was decided.

### 8.6 Keeping agents from stepping on each other
- Separate folders per workstream (the structure in Section 7 already does this).
- API contract changes go through a PR to `docs/api.md` that both owners approve.
- Short weekly sync (or async message) to compare progress and resolve conflicts.

---

## 9. Decisions to Make Before Coding

These are the open questions from the spec, with a suggested default. Record the final choice in `docs/decisions.md`.

| # | Decision | Suggested default |
|---|---|---|
| 1 | Backend framework | **FastAPI** (API-first, simple, close to Flask) |
| 2 | Blockchain approach | **Custom hash-chain in Python** for the prototype; real network later |
| 3 | Vote privacy and tally protocol | Encrypted/committed ballots + receipt hash; design in `docs/protocol.md` and have it reviewed |
| 4 | Sign-in method | Simple student ID + password for the prototype; school login later |
| 5 | Election rules | One candidate per position, no vote changes after submit, define tie handling |
| 6 | Expected number of voters | Agree on a number for load testing |
| 7 | Hosting, backups, data retention | Local/Docker for now; decide hosting before a real election |
| 8 | Mobile | Responsive website only for v1 |

---

## 10. Build Phases

| Phase | Goal | Done when |
|---|---|---|
| **0. Setup** | Repo, folders, Docker + PostgreSQL, agent files, decisions made | Everyone can run the empty app locally |
| **1. Foundation** | DB models, sign-in, roles, election + candidate pages | A student can sign in and see an open election |
| **2. Voting core** | Ballot validation, one-vote enforcement, vote protection | A student can vote exactly once |
| **3. Blockchain** | Chain records votes, tx reference, receipt + verification | Receipt check works without revealing the choice |
| **4. Admin and results** | Admin panel, close election, tally, publish results | Results match a test dataset |
| **5. Hardening** | Audit log, error handling, accessibility, security and load tests | All acceptance criteria below pass |

---

## 11. Done = These Pass (Acceptance Checklist)

- [ ] Eligible student can sign in and see an open election
- [ ] Ineligible user, or anyone outside the voting window, cannot vote
- [ ] Repeated or concurrent submissions never create a second accepted vote
- [ ] Vote never appears in plaintext on the blockchain or in admin views
- [ ] Receipt can be verified without revealing the candidate
- [ ] Each accepted ballot has a blockchain reference, or a clearly shown pending/failed state
- [ ] Submissions are rejected after close; results follow the configured rules
- [ ] Published totals match an independent test dataset (ties, invalid ballots, zero-vote candidates)
- [ ] Non-admins cannot reach admin functions; admin actions appear in the audit log
- [ ] Works on desktop and mobile browsers; passes security, accessibility and load checks

---

## 12. Honest Limits

Using a blockchain does **not** by itself make voting secure or anonymous. Security depends on identity controls, correct cryptography, hosting and testing. For this project:

- Treat the first version as a **working prototype** that demonstrates the idea.
- Get the privacy/tally design reviewed before any **real** student election.
- Never put student names, IDs or plaintext votes on a public blockchain.