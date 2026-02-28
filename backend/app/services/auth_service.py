import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional, Tuple

from db.database import get_db_session
from db import crud


AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-secret-change-me")
AUTH_TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", str(60 * 60 * 24 * 7)))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, expected = stored.split("$", 1)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return hmac.compare_digest(digest, expected)


def create_access_token(user_id: str, email: str, name: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "exp": int(time.time()) + AUTH_TOKEN_TTL_SECONDS,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_encoded = _b64url_encode(payload_bytes)
    sig = hmac.new(AUTH_SECRET.encode("utf-8"), payload_encoded.encode("utf-8"), hashlib.sha256).digest()
    sig_encoded = _b64url_encode(sig)
    return f"{payload_encoded}.{sig_encoded}"


def verify_access_token(token: str) -> Optional[dict]:
    if not token or "." not in token:
        return None

    payload_encoded, sig_encoded = token.rsplit(".", 1)
    expected_sig = hmac.new(AUTH_SECRET.encode("utf-8"), payload_encoded.encode("utf-8"), hashlib.sha256).digest()

    try:
        provided_sig = _b64url_decode(sig_encoded)
    except Exception:
        return None

    if not hmac.compare_digest(expected_sig, provided_sig):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_encoded).decode("utf-8"))
    except Exception:
        return None

    if int(payload.get("exp", 0)) < int(time.time()):
        return None

    return payload


async def get_current_user_from_token(token: str):
    payload = verify_access_token(token)
    if not payload:
        return None

    db = await get_db_session()
    try:
        return await crud.get_user_by_uuid(db, payload["user_id"])
    finally:
        await db.close()


async def verify_google_id_token(google_id_token: str) -> Tuple[str, str, str, Optional[str]]:
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests
    except Exception as exc:
        raise ValueError("Google auth libraries are not available") from exc

    if not GOOGLE_CLIENT_ID:
        raise ValueError("GOOGLE_CLIENT_ID is not configured on backend")

    idinfo = id_token.verify_oauth2_token(google_id_token, requests.Request(), GOOGLE_CLIENT_ID)
    email = idinfo.get("email")
    name = idinfo.get("name") or (email.split("@")[0] if email else "Google User")
    sub = idinfo.get("sub")
    picture = idinfo.get("picture")

    if not email or not sub:
        raise ValueError("Invalid Google token payload")

    return email.lower().strip(), name, sub, picture


async def link_history_to_session(session_uuid: str, topic: Optional[str], filepath: str, slide_count: int):
    db = await get_db_session()
    try:
        mapping = await crud.get_session_user_map(db, session_uuid)
        if not mapping or not mapping.user:
            return None

        filename = os.path.basename(filepath)
        item = await crud.create_history_item(
            db=db,
            user_db_id=mapping.user_id,
            session_uuid=session_uuid,
            topic=topic,
            filename=filename,
            file_path=filepath,
            slide_count=slide_count,
        )
        await crud.increment_user_requests(db, mapping.user, amount=slide_count)
        return item
    finally:
        await db.close()
