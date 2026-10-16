// Email OTP verification (step 2). Input handling + honest pending states.
// FUTURE BACKEND: replace the demo setTimeout in the submit handler with
// POST /auth/verify-email { code } — on 200 go to sign-up-done.html,
// on 401/422 show errorBox + mark inputs invalid (same pattern as below).
// No codes or passwords are logged here.
const form = document.querySelector("#verify-form");
const inputs = [...document.querySelectorAll(".otp-input")];
const submitButton = form?.querySelector('[type="submit"]');
const errorBox = document.querySelector("#verify-error");
const noteBox = document.querySelector("#verify-note");
const resendButton = document.querySelector("#resend-button");
const resendTimer = document.querySelector("#resend-timer");
const emailSlot = document.querySelector("#verify-email");

const RESEND_SECONDS = 30;
let remaining = RESEND_SECONDS;
let timerId = 0;

// Show the address typed on the previous step, if available (email only).
try {
  const saved = window.sessionStorage.getItem("votex-email");
  if (saved && emailSlot) emailSlot.textContent = saved;
} catch {
  // Storage unavailable — the generic label already covers it.
}

function code() {
  return inputs.map((input) => input.value).join("");
}

function refreshSubmit() {
  if (submitButton) submitButton.disabled = code().length !== inputs.length;
}

function clearStatus() {
  if (errorBox) errorBox.hidden = true;
  if (noteBox) {
    noteBox.hidden = true;
    noteBox.textContent = "";
  }
  inputs.forEach((input) => input.removeAttribute("aria-invalid"));
}

inputs.forEach((input, index) => {
  input.addEventListener("input", () => {
    input.value = input.value.replace(/\D/g, "").slice(0, 1);
    clearStatus();
    if (input.value && index < inputs.length - 1) inputs[index + 1]?.focus();
    refreshSubmit();
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Backspace" && !input.value && index > 0) {
      inputs[index - 1]?.focus();
    }
  });

  input.addEventListener("paste", (event) => {
    event.preventDefault();
    const digits = (event.clipboardData?.getData("text") ?? "").replace(/\D/g, "").slice(0, inputs.length);
    if (!digits) return;
    digits.split("").forEach((digit, offset) => {
      const target = inputs[index + offset];
      if (target) target.value = digit;
    });
    const next = inputs[Math.min(index + digits.length, inputs.length - 1)];
    next?.focus();
    clearStatus();
    refreshSubmit();
  });
});

function tick() {
  remaining -= 1;
  if (remaining <= 0) {
    window.clearInterval(timerId);
    if (resendButton) {
      resendButton.disabled = false;
      resendButton.innerHTML = "Resend code";
    }
    return;
  }
  if (resendTimer) resendTimer.textContent = `0:${String(remaining).padStart(2, "0")}`;
}

function startCooldown() {
  remaining = RESEND_SECONDS;
  if (resendButton) {
    resendButton.disabled = true;
    resendButton.innerHTML = `Resend in <span id="resend-timer">0:${RESEND_SECONDS}</span>`;
  }
  window.clearInterval(timerId);
  timerId = window.setInterval(tick, 1000);
}

resendButton?.addEventListener("click", () => {
  if (resendButton.disabled) return;
  startCooldown();
  clearStatus();
  if (noteBox) {
    noteBox.hidden = false;
    noteBox.textContent = "A new code is on its way (demo — no email is actually sent yet).";
  }
  inputs[0]?.focus();
});

startCooldown();
(window.__spaCleanups ??= []).push(() => window.clearInterval(timerId));

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form || !submitButton || submitButton.disabled) return;

  // Honest pending state. Never claim verification before the API confirms.
  // Demo stand-in until POST /auth/verify-email exists: always shows the
  // error state. Real success: window.location.assign("./sign-up-done.html").
  submitButton.disabled = true;
  const originalLabel = submitButton.textContent;
  submitButton.textContent = "Verifying…";

  window.setTimeout(() => {
    submitButton.disabled = false;
    submitButton.textContent = originalLabel;
    refreshSubmit();
    if (errorBox) errorBox.hidden = false;
    inputs.forEach((input) => input.setAttribute("aria-invalid", "true"));
    inputs[0]?.focus();
  }, 800);
});
