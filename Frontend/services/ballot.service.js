// One-shot ballot submit. Picks stay in memory in js/pages/election.js and
// are sent only on Review-and-confirm. Server enforces eligibility, window,
// and one-vote atomically — the Idempotency-Key here just makes retries
// and double-clicks safe to resend.
import { request } from "./http.js";

/** Unique key per ballot attempt; the server dedupes resubmits on it. */
function newIdempotencyKey() {
  try {
    return window.crypto.randomUUID();
  } catch {
    // Non-secure contexts lack randomUUID; uniqueness still holds for voting scale.
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
}

/**
 * Cast the ballot once.
 * @param {string} electionId Target election.
 * @param {Record<string,string>} selections Position → candidate or "Abstain".
 * @param {{idempotencyKey?: string}} opts Reuse a key when retrying the same attempt.
 */
export function submitBallot(electionId, selections, { idempotencyKey } = {}) {
  return request("/ballots", {
    method: "POST",
    auth: true,
    idempotencyKey: idempotencyKey || newIdempotencyKey(),
    body: { election_id: electionId, selections },
  });
}
