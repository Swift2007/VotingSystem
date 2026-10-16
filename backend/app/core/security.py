"""Password hashing and session tokens.

Passwords: PBKDF2-HMAC-SHA256 with 600,000 iterations and a random 16-byte salt,
stored as ``pbkdf2_sha256$<iterations>$<salt hex>$<hash hex>`` so the
iteration count can be raised later without breaking old hashes.

Tokens: 32 random bytes (URL-safe). The client gets the token; the
database stores only sha256(token) (see models/user.py::AuthSession).
"""
import hashlib
import hmac
import os
import secrets

# Tests lower this via the PASSWORD_HASH_ITERATIONS env var to run quickly.
PASSWORD_HASH_ITERATIONS = int(os.getenv("PASSWORD_HASH_ITERATIONS", "600000"))


def hash_password(password: str, *, iterations: int | None = None) -> str:
    iterations = iterations or PASSWORD_HASH_ITERATIONS
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
    return hmac.compare_digest(digest.hex(), hash_hex)


# A pre-computed hash so failed logins for unknown users take as long as real ones
# (prevents learning which student IDs exist from response time).
DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing")


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
