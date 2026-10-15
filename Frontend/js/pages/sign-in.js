// Sign-in page logic. UI-only: validation + honest submitting/error states.
// No tokens, passwords, or choices are stored or logged. Backend enforces auth.
const form = document.querySelector("#signin-form");
const identifier = document.querySelector("#identifier");
const password = document.querySelector("#password");
const submitButton = form?.querySelector('[type="submit"]');
const errorBox = document.querySelector("#form-error");
const showToggle = document.querySelector(".show-toggle");

const identifierHint = document.querySelector("#identifier-hint");
const passwordHint = document.querySelector("#password-hint");

function setHint(hintEl, inputEl, message) {
  if (!hintEl || !inputEl) return;
  if (!message) {
    hintEl.hidden = true;
    hintEl.textContent = "";
    inputEl.removeAttribute("aria-invalid");
  } else {
    hintEl.hidden = false;
    hintEl.textContent = message;
    inputEl.setAttribute("aria-invalid", "true");
  }
}

showToggle?.addEventListener("click", () => {
  const showing = password.type === "text";
  password.type = showing ? "password" : "text";
  showToggle.textContent = showing ? "Show" : "Hide";
  showToggle.setAttribute("aria-pressed", String(!showing));
  password.focus();
});

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form || !submitButton) return;
  if (submitButton.disabled) return; // prevent double submit

  const idValue = identifier?.value.trim() ?? "";
  const pwValue = password?.value ?? "";
  let valid = true;

  setHint(identifierHint, identifier, "");
  setHint(passwordHint, password, "");
  if (errorBox) errorBox.hidden = true;

  if (!idValue) {
    setHint(identifierHint, identifier, "Enter your school email or registration number.");
    valid = false;
  }
  if (!pwValue) {
    setHint(passwordHint, password, "Enter your password.");
    valid = false;
  }
  if (!valid) {
    (identifier?.value ? password : identifier)?.focus();
    return;
  }

  // Honest pending state. Real auth happens server-side; this only
  // demonstrates the UI. Never show "signed in" before the API confirms.
  submitButton.disabled = true;
  const originalLabel = submitButton.textContent;
  submitButton.textContent = "Signing in…";

  window.setTimeout(() => {
    // Demo error state (matches design reference). Same generic message
    // for both fields so it doesn't reveal which accounts exist.
    if (errorBox) errorBox.hidden = false;
    submitButton.disabled = false;
    submitButton.textContent = originalLabel;
  }, 800);
});
