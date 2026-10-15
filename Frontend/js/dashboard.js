import { refreshIcons } from "./components/icons.js";

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
