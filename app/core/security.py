import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _derive_key(raw_key: str) -> bytes:
    """Derive a Fernet-compatible key from the configured encryption key."""
    if not raw_key:
        raise ValueError("ENCRYPTION_KEY is not configured")
    key_bytes = hashlib.sha256(raw_key.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)


_fernet: Fernet | None = None


def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_derive_key(settings.encryption_key))
    return _fernet


def encrypt_text(plaintext: str) -> str:
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_text(ciphertext: str) -> str:
    return get_fernet().decrypt(ciphertext.encode()).decode()
