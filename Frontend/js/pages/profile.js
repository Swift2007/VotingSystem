// Profile: account details + voter status.
// Email/regno recap comes from sign-up (sessionStorage); the student ID is
// confirmed live via GET /auth/me. Password change has no backend endpoint
// yet, so the button stays an honest demo note.
import { refreshIcons } from "../shared/icons.js";
import { requireAuth, wireSignOut } from "../shared/session.js";
import { getSessionUser, me } from "../../services/auth.service.js";

// Signed-out visitors bounce to sign-in; sign-out links clear the token.
requireAuth();
// The page's second sign-out button uses .profile-signout, not .sign-out.
wireSignOut(".profile-signout, .sign-out");

refreshIcons();
window.addEventListener("load", refreshIcons, { once: true });

// Recap from sign-up when available (demo defaults already cover the rest).
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

// Live confirmation: show the backend-known student ID when no recap exists.
// requireAuth() already redirects on 401; errors here stay silent on purpose.
try {
  const sessionId = getSessionUser();
  if (!document.querySelector("#profile-regno")?.textContent?.trim() || !sessionId) {
    const profile = await me();
    const slot = document.querySelector("#profile-regno");
    if (slot && profile?.student_id) slot.textContent = profile.student_id;
  }
} catch {
  // Offline or expired — requireAuth's background check handles the redirect.
}

document.querySelector("#password-btn")?.addEventListener("click", () => {
  const note = document.querySelector("#password-note");
  if (note) {
    note.hidden = false;
    note.textContent = "Password change is not wired to the backend yet (demo).";
  }
});
