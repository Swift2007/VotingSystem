import { refreshIcons } from "../shared/icons.js";
import { requireAuth } from "../shared/session.js";

// Signed-out visitors bounce to sign-in; sign-out links clear the token.
requireAuth();

// Profile: icons + details from sign-up when available (demo defaults otherwise).
refreshIcons();
window.addEventListener("load", refreshIcons, { once: true });

try {
  const email = window.sessionStorage.getItem("votex-email");
  const regno = window.sessionStorage.getItem("votex-regno");
  if (email) {
    const slot = document.querySelector("#profile-email");
    if (slot) slot.textContent = email;
  }
  if (regno) {
    const slot = document.querySelector("#profile-regno");
    if (slot) slot.textContent = regno;
  }
} catch {
  // Storage unavailable — demo defaults already cover it.
}

document.querySelector("#password-btn")?.addEventListener("click", () => {
  const note = document.querySelector("#password-note");
  if (note) {
    note.hidden = false;
    note.textContent = "Password change is not wired to the backend yet (demo).";
  }
});
