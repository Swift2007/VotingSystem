import hashlib
import hmac
import secrets
from dataclasses import dataclass
from threading import RLock

_PASSWORD_HASH_ITERATIONS = 600_000


class DuplicateStudentIDError(Exception):
    pass


@dataclass(frozen=True)
class AuthSession:
    student_id: str
    access_token: str


class InMemoryAuthStore:
    """Temporary auth storage; replace this implementation with a database adapter later."""

    def __init__(self) -> None:
        self._users: dict[str, tuple[bytes, bytes]] = {}
        self._tokens: dict[str, str] = {}
        self._lock = RLock()

    def register(self, student_id: str, password: str) -> AuthSession:
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(password, salt)

        with self._lock:
            if student_id in self._users:
                raise DuplicateStudentIDError(student_id)
            self._users[student_id] = (salt, password_hash)
            return self._new_session(student_id)

    def login(self, student_id: str, password: str) -> AuthSession | None:
        with self._lock:
            credentials = self._users.get(student_id)

        if credentials is None:
            return None

        salt, stored_hash = credentials
        submitted_hash = self._hash_password(password, salt)
        if not hmac.compare_digest(submitted_hash, stored_hash):
            return None

        with self._lock:
            return self._new_session(student_id)

    def get_student_id_for_token(self, access_token: str) -> str | None:
        with self._lock:
            return self._tokens.get(access_token)

    def _new_session(self, student_id: str) -> AuthSession:
        access_token = secrets.token_urlsafe(32)
        self._tokens[access_token] = student_id
        return AuthSession(student_id=student_id, access_token=access_token)

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            _PASSWORD_HASH_ITERATIONS,
        )


auth_store = InMemoryAuthStore()