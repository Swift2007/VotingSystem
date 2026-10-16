"""Import every model so Base.metadata knows all tables.

Table map (who reads what):
* users, auth_sessions                      - login (all roles)
* elections, results                        - election admin
* candidates                                - election admin (write), everyone (read)
* eligible_voters, voter_status, receipts   - voting rules; no vote choices
* ballots                                   - encrypted ballot box; no user link
* chain_blocks, block_transactions,
  audit_log                                 - auditor / observer
"""
from app.models.user import AuthSession, User
from app.models.admin import Election, Result
from app.models.candidate import Candidate
from app.models.student import EligibleVoter, Receipt, VoterStatus
from app.models.ballot import Ballot
from app.models.auditor import AuditLog, BlockTransaction, ChainBlock

__all__ = [
    "User", "AuthSession", "Election", "Result", "Candidate", "EligibleVoter",
    "VoterStatus", "Receipt", "Ballot", "ChainBlock", "BlockTransaction", "AuditLog",
]
