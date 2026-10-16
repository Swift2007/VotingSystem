import { refreshIcons } from "../shared/icons.js";
import { requireAuth } from "../shared/session.js";

// Signed-out visitors bounce to sign-in; sign-out links clear the token.
requireAuth();

// Dashboard overview: icons + hand receipt codes to the verify page
// via sessionStorage (never in the URL).
refreshIcons();
window.addEventListener("load", refreshIcons, { once: true });

document.querySelectorAll("[data-code]").forEach((link) => {
  link.addEventListener("click", () => {
    try {
      const code = link instanceof HTMLElement ? link.dataset.code ?? "" : "";
      window.sessionStorage.setItem("votex-verify-code", code);
    } catch {
      // Non-essential convenience only.
    }
  });
});
