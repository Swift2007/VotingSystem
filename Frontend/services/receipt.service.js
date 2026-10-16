// Receipt verification: proves counting without revealing the choice.
// Display format stays "VC · XXXX · XXXX · XXXX"; the API uses the
// normalized form (uppercase alphanumerics only).
import { request } from "./http.js";

/** Strip separators/spaces: "VC · 7QK4…" → "VC7QK4…". Matches verify-receipt.js. */
export function normalizeReceiptCode(value) {
  return String(value ?? "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "");
}

/** Check one receipt; 404 means "no ballot matches this code". */
export function verifyReceipt(code) {
  const normalized = normalizeReceiptCode(code);
  return request(`/receipts/${encodeURIComponent(normalized)}`, { auth: true });
}

/** Receipts for the signed-in voter (codes only, never choices). */
export function listMyReceipts() {
  return request("/receipts/mine", { auth: true });
}
