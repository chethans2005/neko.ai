import base64
import hashlib
import hmac
import json
import os
import secrets
import smtplib
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Optional, Tuple

import httpx

from db.database import get_db_session
from db import crud
from app.services.disposable_domains import DISPOSABLE_EMAIL_DOMAINS


AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-secret-change-me")
AUTH_TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", str(60 * 60 * 24 * 7)))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
OTP_SECRET = os.getenv("OTP_SECRET", AUTH_SECRET)
OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "600"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "45"))
PENDING_SIGNUP_TTL_SECONDS = int(os.getenv("PENDING_SIGNUP_TTL_SECONDS", "1800"))
SIGNUP_TOKEN_TTL_SECONDS = int(os.getenv("SIGNUP_TOKEN_TTL_SECONDS", "1800"))
AUTH_DEBUG_RETURN_OTP = os.getenv("AUTH_DEBUG_RETURN_OTP", "false").lower() == "true"

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER).strip()
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "AI PPT")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() != "false"

DISPOSABLE_EMAIL_API_URL = os.getenv("DISPOSABLE_EMAIL_API_URL", "").strip()
DISPOSABLE_EMAIL_API_KEY = os.getenv("DISPOSABLE_EMAIL_API_KEY", "").strip()

SIGNUP_PURPOSE = "signup"


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


def create_signed_token(payload: dict, ttl_seconds: int, token_type: str) -> str:
    normalized_payload = {
        **payload,
        "exp": int(time.time()) + ttl_seconds,
        "token_type": token_type,
    }
    payload_bytes = json.dumps(normalized_payload, separators=(",", ":")).encode("utf-8")
    payload_encoded = _b64url_encode(payload_bytes)
    sig = hmac.new(AUTH_SECRET.encode("utf-8"), payload_encoded.encode("utf-8"), hashlib.sha256).digest()
    sig_encoded = _b64url_encode(sig)
    return f"{payload_encoded}.{sig_encoded}"


def verify_signed_token(token: str, expected_type: str) -> Optional[dict]:
    payload = verify_access_token(token)
    if not payload:
        return None
    if payload.get("token_type") != expected_type:
        return None
    return payload


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


def normalize_email(email: str) -> str:
    return email.lower().strip()


def generate_otp_code() -> str:
    max_value = 10 ** OTP_LENGTH
    return f"{secrets.randbelow(max_value):0{OTP_LENGTH}d}"


def hash_otp(email: str, otp_code: str, purpose: str = SIGNUP_PURPOSE) -> str:
    normalized_email = normalize_email(email)
    material = f"{normalized_email}:{purpose}:{otp_code}".encode("utf-8")
    return hmac.new(OTP_SECRET.encode("utf-8"), material, hashlib.sha256).hexdigest()


async def send_signup_otp_email(to_email: str, name: str, otp_code: str) -> bool:
    subject = "Your AI PPT signup verification code"
    body = (
        f"Hi {name},\n\n"
        f"Your verification code is: {otp_code}\n"
        f"This code expires in {OTP_TTL_SECONDS // 60} minutes.\n\n"
        "If you did not request this, you can ignore this email."
    )

    if not SMTP_HOST or not SMTP_FROM_EMAIL:
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            if SMTP_USE_TLS:
                smtp.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)
        return True
    except Exception:
        return False


def is_locally_disposable_email(email: str) -> bool:
    domain = normalize_email(email).split("@")[-1]
    return domain in DISPOSABLE_EMAIL_DOMAINS


def _parse_disposable_provider_result(data: dict) -> Optional[bool]:
    if not isinstance(data, dict):
        return None
    candidate_keys = ["disposable", "is_disposable", "isDisposable", "disposable_email", "is_disposable_email"]
    for key in candidate_keys:
        value = data.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
    for nested_key in ["data", "result"]:
        nested = data.get(nested_key)
        if isinstance(nested, dict):
            nested_value = _parse_disposable_provider_result(nested)
            if nested_value is not None:
                return nested_value
    return None


async def is_disposable_email(email: str) -> bool:
    if is_locally_disposable_email(email):
        return True

    if not DISPOSABLE_EMAIL_API_URL:
        return False

    headers = {}
    if DISPOSABLE_EMAIL_API_KEY:
        headers["Authorization"] = f"Bearer {DISPOSABLE_EMAIL_API_KEY}"
        headers["X-API-Key"] = DISPOSABLE_EMAIL_API_KEY

    try:
        async with httpx.AsyncClient(timeout=4) as client:
            response = await client.get(
                DISPOSABLE_EMAIL_API_URL,
                params={"email": normalize_email(email)},
                headers=headers,
            )
            response.raise_for_status()
            parsed = _parse_disposable_provider_result(response.json())
            return bool(parsed)
    except Exception:
        return False


def build_signup_token(email: str) -> str:
    return create_signed_token(
        payload={"email": normalize_email(email), "purpose": SIGNUP_PURPOSE},
        ttl_seconds=SIGNUP_TOKEN_TTL_SECONDS,
        token_type="signup",
    )


def verify_signup_token(token: str, email: str) -> bool:
    payload = verify_signed_token(token, "signup")
    if not payload:
        return False
    return payload.get("email") == normalize_email(email) and payload.get("purpose") == SIGNUP_PURPOSE


def utc_now() -> datetime:
    return datetime.utcnow()


def otp_expiry_time() -> datetime:
    return utc_now() + timedelta(seconds=OTP_TTL_SECONDS)


def resend_available_time() -> datetime:
    return utc_now() + timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS)


def pending_signup_expiry_time() -> datetime:
    return utc_now() + timedelta(seconds=PENDING_SIGNUP_TTL_SECONDS)


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
