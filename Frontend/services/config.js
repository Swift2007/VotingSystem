// Frontend API base URL.
//
// Resolution order: <meta name="api-base"> → window.__VOTEX_API_BASE → "".
// Empty string means same-origin, which is correct once frontend and
// backend share a host. Set the meta tag for local dev, e.g.
// <meta name="api-base" content="http://127.0.0.1:8000">.
//
// Note: cross-origin dev also needs FastAPI CORSMiddleware on the backend.

/** Base URL without trailing slash. */
const fromMeta =
  typeof document !== "undefined"
    ? document.querySelector('meta[name="api-base"]')?.getAttribute("content")?.trim() ?? ""
    : "";

/** Manual override, useful in console: window.__VOTEX_API_BASE = "...". */
const fromGlobal =
  typeof window !== "undefined" && typeof window.__VOTEX_API_BASE === "string"
    ? window.__VOTEX_API_BASE.trim()
    : "";

/** Avoid double slashes when joining base + path. */
function stripTrailingSlash(value) {
  return value.endsWith("/") && value.length > 1 ? value.slice(0, -1) : value;
}

/** Resolved API origin, e.g. "http://127.0.0.1:8000" or "" for same-origin. */
export const API_BASE = stripTrailingSlash(fromMeta || fromGlobal || "");

/** Default per-request timeout; http.js aborts slower requests. */
export const API_TIMEOUT_MS = 10000;

/** sessionStorage key for the Bearer token (tab-scoped, never in URL). */
export const TOKEN_KEY = "votex-token";

/**
 * Join a backend path with the configured base.
 * @param {string} path Path starting with "/", e.g. "/auth/login".
 * @returns {string} Full URL to fetch.
 */
export function apiUrl(path) {
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${clean}`;
}
