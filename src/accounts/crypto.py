from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from decouple import config


def _key_bytes(master_key):
    if isinstance(master_key, bytes):
        return master_key
    return master_key.encode("utf-8")


@lru_cache(maxsize=1)
def _fernet():
    return Fernet(_key_bytes(config("MASTER_ENCRYPTION_KEY")))


def encrypt_value(value):
    if value is None:
        raise ValueError("value cannot be None")
    if not isinstance(value, str):
        value = str(value)
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_value(encrypted_value):
    if not encrypted_value:
        return None
    try:
        return _fernet().decrypt(encrypted_value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeError):
        return None
