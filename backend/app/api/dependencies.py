from typing import Optional

from fastapi import Header, HTTPException

from app.services.auth_service import get_current_user_from_token
from db.database import get_db_session
from db import crud


async def require_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing authentication token")

    token = authorization.split(" ", 1)[1].strip()
    user = await get_current_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


async def ensure_session_owned_by_user(session_id: str, user_db_id: int):
    db = await get_db_session()
    try:
        mapping = await crud.get_session_user_map(db, session_id)
        if not mapping or mapping.user_id != user_db_id:
            raise HTTPException(status_code=403, detail="You do not have access to this session")
    finally:
        await db.close()
