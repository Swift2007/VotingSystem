// Sign-up step 1 (Details). UI-only: format checks + honest pending state.
// Real register/eligibility checks happen server-side. Nothing secret is logged.
const form = document.querySelector("#signup-form");
const email = document.querySelector("#email");
const regno = document.querySelector("#regno");
const regnoBadge = document.querySelector("#regno-badge");
const regnoHint = document.querySelector("#regno-hint");
const password = document.querySelector("#new-password");
const confirm = document.querySelector("#confirm-password");
const confirmHint = document.querySelector("#confirm-hint");
const emailHint = document.querySelector("#email-hint");
const submitButton = form?.querySelector('[type="submit"]');
const formNote = document.querySelector("#form-note");
const ruleItems = {
  length: document.querySelector('[data-rule="length"]'),
  number: document.querySelector('[data-rule="number"]'),
  symbol: document.querySelector('[data-rule="symbol"]'),
};

const EMAIL_SUFFIX = "@school.edu";
const REGNO_PATTERN = /^SC\/\d{4}\/\d{4}$/i;

function setInvalid(inputEl, hintEl, message) {
  if (!inputEl) return;
  if (!message) {
    inputEl.removeAttribute("aria-invalid");
    if (hintEl && hintEl.id !== "email-hint") {
      hintEl.hidden = true;
      hintEl.textContent = "";
    }
  } else {
    inputEl.setAttribute("aria-invalid", "true");
    if (hintEl) {
      hintEl.hidden = false;
      hintEl.textContent = message;
      hintEl.classList.remove("field-note");
    }
  }
}

function checkPassword(value) {
  const checks = {
    length: value.length >= 10,
    number: /\d/.test(value),
    symbol: /[^A-Za-z0-9]/.test(value),
  };
  for (const [key, passed] of Object.entries(checks)) {
    const li = ruleItems[key];
    if (!li) continue;
    li.classList.toggle("is-met", passed);
    const mark = li.querySelector("span");
    if (mark) mark.textContent = passed ? "✓" : "○";
  }
  return checks;
}

function refreshRegnoBadge() {
  if (!regno || !regnoBadge) return;
  // Format match only drives the demo badge. The real
  // "found on register" check is server-side.
  const matches = REGNO_PATTERN.test(regno.value.trim());
  regnoBadge.classList.toggle("is-visible", matches);
}

document.querySelectorAll(".show-toggle").forEach((button) => {
  button.addEventListener("click", () => {
    const target = document.getElementById(button.dataset.for || "");
    if (!(target instanceof HTMLInputElement)) return;
    const showing = target.type === "text";
    target.type = showing ? "password" : "text";
    button.textContent = showing ? "Show" : "Hide";
    button.setAttribute("aria-pressed", String(!showing));
    target.focus();
  });
});

password?.addEventListener("input", () => checkPassword(password.value));
regno?.addEventListener("input", () => {
  refreshRegnoBadge();
  setInvalid(regno, regnoHint, "");
});

checkPassword(password?.value ?? "");
refreshRegnoBadge();

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form || !submitButton || submitButton.disabled) return;

  if (formNote) {
    formNote.hidden = true;
    formNote.textContent = "";
  }

  let firstBad = null;
  const emailValue = email?.value.trim() ?? "";
  const regnoValue = regno?.value.trim() ?? "";
  const pwValue = password?.value ?? "";

  if (!emailValue.toLowerCase().endsWith(EMAIL_SUFFIX)) {
    setInvalid(email, emailHint, `Use your school email ending in ${EMAIL_SUFFIX}.`);
    firstBad ??= email;
  } else {
    setInvalid(email, null, "");
    if (emailHint) {
      emailHint.textContent = `Must end in ${EMAIL_SUFFIX}`;
      emailHint.classList.add("field-note");
    }
  }

  if (!REGNO_PATTERN.test(regnoValue)) {
    setInvalid(regno, regnoHint, "Use the format SC/2023/0412.");
    firstBad ??= regno;
  } else {
    setInvalid(regno, regnoHint, "");
  }

  const checks = checkPassword(pwValue);
  if (!checks.length || !checks.number || !checks.symbol) {
    password?.setAttribute("aria-invalid", "true");
    firstBad ??= password;
  } else {
    password?.removeAttribute("aria-invalid");
  }

  if (confirm?.value !== pwValue || !pwValue) {
    setInvalid(confirm, confirmHint, "Passwords don’t match yet.");
    firstBad ??= confirm;
  } else {
    setInvalid(confirm, confirmHint, "");
  }

  if (firstBad) {
    firstBad.focus();
    return;
  }

  // Honest pending state. Never claim the account exists before the API confirms.
  submitButton.disabled = true;
  const originalLabel = submitButton.textContent;
  submitButton.textContent = "Checking…";

  window.setTimeout(() => {
    submitButton.disabled = false;
    submitButton.textContent = originalLabel;
    if (formNote) {
      formNote.hidden = false;
      formNote.textContent = "Details look good. Email verification is next (not wired to the backend yet).";
    }
  }, 800);
});
