"""Password hashing using PBKDF2-HMAC-SHA256 (stdlib only).

Format: ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``
Legacy ``sha256:<digest>`` (unsalted) values from the existing seed are accepted
for verify() only — never produced by hash_password().
"""

from __future__ import annotations

import hashlib
import hmac
import os

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 120_000
_SALT_BYTES = 16
_DKLEN = 32


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS, dklen=_DKLEN)
    return f"{_ALGO}${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not stored:
        return False

    if stored.startswith("sha256:"):
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(stored, f"sha256:{digest}")

    if stored.startswith(f"{_ALGO}$"):
        try:
            _, iter_s, salt_hex, hash_hex = stored.split("$", 3)
            iterations = int(iter_s)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
        except (ValueError, TypeError):
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected))
        return hmac.compare_digest(dk, expected)

    return False
