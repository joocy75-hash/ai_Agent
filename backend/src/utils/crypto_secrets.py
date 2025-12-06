from os import getenv

from cryptography.fernet import Fernet, InvalidToken


class CryptoError(Exception):
    """Raised when encryption or decryption fails."""


def _build_fernet() -> Fernet:
    key = getenv("ENCRYPTION_KEY", "")
    if not key:
        raise CryptoError("ENCRYPTION_KEY environment variable is required for secret encryption.")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise CryptoError("ENCRYPTION_KEY must be a valid URL-safe base64 32-byte key.") from exc


_FERNET = _build_fernet()


def get_fernet() -> Fernet:
    """Return the singleton Fernet instance."""
    return _FERNET


def encrypt_secret(plaintext: str) -> str:
    if plaintext is None:
        return ""
    fernet = get_fernet()
    token = fernet.encrypt(plaintext.encode())
    return token.decode()


def decrypt_secret(ciphertext: str | None) -> str | None:
    if not ciphertext:
        return None
    fernet = get_fernet()
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise CryptoError("Cannot decrypt secret; token invalid.") from exc
