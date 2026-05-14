"""
Fernet helpers for encrypting channel credentials at rest.

Uses CHANNEL_ENCRYPTION_KEY if set (44-byte urlsafe base64 Fernet key),
otherwise derives a key from secret_key (development only — set CHANNEL_ENCRYPTION_KEY in production).
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    raw = os.environ.get("CHANNEL_ENCRYPTION_KEY")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        sk = getattr(settings, "channel_encryption_key", "") or ""
        raw = sk.strip() if sk else None
    if raw:
        return Fernet(raw.encode("utf-8") if isinstance(raw, str) else raw)
    # Dev fallback: deterministic from secret_key (not ideal for multi-tenant production)
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> Optional[str]:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning("Failed to decrypt channel credential (wrong key?)")
        return None
