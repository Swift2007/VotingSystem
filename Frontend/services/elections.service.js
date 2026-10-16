// Election catalog. Backend route not built yet — paths below are the
// agreed contract so pages work unchanged once GET /elections lands.
// Item shape: { id, title, status: "upcoming"|"open"|"closed",
//   positions: number, closes_at: string|null }.
import { request } from "./http.js";

/** Open + upcoming + closed elections visible to the signed-in student. */
export function listElections() {
  return request("/elections", { auth: true });
}

/** Single election with positions/candidates. */
export function getElection(electionId) {
  return request(`/elections/${encodeURIComponent(electionId)}`, { auth: true });
}
