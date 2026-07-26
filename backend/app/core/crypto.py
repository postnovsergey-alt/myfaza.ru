"""Шифрование отдельных полей БД (раздел 11.2 ТЗ).

Используется для daily_logs.note — свободного текста, который пользователь
пишет о себе. Всё остальное защищается шифрованием диска на уровне сервера.
"""
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import String, TypeDecorator

from app.config import get_settings

_NONCE_BYTES = 12


def _key() -> bytes:
    raw = get_settings().FIELD_ENCRYPTION_KEY
    # Ключ в .env хранится как hex (openssl rand -hex 32)
    return bytes.fromhex(raw) if len(raw) == 64 else raw.encode()[:32].ljust(32, b"\0")


def encrypt(plaintext: str) -> str:
    nonce = os.urandom(_NONCE_BYTES)
    ct = AESGCM(_key()).encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt(token: str) -> str:
    blob = base64.b64decode(token)
    nonce, ct = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
    return AESGCM(_key()).decrypt(nonce, ct, None).decode()


class EncryptedString(TypeDecorator):
    """Прозрачно шифрует значение при записи и расшифровывает при чтении."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else encrypt(value)

    def process_result_value(self, value, dialect):
        return None if value is None else decrypt(value)
