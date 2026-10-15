"""Import every model so Base.metadata knows all 10 tables."""
from app.models.user import User
from app.models.admin import Election, Result
from app.models.candidate import Candidate
from app.models.student import EligibleVoter, VoterStatus, Receipt
from app.models.ballot import Ballot
from app.models.auditor import ChainBlock, AuditLog

__all__ = ["User", "Election", "Result", "Candidate", "EligibleVoter",
           "VoterStatus", "Receipt", "Ballot", "ChainBlock", "AuditLog"]
