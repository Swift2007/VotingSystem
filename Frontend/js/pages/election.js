import { refreshIcons } from "../shared/icons.js";
import { requireAuth } from "../shared/session.js";
import { submitBallot } from "../../services/ballot.service.js";

// Signed-out visitors bounce to sign-in; sign-out links clear the token.
requireAuth();

// Election page for the open ballot. Candidates stay hardcoded until
// GET /elections/{id} exists; only the submit below talks to the backend
// (POST /ballots). Picks stay in memory only — never stored — and the
// backend enforces eligibility, one-vote and the election window.
refreshIcons();
window.addEventListener("load", refreshIcons, { once: true });

// --- Closing countdown (today 18:00 local; rolls to tomorrow if passed) ---
const countdownEl = document.querySelector("#countdown");

function closeTime() {
  const close = new Date();
  close.setHours(18, 0, 0, 0);
  if (close.getTime() <= Date.now()) close.setDate(close.getDate() + 1);
  return close.getTime();
}

const CLOSE_AT = closeTime();

function pad(n) {
  return String(n).padStart(2, "0");
}

function tickCountdown() {
  if (!countdownEl) return;
  const left = CLOSE_AT - Date.now();
  if (left <= 0) {
    countdownEl.textContent = "Closed";
    return;
  }
  const h = Math.floor(left / 3_600_000);
  const m = Math.floor((left % 3_600_000) / 60_000);
  const s = Math.floor((left % 60_000) / 1000);
  countdownEl.textContent = `${pad(h)}h ${pad(m)}m ${pad(s)}s`;
}

tickCountdown();
const countdownId = window.setInterval(tickCountdown, 1000);
(window.__spaCleanups ??= []).push(() => window.clearInterval(countdownId));

// --- Manifesto expanders (inside labels, so don't trigger the radio) ---
document.querySelectorAll(".manifesto-toggle").forEach((button) => {
  button.addEventListener("click", (event) => {
    event.preventDefault();
    const card = button.closest(".candidate");
    const text = card?.querySelector(".manifesto");
    if (!text) return;
    const expanded = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!expanded));
    text.hidden = expanded;
    button.textContent = expanded ? "Read manifesto" : "Hide manifesto";
  });
});

// --- Selection state (memory only) ---
const POSITIONS = ["president", "secretary", "treasurer"];
const picks = { president: null, secretary: null, treasurer: null };

// Ballot identity matches election.html ("Student Council Election 2026").
// Once GET /elections exists, derive this from the URL (?id=…) instead.
const ELECTION_ID = "student-council-2026";

// Two-step confirm: first click arms ("Confirm ballot"), second submits.
// Any pick change disarms back to "Review and confirm".
const REVIEW_LABEL = "Review and confirm";
const CONFIRM_LABEL = "Confirm ballot";
let reviewArmed = false;
let submitted = false;

const progressText = document.querySelector("#progress-text");
const progressBar = document.querySelector("#progress-bar");
const reviewButton = document.querySelector("#review-btn");
const reviewNote = document.querySelector("#review-note");

function refreshPosition(name) {
  const scope = name === "treasurer"
    ? document.querySelector("#pos-treasurer")
    : document.querySelector(`#pos-${name}`);
  if (!scope) return;

  scope.querySelectorAll(".candidate, .abstain").forEach((label) => {
    const input = label.querySelector('input[type="radio"]');
    label.classList.toggle("is-selected", Boolean(input?.checked));
  });

  const badge = scope.querySelector("[data-badge]");
  const value = picks[name];
  if (badge) {
    badge.textContent = value ? (value === "Abstain" ? "Abstained" : "Selected") : "Not answered";
    badge.classList.toggle("is-answered", Boolean(value));
  }

  const slot = document.querySelector(`#pick-${name}`);
  if (slot) {
    if (value) {
      slot.textContent = value;
    } else {
      slot.innerHTML = `<a href="#pos-${name}">Choose</a>`;
    }
  }
}

function refreshSummary() {
  const answered = POSITIONS.filter((name) => picks[name]).length;
  if (progressText) progressText.textContent = `${answered} of 3 positions answered`;
  if (progressBar) progressBar.style.width = `${(answered / POSITIONS.length) * 100}%`;
  if (reviewButton) reviewButton.disabled = answered !== POSITIONS.length;
}

/** Reset the confirm step whenever picks change (keeps the action honest). */
function disarmReview() {
  reviewArmed = false;
  if (reviewButton && !submitted) reviewButton.textContent = REVIEW_LABEL;
}

document.querySelectorAll('.position input[type="radio"]').forEach((input) => {
  input.addEventListener("change", () => {
    picks[input.name] = input.value;
    refreshPosition(input.name);
    refreshSummary();
    disarmReview();
    if (reviewNote) {
      reviewNote.hidden = true;
      reviewNote.textContent = "";
    }
  });
});

/** Second click: POST the ballot once (Idempotency-Key makes retries safe). */
async function confirmBallot() {
  if (!reviewButton || !reviewNote || submitted) return;
  reviewButton.disabled = true;
  reviewButton.textContent = "Submitting…";
  try {
    const data = await submitBallot(ELECTION_ID, { ...picks });
    submitted = true;
    // Receipt shape depends on the future backend; accept common variants.
    const receipt = data?.receipt_code ?? data?.receipt ?? data?.code ?? "";
    reviewNote.hidden = false;
    reviewNote.textContent = receipt
      ? `Vote recorded. Your receipt: ${receipt} — keep it to verify counting.`
      : "Vote recorded. Your receipt will appear under My Receipts.";
    reviewButton.textContent = "Ballot submitted";
  } catch (error) {
    if (error?.status === 401) {
      // Stale token: session guard will bounce to sign-in on next boot.
      window.location.href = "./sign-in.html";
      return;
    }
    reviewArmed = false;
    reviewNote.hidden = false;
    if (error?.status === 409) {
      reviewNote.textContent = "This ballot was already recorded — each student votes once.";
    } else if (error?.status === 422) {
      reviewNote.textContent = "Ballot rejected. Re-check your picks and try again.";
    } else if (error?.status === 0) {
      reviewNote.textContent = "Cannot reach the server. Nothing was submitted — try again.";
    } else {
      reviewNote.textContent = error?.message || "Submit failed. Nothing was submitted — try again.";
    }
    refreshSummary(); // re-enables the button when the ballot is complete
    reviewButton.textContent = REVIEW_LABEL;
  }
}

reviewButton?.addEventListener("click", () => {
  if (!reviewButton || reviewButton.disabled || submitted) return;
  if (!reviewArmed) {
    // First click: show the exact picks for review, arm the confirm step.
    reviewArmed = true;
    if (reviewNote) {
      const summary = POSITIONS.map((name) => `${name}: ${picks[name]}`).join(" · ");
      reviewNote.hidden = false;
      reviewNote.textContent = `Review — ${summary}. Click "${CONFIRM_LABEL}" to cast it (cannot be changed).`;
    }
    reviewButton.textContent = CONFIRM_LABEL;
    return;
  }
  void confirmBallot();
});

POSITIONS.forEach(refreshPosition);
refreshSummary();
