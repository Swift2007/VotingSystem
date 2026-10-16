// Sign-up step 1 (Details). Validates locally, then POST /auth/register.
// Backend contract has a single `student_id` field, so the registration
// number is sent as student_id; the school email is kept only for UX
// (profile recap + OTP display) and never sent to the backend.
// On success the backend signs the user in (token stored by the service)
// and the flow continues to verify-email.html.
import { register } from "../../services/auth.service.js";
import { redirectIfSignedIn } from "../shared/session.js";

// Signed-in users don't need a second account.
if (!redirectIfSignedIn()) {
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

  const EMAIL_SUFFIX = "@gmail.com";
  const REGNO_PATTERN = /^BEH\/\d{2}\/\d{2}\/\d{2}$/i;

  /** Mark a field valid/invalid with hint text (email hint keeps its default note). */
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

  /** Live password-rule checklist; returns per-rule pass flags. */
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

  /** Format badge only — real register membership is checked server-side. */
  function refreshRegnoBadge() {
    if (!regno || !regnoBadge) return;
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

  /** Info/status line below the form (textContent only — never user HTML). */
  function note(message, link) {
    if (!formNote) return;
    formNote.textContent = "";
    formNote.hidden = false;
    formNote.append(message);
    if (link) {
      const anchor = document.createElement("a");
      anchor.className = "inline-link";
      anchor.href = link.href;
      anchor.textContent = link.text;
      formNote.append(" ", anchor);
    }
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form || !submitButton || submitButton.disabled) return;

    if (formNote) {
      formNote.hidden = true;
      formNote.textContent = "";
    }

    // --- Local validation (server revalidates everything) ---
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
      setInvalid(regno, regnoHint, "Use the format BEH/01/29/24.");
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

    // --- Real registration. Never claim the account exists first. ---
    submitButton.disabled = true;
    const originalLabel = submitButton.textContent;
    submitButton.textContent = "Creating…";

    try {
      // student_id = registration number (backend's single identity field).
      await register(regnoValue, pwValue);
      try {
        window.sessionStorage.setItem("votex-email", emailValue);
        window.sessionStorage.setItem("votex-regno", regnoValue);
      } catch {
        // Recap convenience only; the session token is what matters.
      }
      window.location.href = "./verify-email.html";
    } catch (error) {
      if (error?.status === 409) {
        note("This registration number is already registered. ", {
          href: "./sign-in.html",
          text: "Sign in instead →",
        });
        regno?.focus();
      } else if (error?.status === 422) {
        note("Check your entries and try again.");
      } else if (error?.status === 0) {
        note("Cannot reach the server. Check your connection and try again.");
      } else {
        note(error?.message || "Could not create the account. Try again.");
      }
      submitButton.disabled = false;
      submitButton.textContent = originalLabel;
    }
  });
}
