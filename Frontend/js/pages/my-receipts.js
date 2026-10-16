import { refreshIcons } from "../shared/icons.js";
import { requireAuth } from "../shared/session.js";

// Signed-out visitors bounce to sign-in; sign-out links clear the token.
requireAuth();

// My Receipts: copy buttons + hand the code to the verify page
// via sessionStorage (never in the URL).
refreshIcons();
window.addEventListener("load", refreshIcons, { once: true });

document.querySelectorAll(".copy-btn").forEach((button) => {
  button.addEventListener("click", async () => {
    const text = button.dataset.copy ?? "";
    const label = button.querySelector("span");
    const original = label?.textContent ?? "Copy";
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard unavailable — select nothing, still confirm the code visibly.
    }
    if (label) label.textContent = "Copied ✓";
    window.setTimeout(() => {
      if (label) label.textContent = original;
    }, 1500);
  });
});

document.querySelectorAll(".verify-link").forEach((link) => {
  link.addEventListener("click", () => {
    try {
      window.sessionStorage.setItem("votex-verify-code", link.dataset.code ?? "");
    } catch {
      // Non-essential convenience only.
    }
  });
});
