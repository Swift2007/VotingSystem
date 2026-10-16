import { refreshIcons } from "../shared/icons.js";
import { requireAuth } from "../shared/session.js";

// Signed-out visitors bounce to sign-in; sign-out links clear the token.
requireAuth();

// Verify Receipt: format check + demo lookup. The real check runs
// server-side against the blockchain; this page only demos the states.
refreshIcons();
window.addEventListener("load", refreshIcons, { once: true });

// Demo receipts (stand-ins until the API exists).
const KNOWN = {
  "VC7QK493X22H8P": "Sports Captain · voted 28 Apr 2026",
  "VC2M8P44AB9QWE": "Student Council 2026 · voted today · counted at close",
};

const form = document.querySelector("#verify-form");
const input = document.querySelector("#receipt-code");
const hint = document.querySelector("#code-hint");
const submitButton = form?.querySelector('[type="submit"]');
const resultOk = document.querySelector("#result-ok");
const resultBad = document.querySelector("#result-bad");
const resultElection = document.querySelector("#result-election");

function normalize(value) {
  return value.toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function clearResults() {
  if (resultOk) resultOk.hidden = true;
  if (resultBad) resultBad.hidden = true;
  input?.removeAttribute("aria-invalid");
  if (hint) {
    hint.textContent = "Codes look like VC · XXXX · XXXX · XXXX";
    hint.classList.add("field-note");
  }
}

// Prefill when coming from My Receipts (never via URL).
try {
  const saved = window.sessionStorage.getItem("votex-verify-code");
  if (saved && input && !input.value) {
    input.value = saved;
    window.sessionStorage.removeItem("votex-verify-code");
  }
} catch {
  // Storage unavailable — manual entry still works.
}

document.querySelector("[data-fill]")?.addEventListener("click", (event) => {
  const button = event.currentTarget;
  if (button instanceof HTMLElement && input) {
    input.value = button.dataset.fill ?? "";
    input.focus();
    clearResults();
  }
});

input?.addEventListener("input", clearResults);

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form || !submitButton || !input || submitButton.disabled) return;
  clearResults();

  const code = normalize(input.value);
  if (!/^VC[A-Z0-9]{6,}$/.test(code)) {
    input.setAttribute("aria-invalid", "true");
    if (hint) {
      hint.textContent = "Enter the full code from your receipt.";
      hint.classList.remove("field-note");
    }
    input.focus();
    return;
  }

  // Honest pending state. Never claim validity before the API confirms.
  submitButton.disabled = true;
  const originalLabel = submitButton.textContent;
  submitButton.textContent = "Verifying…";

  window.setTimeout(() => {
    submitButton.disabled = false;
    submitButton.textContent = originalLabel;
    const election = KNOWN[code];
    if (election) {
      if (resultElection) resultElection.textContent = election;
      if (resultOk) resultOk.hidden = false;
    } else {
      if (resultBad) resultBad.hidden = false;
    }
  }, 800);
});
