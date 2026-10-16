// Auth client for backend/app/api/auth.py.
// Contract: { student_id: 1–64 chars, password: 8–128 chars } →
// { access_token, token_type: "bearer", user: { student_id } }.
// Token is tab-scoped in sessionStorage — never localStorage or URL.
import { clearToken, getToken, request, setToken } from "./http.js";

/** sessionStorage key for the display ID (token itself lives under TOKEN_KEY). */
const SESSION_USER_KEY = "votex-user";

/** Store token + ID after register/login so the UI survives SPA swaps. */
function rememberSession(payload) {
  setToken(payload?.access_token ?? "");
  try {
    if (payload?.user?.student_id) {
      window.sessionStorage.setItem(SESSION_USER_KEY, payload.user.student_id);
    }
  } catch {
    // Display ID is convenience only; auth still works via the token.
  }
  return payload;
}

/** Last signed-in student ID for headers/avatars ("" when unknown). */
export function getSessionUser() {
  try {
    return window.sessionStorage.getItem(SESSION_USER_KEY) ?? "";
  } catch {
    return "";
  }
}

/** True when a Bearer token is present (server still validates it). */
export function isSignedIn() {
  return Boolean(getToken());
}

/** Drop token + cached ID. */
export function logout() {
  clearToken();
  try {
    window.sessionStorage.removeItem(SESSION_USER_KEY);
  } catch {
    // Ignore storage failures on logout.
  }
}

/** Create account and sign in (409 when the ID is taken). */
export function register(studentId, password) {
  return request("/auth/register", {
    method: "POST",
    body: { student_id: studentId.trim(), password },
  }).then(rememberSession);
}

/** Sign in (401 with generic message to avoid revealing which IDs exist). */
export function login(studentId, password) {
  return request("/auth/login", {
    method: "POST",
    body: { student_id: studentId.trim(), password },
  }).then(rememberSession);
}

/** Current user from the token; throws 401 when missing/expired. */
export function me() {
  return request("/auth/me", { auth: true });
}
