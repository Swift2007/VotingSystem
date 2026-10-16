"""Ballot encryption (README critical requirement 3: protect the vote).

Each election has its own random 256-bit key, kept in a file *outside the
database*:

    <ELECTION_KEYS_DIR>/election_<id>.key      (hex, chmod 600)

Only the SHA-256 fingerprint of the key is stored in the `elections` table,
so a stolen database alone cannot decrypt any ballot.

Ciphertext format:  nonce (12 bytes) || AES-GCM(ciphertext + 16-byte tag)
The election id is passed as "associated data", so a ballot copied into a
different election fails to decrypt.

Plaintext: canonical JSON {"choices": {position: candidate_id}, "pad": <random>}.
The random pad makes two identical votes encrypt to different-looking
ciphertexts (AES-GCM's random nonce already does this; the pad also hides the
exact length of short ballots).

Why AES-GCM and not Fernet: a Fernet token embeds the encryption time in
plaintext. That would be a per-ballot timestamp, which the ballots table
deliberately avoids (decision D-006).
"""
import json
import os
import secrets
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.blockchain.hashing import canonical_json, sha256_hex

_NONCE_BYTES = 12


class BallotDecryptionError(Exception):
    """The ciphertext was altered, belongs to another election, or the key is wrong."""


class ElectionKeyStore:
    def __init__(self, keys_dir: str | Path) -> None:
        self.dir = Path(keys_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, election_id: int) -> Path:
        return self.dir / f"election_{election_id}.key"

    def create(self, election_id: int) -> str:
        """Generate a key for a new election. Returns its fingerprint."""
        path = self._path(election_id)
        if path.exists():
            return self.fingerprint(election_id)
        key = AESGCM.generate_key(bit_length=256)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(key.hex())
        return sha256_hex(key)

    def _key(self, election_id: int) -> bytes:
        try:
            return bytes.fromhex(self._path(election_id).read_text().strip())
        except FileNotFoundError as error:
            raise BallotDecryptionError(f"no key file for election {election_id}") from error

    def fingerprint(self, election_id: int) -> str:
        return sha256_hex(self._key(election_id))

    def encrypt(self, election_id: int, choices: dict[str, int]) -> bytes:
        """Encrypt a validated ballot. Returns nonce || ciphertext."""
        payload = canonical_json({"choices": choices, "pad": secrets.token_hex(secrets.randbelow(16) + 8)})
        nonce = secrets.token_bytes(_NONCE_BYTES)
        aad = str(election_id).encode()
        return nonce + AESGCM(self._key(election_id)).encrypt(nonce, payload, aad)

    def decrypt(self, election_id: int, blob: bytes) -> dict[str, int]:
        """Decrypt a ballot (tally only). Raises BallotDecryptionError."""
        if len(blob) <= _NONCE_BYTES:
            raise BallotDecryptionError("ciphertext too short")
        nonce, ciphertext = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
        try:
            plaintext = AESGCM(self._key(election_id)).decrypt(nonce, ciphertext, str(election_id).encode())
            data = json.loads(plaintext)
            return {str(k): int(v) for k, v in data["choices"].items()}
        except (InvalidTag, ValueError, KeyError, TypeError, AttributeError) as error:
            raise BallotDecryptionError("ballot could not be decrypted") from error


def ballot_hash(ballot_id: str, encrypted_ballot: bytes) -> str:
    """The only value recorded on the chain for a ballot."""
    return sha256_hex(bytes.fromhex(ballot_id) + encrypted_ballot)
