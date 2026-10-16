// Shared HTTP layer. Every backend call goes through request() so auth,
// timeout, and error shape stay consistent. Never log bodies here —
// they may carry passwords or ballot choices.
import { API_TIMEOUT_MS, TOKEN_KEY, apiUrl } from "./config.js";

/** Backend failure with HTTP status kept for UI branching (401 vs 409…). */
export class ApiError extends Error {
  /**
   * @param {string} message UI-safe message.
   * @param {{status?: number, details?: unknown}} info Raw status + body.
   */
  constructor(message, { status = 0, details = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

/** Current Bearer token, or "" when signed out / storage blocked. */
export function getToken() {
  try {
    return window.sessionStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

/** Persist or clear the token (pass "" to clear). */
export function setToken(token) {
  try {
    if (token) window.sessionStorage.setItem(TOKEN_KEY, token);
    else window.sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // Private-mode storage: requests still work if the caller passes auth explicitly.
  }
}

/** Sign-out helper: drops the token. */
export function clearToken() {
  setToken("");
}

/** Build the Authorization header. `auth` may be true (use stored token) or a raw token. */
function authHeaders(auth) {
  if (!auth) return {};
  const token = typeof auth === "string" ? auth : getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Prefer FastAPI's `detail` string, else fall back to status-based text. */
function errorMessage(status, data) {
  if (data && typeof data.detail === "string" && data.detail.trim()) return data.detail;
  if (status === 401) return "Sign in required.";
  if (status === 409) return "Already exists.";
  if (status === 422) return "Invalid request.";
  if (status >= 500) return "Server error. Try again.";
  return "Request failed.";
}

/**
 * JSON request with timeout and unified errors.
 * @param {string} path Backend path, e.g. "/auth/me".
 * @param {object} options
 * @param {string} [options.method] HTTP verb.
 * @param {unknown} [options.body] JSON-encoded when defined.
 * @param {boolean|string} [options.auth] Attach Bearer token.
 * @param {string} [options.idempotencyKey] Sent as Idempotency-Key (ballot retries).
 * @param {AbortSignal} [options.signal] Caller cancellation.
 * @param {number} [options.timeoutMs] Override for slow endpoints.
 */
export async function request(path, options = {}) {
  const {
    method = "GET",
    body,
    auth = false,
    idempotencyKey = "",
    signal,
    timeoutMs = API_TIMEOUT_MS,
  } = options;

  // Local timeout that also respects the caller's AbortSignal.
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  const onAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", onAbort, { once: true });
  }

  try {
    const response = await fetch(apiUrl(path), {
      method,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(auth),
        ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    // Empty / non-JSON bodies resolve to null instead of throwing.
    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      throw new ApiError(errorMessage(response.status, data), {
        status: response.status,
        details: data,
      });
    }
    return data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error?.name === "AbortError") {
      throw new ApiError("Request timed out. Try again.", { status: 0 });
    }
    throw new ApiError("Network error. Check your connection.", { status: 0 });
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener?.("abort", onAbort);
  }
}
