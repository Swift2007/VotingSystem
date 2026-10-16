// Sign-in page: validation + real POST /auth/login via services/.
// Server enforces auth; this only handles UX: hints, honest pending state,
// generic errors (never reveal which IDs exist), and post-login redirect.
import { login } from "../../services/auth.service.js";
import { loginRedirectTarget, redirectIfSignedIn } from "../shared/session.js";

// Already signed in (e.g. back-button after logout in another tab skipped)
// → skip straight to the app instead of showing the form.
if (redirectIfSignedIn()) {
  // Navigation away; stop module execution.
} else {
  const form = document.querySelector("#signin-form");
  const identifier = document.querySelector("#identifier");
  const password = document.querySelector("#password");
  const submitButton = form?.querySelector('[type="submit"]');
  const errorBox = document.querySelector("#form-error");
  const showToggle = document.querySelector(".show-toggle");

  const identifierHint = document.querySelector("#identifier-hint");
  const passwordHint = document.querySelector("#password-hint");

  /** Show or clear a field hint + aria-invalid. */
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

  /** Replace the demo error markup with a single safe message (textContent only). */
  function showError(message) {
    if (!errorBox) return;
    errorBox.textContent = "";
    const line = document.createElement("p");
    line.textContent = message;
    errorBox.appendChild(line);
    errorBox.hidden = false;
  }

  function clearError() {
    if (!errorBox) return;
    errorBox.hidden = true;
    errorBox.textContent = "";
  }

  showToggle?.addEventListener("click", () => {
    if (!(password instanceof HTMLInputElement)) return;
    const showing = password.type === "text";
    password.type = showing ? "password" : "text";
    showToggle.textContent = showing ? "Show" : "Hide";
    showToggle.setAttribute("aria-pressed", String(!showing));
    password.focus();
  });

  // Clear server errors as soon as the user edits (keeps role=alert accurate).
  identifier?.addEventListener("input", () => {
    setHint(identifierHint, identifier, "");
    clearError();
  });
  password?.addEventListener("input", () => {
    setHint(passwordHint, password, "");
    clearError();
  });

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form || !submitButton || submitButton.disabled) return; // prevent double submit

    const idValue = identifier?.value.trim() ?? "";
    const pwValue = password?.value ?? "";
    let valid = true;

    setHint(identifierHint, identifier, "");
    setHint(passwordHint, password, "");
    clearError();

    if (!idValue) {
      setHint(identifierHint, identifier, "Enter your school email or registration number.");
      valid = false;
    }
    if (!pwValue) {
      setHint(passwordHint, password, "Enter your password.");
      valid = false;
    } else if (pwValue.length < 8) {
      // Matches backend min_length=8; avoids a round-trip that would 422.
      setHint(passwordHint, password, "Password must be at least 8 characters.");
      valid = false;
    }
    if (!valid) {
      (identifier?.value ? password : identifier)?.focus();
      return;
    }

    // Honest pending state. Never claim sign-in before the API confirms.
    submitButton.disabled = true;
    const originalLabel = submitButton.textContent;
    submitButton.textContent = "Signing in…";

    try {
      await login(idValue, pwValue);
      // Success → full load so the next page boots with the fresh session.
      window.location.href = loginRedirectTarget();
    } catch (error) {
      // Generic 401 message for both fields so it never reveals which IDs exist.
      if (error?.status === 401) {
        showError("Email or password is incorrect.");
      } else if (error?.status === 422) {
        showError("Check your entries and try again.");
      } else if (error?.status === 0) {
        showError("Cannot reach the server. Check your connection and try again.");
      } else {
        showError(error?.message || "Sign in failed. Try again.");
      }
      // Keep the ID, drop the password on credential errors.
      if (error?.status === 401 && password instanceof HTMLInputElement) {
        password.value = "";
        password.focus();
      }
      submitButton.disabled = false;
      submitButton.textContent = originalLabel;
    }
  });
}
