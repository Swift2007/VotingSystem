// Client-side session guard. Server remains the enforcer for eligibility,
// one-vote, and windows — this only keeps the UI honest (redirects,
// sign-out clearing, avatar initials).
import { getSessionUser, isSignedIn, logout, me } from "../../services/auth.service.js";

const SIGN_IN_PAGE = "./sign-in.html";

/** Filenames allowed as ?next= targets (same folder, no external URLs). */
function isSafeNext(value) {
  if (!value) return false;
  if (/^(https?:)?\/\//i.test(value) || value.includes("\\") || value.includes(":")) return false;
  const clean = value.split("?")[0].split("#")[0];
  return /^[A-Za-z0-9][A-Za-z0-9._-]*\.html?$/.test(clean) || /^\.\/[A-Za-z0-9][A-Za-z0-9._-]*\.html?$/.test(clean);
}

/** Where to send the user after sign-in (?next= when safe, else dashboard). */
export function loginRedirectTarget(fallback = "./dashboard.html") {
  try {
    const next = new URLSearchParams(window.location.search).get("next") ?? "";
    if (isSafeNext(next)) return next.startsWith("./") ? next : `./${next}`;
  } catch {
    // Ignore malformed URLs.
  }
  return fallback;
}

/** Clear token on every sign-out link without breaking its navigation. */
export function wireSignOut(selector = ".sign-out") {
  document.querySelectorAll(selector).forEach((link) => {
    if (link instanceof HTMLElement && link.dataset.wired) return;
    if (link instanceof HTMLElement) link.dataset.wired = "1";
    link.addEventListener("click", () => logout());
  });
}

/** Show stored ID initials in the topbar avatar (leaves demo text when unknown). */
export function updateAccountUI() {
  const user = getSessionUser().trim();
  if (!user) return;
  const initials = user
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
  document.querySelectorAll(".account-avatar").forEach((el) => {
    el.textContent = initials || user.slice(0, 2).toUpperCase();
    el.setAttribute("aria-label", `Signed in as ${user}`);
  });
}

/**
 * Protect an app page. Redirects to sign-in when no token exists.
 * When a stale token exists, validates in the background via GET /auth/me
 * and signs out + redirects on 401.
 * @returns {boolean} false when redirecting away.
 */
export function requireAuth() {
  wireSignOut();
  updateAccountUI();
  if (!isSignedIn()) {
    const current = window.location.pathname.split("/").pop() || "dashboard.html";
    const next = isSafeNext(current) ? `./${current}` : "./dashboard.html";
    window.location.href = `${SIGN_IN_PAGE}?next=${encodeURIComponent(next)}`;
    return false;
  }
  // Background revalidation only — never blocks the page on network errors.
  me().catch((error) => {
    if (error?.status === 401) {
      logout();
      window.location.href = SIGN_IN_PAGE;
    }
  });
  return true;
}

/** Sign-in page helper: already signed in → skip straight to the app. */
export function redirectIfSignedIn() {
  if (isSignedIn()) {
    window.location.replace(loginRedirectTarget());
    return true;
  }
  return false;
}
