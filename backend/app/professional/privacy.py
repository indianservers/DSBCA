"""Field encryption for private Phase 3 company facts; key stays outside the database."""

import base64, json, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from app.core.config import settings


def key():
    try:
        value = base64.urlsafe_b64decode(settings().data_encryption_key)
        if len(value) != 32:
            raise ValueError()
        return value
    except Exception:
        raise HTTPException(503, "Private company field encryption is not configured")


def protect(data):
    if not data or not any(v not in ["", None, [], {}] for v in data.values()):
        return {}
    nonce = secrets.token_bytes(12)
    payload = json.dumps(data, separators=(",", ":")).encode()
    encrypted = AESGCM(key()).encrypt(nonce, payload, b"DSBCA-private-v1")
    return {"_encrypted_v1": base64.urlsafe_b64encode(nonce + encrypted).decode()}


def reveal(data):
    if not data or "_encrypted_v1" not in data:
        return data
    try:
        raw = base64.urlsafe_b64decode(data["_encrypted_v1"])
        return json.loads(
            AESGCM(key()).decrypt(raw[:12], raw[12:], b"DSBCA-private-v1")
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            503, "Private record cannot be decrypted; verify the configured key"
        )
