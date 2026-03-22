"""Encryption service for sensitive credentials.

Uses Fernet (AES-128-CBC + HMAC-SHA256) for symmetric encryption.
The encryption key is stored in a file outside the codebase,
auto-generated on first run if it doesn't exist.
"""

import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_KEY_FILE_ENV = "ENCRYPTION_KEY_FILE"
_DEFAULT_KEY_PATH = Path("/app/data/.encryption_key")

_fernet: Fernet | None = None


def _get_key_path() -> Path:
    """Resolve the encryption key file path from env or default."""
    return Path(os.getenv(_KEY_FILE_ENV, str(_DEFAULT_KEY_PATH)))


def _load_or_create_key() -> bytes:
    """Load the encryption key from file, or generate one if it doesn't exist."""
    key_path = _get_key_path()

    if key_path.exists():
        key = key_path.read_bytes().strip()
        logger.info("Encryption key loaded from %s", key_path)
        return key

    # Generate new key
    key = Fernet.generate_key()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)

    # Restrict permissions (owner-only read/write)
    try:
        key_path.chmod(0o600)
    except OSError:
        pass  # Windows doesn't support Unix permissions

    logger.info("Generated new encryption key at %s", key_path)
    return key


def get_fernet() -> Fernet:
    """Get the singleton Fernet instance."""
    global _fernet
    if _fernet is None:
        key = _load_or_create_key()
        _fernet = Fernet(key)
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a string. Returns a base64-encoded ciphertext string."""
    if not plaintext:
        return ""
    return get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext string. Returns plaintext."""
    if not ciphertext:
        return ""
    try:
        return get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.error("Failed to decrypt value — key may have changed or data is corrupted")
        return ""


def is_encrypted(value: str) -> bool:
    """Check if a value looks like a Fernet-encrypted token."""
    if not value:
        return False
    # Fernet tokens start with 'gAAAAA'
    return value.startswith("gAAAAA") and len(value) > 50
