// Verify Receipt: format check + GET /receipts/{code} via services/.
// API-first: a 404 means "no ballot matches" (never reveals choices).
// Only when the server is unreachable (status 0 — backend not built yet
// or offline) does the offline demo table below apply, so a real backend
// is never masked by demo data once connected.
import { refreshIcons } from "../shared/icons.js";
import { requireAuth } from "../shared/session.js";
import { normalizeReceiptCode, verifyReceipt } from "../../services/receipt.service.js";

// Signed-out visitors bounce to sign-in; sign-out links clear the token.
requireAuth();

refreshIcons();
window.addEventListener("load", refreshIcons, { once: true });

// Offline stand-ins, used ONLY when the API cannot be reached.
// Kept in sync with the demo button in verify-receipt.html.
const OFFLINE_KNOWN = {
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

function clearResults() {
  if (resultOk) resultOk.hidden = true;
  if (resultBad) resultBad.hidden = true;
  input?.removeAttribute("aria-invalid");
  if (hint) {
    hint.textContent = "Codes look like VC · XXXX · XXXX · XXXX";
    hint.classList.add("field-note");
  }
}

/** Show the valid state with whatever election label the API returned. */
function showValid(data, fallbackLabel) {
  const label =
    data?.election ?? data?.election_title ?? data?.title ?? fallbackLabel ?? "Ballot counted";
  if (resultElection) resultElection.textContent = label;
  if (resultOk) resultOk.hidden = false;
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

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form || !submitButton || !input || submitButton.disabled) return;
  clearResults();

  const code = normalizeReceiptCode(input.value);
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

  try {
    const data = await verifyReceipt(code);
    showValid(data);
  } catch (error) {
    if (error?.status === 404) {
      if (resultBad) resultBad.hidden = false;
    } else if (error?.status === 0) {
      // Backend unreachable: fall back to the offline demo table so the
      // demo code keeps working during development.
      const election = OFFLINE_KNOWN[code];
      if (election) {
        showValid(null, `${election} (offline preview)`);
      } else if (resultBad) {
        resultBad.hidden = false;
      }
    } else if (error?.status === 401) {
      window.location.href = "./sign-in.html";
      return;
    } else {
      input.setAttribute("aria-invalid", "true");
      if (hint) {
        hint.textContent = error?.message || "Verification failed. Try again.";
        hint.classList.remove("field-note");
      }
    }
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = originalLabel;
  }
});
