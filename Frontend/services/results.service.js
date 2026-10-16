// Published results. Backend must 404 until the election is closed —
// the frontend never infers partial totals from this endpoint.
import { request } from "./http.js";

/** All published elections with winners + per-candidate totals. */
export function listResults() {
  return request("/results", { auth: true });
}

/** Published totals for one closed election. */
export function getResult(electionId) {
  return request(`/results/${encodeURIComponent(electionId)}`, { auth: true });
}
