# Frontend Agent Prompt — Landing Page and Dashboard (from Google Stitch)

> **How to use:** After the Stitch designs are ready, export them (HTML/CSS code and screenshots) into `frontend/design/stitch/`. Then give this whole file to the Frontend agent as its task instructions.

---

## 1. Your Role

You are the **Frontend agent** for the *Blockchain Online Voting System for Student Council* (working name: **VoteChain**, placeholder; keep the name in one config constant so it can be changed easily).

Your job is to turn the Google Stitch designs into a clean, responsive, accessible frontend using **HTML5, CSS3 + Tailwind CSS and vanilla JavaScript**. Start with the **landing page**, then build the **dashboards**.

Work **only inside `frontend/`** and `docs/` (for notes). Do not touch `backend/`.

## 2. Read First (in this order)

1. `docs/simplified.md` — what the system does, roles, and structure
2. `docs/decisions.md` — decisions made so far
3. `docs/api.md` — API contract (if it doesn't exist yet, use mock data, see Section 7)
4. `frontend/design/stitch/` — Stitch exports and screenshots (**the visual source of truth**)

If something is unclear, write the question in `docs/decisions.md` under "Open Questions". Don't guess.

## 3. Design Direction

**Minimalistic, calm, trustworthy.** Lots of whitespace, thin 1px borders, soft rounded corners, very subtle shadows. No gradients, no neon, no bright saturated colors.

### Color tokens (define once in `tailwind.config.js`, never hard-code hex elsewhere)

| Token | Hex | Use |
|---|---|---|
| `soft-white` | `#F8F8F6` | Page background (never pure bright white) |
| `card` | `#FDFDFC` | Cards and panels |
| `ink` | `#3F3F46` | Primary text |
| `dove` | `#8A8A8E` | Secondary text, icons |
| `line` | `#E4E4E1` | Borders and dividers |
| `sky-soft` | `#8EC5E8` | Highlights, tags, chart fills |
| `sky-deep` | `#2F78B0` | Primary buttons, links (meets contrast for white text) |
| `ok` / `warn` | muted green / muted amber | Status badges ("Open", "Upcoming"); "Closed" uses `dove` |

If Stitch's exported values differ slightly, **Stitch wins**: update the tokens to match and note it in `docs/decisions.md`.

### Type and spacing
- Font: Inter (or the font Stitch used). Clear hierarchy: one H1 per page.
- Radius: 12px cards, 8px inputs and buttons.
- Spacing scale: Tailwind defaults; generous padding (sections 80–120px vertical on desktop).

## 4. Screens to Build (in this order)

**Phase A — Landing page** (`frontend/index.html`)
- Nav: logo, How it works, Features, Security, **Sign in** button
- Hero: headline, subtext, primary "Sign in to vote", secondary "How it works", dashboard preview image
- How it works: 3 steps (Sign in → Vote once → Verify with receipt)
- Feature grid: one vote per student, private ballots, tamper-evident record, receipt verification, instant results
- Trust/security note, footer

**Phase B — Student area** (`frontend/pages/`)
- `login.html`
- `dashboard.html` — summary cards, election cards with status badge and "Vote now", recent receipts
- `elections.html` and `ballot.html` — candidate cards, radio selection, review-and-confirm step, closing countdown
- `receipt.html` — success state, copyable receipt code
- `verify-receipt.html`
- `results.html` — winner card, simple bar chart per candidate

**Phase C — Admin area** (`frontend/pages/admin/`)
- `dashboard.html` — turnout stats, turnout line chart, elections table, audit log list
- `elections-manage.html`, `candidates-manage.html`, `voters-manage.html`

Shared pieces (sidebar, top bar, status badge, stat card, button, table) must be **reusable components** (partial HTML files or JS template functions), not copy-pasted.

## 5. Technical Rules

- **Tailwind CSS** build via `package.json` script; output to `src/css/output.css`. Don't use the CDN build for the final version.
- Plain **HTML + JS modules**. No framework unless `docs/decisions.md` says otherwise.
- Folder layout:
  ```
  frontend/
  ├── index.html
  ├── pages/ (+ admin/)
  ├── components/        # sidebar, topbar, badge, stat-card, etc.
  ├── src/
  │   ├── js/            # api.js (API client), auth.js, page scripts
  │   └── css/           # input.css + generated output.css
  ├── assets/            # logo, icons, images
  ├── design/stitch/     # Stitch exports (read-only reference)
  ├── tailwind.config.js
  └── package.json
  ```
- **Responsive:** mobile-first. Test at 375px, 768px, 1280px. The sidebar collapses to a menu button on mobile. No horizontal scrolling.
- **Accessibility:** semantic HTML, one `h1` per page, labelled form controls, visible focus rings, keyboard navigation, alt text, contrast at least 4.5:1 for body text, `prefers-reduced-motion` respected.
- **Performance:** optimize images, no unused libraries, lazy-load below-the-fold images.
- Charts: lightweight (e.g. Chart.js) or hand-built SVG. Use `sky-soft` and `dove`, no rainbow palettes.

## 6. Hard Rules for the Voting Product (do not break)

1. **The UI never decides security.** Show/hide is cosmetic. All permission, eligibility, one-vote and election-window checks are enforced by the backend. The frontend only reflects what the API returns.
2. **Never store the voter's choice** in `localStorage`, `sessionStorage`, cookies, URLs or console logs. Keep it in memory only until submission, then discard.
3. **Never show "Vote recorded"** until the API confirms it. Show honest states: *submitting*, *pending confirmation*, *recorded*, *failed* with a retry/next-step message.
4. **Disable the submit button after the first click** to prevent double submits. The backend still enforces one vote.
5. **No tokens or passwords in logs or URLs.** No real secrets in code. Use `.env.example` for names only.
6. The receipt page must state clearly that **the receipt does not reveal the choice**.
7. Add a **confirmation step** before the final submit (NFR-07).
8. Don't claim "unhackable" or "100% tamper-proof" anywhere in the copy. Use honest wording such as "tamper-evident" and "verifiable".

## 7. Working Without the Backend

If the API isn't ready, build against a **mock layer**:
- Put mock data in `src/js/mock/` and a single `api.js` that can switch between mock and real via one config flag.
- Mock shapes must follow `docs/api.md`. If the contract is missing, propose endpoints in `docs/api.md` as a PR and wait for the backend owner's approval. Don't invent a hidden contract.
- Remove all mock data before the production build.

## 8. Workflow

1. Create a branch: `feature/frontend-<short-name>`.
2. Build in the Phase order above, one phase per PR. Keep PRs small.
3. Compare your result against the Stitch screenshots at 375 / 768 / 1280 px.
4. Self-check against the checklist below.
5. Commit format: `frontend: short description`.
6. Open a PR. It needs a **human reviewer** and a pass from the Review/Security agent. Don't merge to `main` yourself.

## 9. Done Checklist (every PR)

- [ ] Matches the Stitch design (colors, spacing, type) with no raw hex outside `tailwind.config.js`
- [ ] Works at 375, 768 and 1280 px, with no horizontal scroll
- [ ] Keyboard-navigable, visible focus, labelled inputs, contrast checked
- [ ] Lighthouse: Accessibility 90+, Best Practices 90+, Performance 85+ (landing page)
- [ ] No choice, token or password stored or logged on the client
- [ ] All error, loading and empty states exist (not just the happy path)
- [ ] Reusable components used instead of copy-paste
- [ ] No console errors or warnings
- [ ] Short summary written in the PR: what changed, what's untested, what's open

## 10. End-of-Task Report (required)

When finished, reply with:
1. What you built (pages/components, file list)
2. Where you deviated from Stitch and why
3. Anything blocked on backend or API decisions
4. Open questions added to `docs/decisions.md`
