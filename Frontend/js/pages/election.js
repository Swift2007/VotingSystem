import { refreshIcons } from "../shared/icons.js";
import { requireAuth } from "../shared/session.js";

// Signed-out visitors bounce to sign-in; sign-out links clear the token.
requireAuth();

// Ballot page: countdown, card selection, live ballot summary.
// Picks stay in memory only — never stored — and the backend enforces
// eligibility, one-vote and the election window.
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

document.querySelectorAll('.position input[type="radio"]').forEach((input) => {
  input.addEventListener("change", () => {
    picks[input.name] = input.value;
    refreshPosition(input.name);
    refreshSummary();
    if (reviewNote) {
      reviewNote.hidden = true;
      reviewNote.textContent = "";
    }
  });
});

reviewButton?.addEventListener("click", () => {
  if (reviewButton.disabled) return;
  // Review-and-confirm screen is the next build; never claim a vote
  // is recorded before the API confirms it.
  if (reviewNote) {
    reviewNote.hidden = false;
    reviewNote.textContent = "Ballot complete. The review-and-confirm step is next (not built yet) — nothing has been submitted.";
  }
});

POSITIONS.forEach(refreshPosition);
refreshSummary();
