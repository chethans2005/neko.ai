"""
CRUD Operations - Database Access Layer

Provides async CRUD operations for all database models.
"""
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import (
    SessionModel,
    SlideModel,
    SlideVersionModel,
    ChatMessageModel,
    UserModel,
    UserSessionMapModel,
    PresentationHistoryModel,
    EmailOtpModel,
    PendingSignupModel,
)


# =============================================================================
# Session CRUD
# =============================================================================

async def create_session(
    db: AsyncSession,
    session_id: str,
    template: str = "professional",
    tone: str = "professional"
) -> SessionModel:
    """Create a new session."""
    session = SessionModel(
        session_id=session_id,
        template=template,
        tone=tone,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_by_uuid(db: AsyncSession, session_id: str) -> Optional[SessionModel]:
    """Get a session by its UUID."""
    result = await db.execute(
        select(SessionModel)
        .where(SessionModel.session_id == session_id)
        .options(
            selectinload(SessionModel.slides).selectinload(SlideModel.versions),
            selectinload(SessionModel.chat_messages)
        )
    )
    return result.scalar_one_or_none()


async def get_session_row_by_uuid(db: AsyncSession, session_id: str) -> Optional[SessionModel]:
    """Get a session row by UUID without eager-loading relations."""
    result = await db.execute(
        select(SessionModel).where(SessionModel.session_id == session_id)
    )
    return result.scalar_one_or_none()


async def get_session_db_id_by_uuid(db: AsyncSession, session_uuid: str) -> Optional[int]:
    """Get internal database session id from public session UUID."""
    result = await db.execute(
        select(SessionModel.id).where(SessionModel.session_id == session_uuid)
    )
    return result.scalar_one_or_none()


async def get_session_by_id(db: AsyncSession, id: int) -> Optional[SessionModel]:
    """Get a session by its database ID."""
    result = await db.execute(
        select(SessionModel)
        .where(SessionModel.id == id)
        .options(
            selectinload(SessionModel.slides).selectinload(SlideModel.versions),
            selectinload(SessionModel.chat_messages)
        )
    )
    return result.scalar_one_or_none()


async def update_session(
    db: AsyncSession,
    session_id: str,
    topic: Optional[str] = None,
    template: Optional[str] = None,
    tone: Optional[str] = None,
    context_memory: Optional[str] = None
) -> Optional[SessionModel]:
    """Update session fields."""
    session = await get_session_row_by_uuid(db, session_id)
    if not session:
        return None
    
    if topic is not None:
        session.topic = topic
    if template is not None:
        session.template = template
    if tone is not None:
        session.tone = tone
    if context_memory is not None:
        session.context_memory = context_memory
    
    session.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(session)
    return session


async def delete_session(db: AsyncSession, session_id: str) -> bool:
    """Delete a session and all associated data."""
    session = await get_session_row_by_uuid(db, session_id)
    if not session:
        return False
    
    await db.delete(session)
    await db.commit()
    return True


async def list_sessions(db: AsyncSession) -> List[SessionModel]:
    """List all sessions."""
    result = await db.execute(select(SessionModel).order_by(SessionModel.created_at.desc()))
    return list(result.scalars().all())


# =============================================================================
# Slide CRUD
# =============================================================================

async def create_slide(
    db: AsyncSession,
    session_db_id: int,
    slide_number: int,
    title: str,
    content: List[str],
    speaker_notes: Optional[str] = None,
    instruction: str = "Initial generation",
    commit: bool = True,
) -> SlideModel:
    """Create a new slide with initial version."""
    # Create slide
    slide = SlideModel(
        session_id=session_db_id,
        slide_number=slide_number,
        title=title,
        content_json=content,
        speaker_notes=speaker_notes,
        current_version=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(slide)
    await db.flush()  # Get the slide ID
    
    # Create initial version
    version = SlideVersionModel(
        slide_id=slide.id,
        version_number=0,
        title=title,
        content_json=content,
        speaker_notes=speaker_notes,
        instruction=instruction,
        created_at=datetime.utcnow()
    )
    db.add(version)
    
    if commit:
        await db.commit()
        await db.refresh(slide)
    return slide


async def get_slide(db: AsyncSession, session_id: str, slide_number: int) -> Optional[SlideModel]:
    """Get a slide by session UUID and slide number."""
    session_db_id = await get_session_db_id_by_uuid(db, session_id)
    if session_db_id is None:
        return None
    
    result = await db.execute(
        select(SlideModel)
        .where(SlideModel.session_id == session_db_id)
        .where(SlideModel.slide_number == slide_number)
        .options(selectinload(SlideModel.versions))
    )
    return result.scalar_one_or_none()


async def update_slide_content(
    db: AsyncSession,
    slide: SlideModel,
    title: str,
    content: List[str],
    speaker_notes: Optional[str] = None,
    instruction: Optional[str] = None
) -> SlideModel:
    """
    Update slide content by creating a new version.
    
    This creates a new version entry and updates the current_version pointer.
    """
    # Determine new version number
    new_version_num = len(slide.versions)
    
    # Create new version
    version = SlideVersionModel(
        slide_id=slide.id,
        version_number=new_version_num,
        title=title,
        content_json=content,
        speaker_notes=speaker_notes,
        instruction=instruction,
        created_at=datetime.utcnow()
    )
    db.add(version)
    
    # Update slide with new content
    slide.title = title
    slide.content_json = content
    slide.speaker_notes = speaker_notes
    slide.current_version = new_version_num
    slide.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(slide)
    return slide


async def rollback_slide_version(
    db: AsyncSession,
    slide: SlideModel,
    version_index: int
) -> Optional[SlideModel]:
    """Rollback a slide to a previous version."""
    if version_index < 0 or version_index >= len(slide.versions):
        return None
    
    version = slide.versions[version_index]
    
    # Update slide with version content
    slide.title = version.title
    slide.content_json = version.content_json
    slide.speaker_notes = version.speaker_notes
    slide.current_version = version_index
    slide.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(slide)
    return slide


async def delete_slides_for_session(db: AsyncSession, session_db_id: int, commit: bool = True) -> None:
    """Delete all slides for a session (used before regenerating)."""
    await db.execute(
        delete(SlideModel).where(SlideModel.session_id == session_db_id)
    )
    if commit:
        await db.commit()


# =============================================================================
# Chat Message CRUD
# =============================================================================

async def add_chat_message(
    db: AsyncSession,
    session_db_id: int,
    role: str,
    content: str,
    related_slide: Optional[int] = None
) -> ChatMessageModel:
    """Add a chat message to session history."""
    message = ChatMessageModel(
        session_id=session_db_id,
        role=role,
        content=content,
        related_slide=related_slide,
        created_at=datetime.utcnow()
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_chat_history(
    db: AsyncSession,
    session_db_id: int,
    limit: int = 50
) -> List[ChatMessageModel]:
    """Get recent chat messages for a session."""
    result = await db.execute(
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == session_db_id)
        .order_by(ChatMessageModel.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()  # Return in chronological order
    return messages


async def clear_chat_history(db: AsyncSession, session_db_id: int) -> None:
    """Clear all chat messages for a session."""
    await db.execute(
        delete(ChatMessageModel).where(ChatMessageModel.session_id == session_db_id)
    )
    await db.commit()


# =============================================================================
# Auth/User CRUD
# =============================================================================

async def create_user(
    db: AsyncSession,
    name: str,
    email: str,
    password_hash: Optional[str] = None,
    provider: str = "email",
    google_sub: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> UserModel:
    user = UserModel(
        name=name,
        email=email.lower().strip(),
        password_hash=password_hash,
        provider=provider,
        google_sub=google_sub,
        avatar_url=avatar_url,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_login_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[UserModel]:
    result = await db.execute(
        select(UserModel).where(UserModel.email == email.lower().strip())
    )
    return result.scalar_one_or_none()


async def get_user_by_uuid(db: AsyncSession, user_id: str) -> Optional[UserModel]:
    result = await db.execute(select(UserModel).where(UserModel.user_id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_google_sub(db: AsyncSession, google_sub: str) -> Optional[UserModel]:
    result = await db.execute(select(UserModel).where(UserModel.google_sub == google_sub))
    return result.scalar_one_or_none()


async def update_user_login(db: AsyncSession, user: UserModel) -> UserModel:
    user.last_login_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def increment_user_requests(db: AsyncSession, user: UserModel, amount: int = 1) -> UserModel:
    user.requests_generated = (user.requests_generated or 0) + max(0, amount)
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def increment_user_requests_by_id(db: AsyncSession, user_db_id: int, amount: int = 1) -> None:
    """Increment generated slide count without loading the full user model."""
    increment_by = max(0, amount)
    await db.execute(
        update(UserModel)
        .where(UserModel.id == user_db_id)
        .values(
            requests_generated=UserModel.requests_generated + increment_by,
            updated_at=datetime.utcnow(),
        )
    )
    await db.commit()


async def upsert_pending_signup(
    db: AsyncSession,
    email: str,
    name: str,
    password_hash: str,
    expires_at: datetime,
) -> PendingSignupModel:
    normalized_email = email.lower().strip()
    result = await db.execute(
        select(PendingSignupModel).where(PendingSignupModel.email == normalized_email)
    )
    pending = result.scalar_one_or_none()

    if pending:
        pending.name = name
        pending.password_hash = password_hash
        pending.expires_at = expires_at
        pending.created_at = datetime.utcnow()
    else:
        pending = PendingSignupModel(
            email=normalized_email,
            name=name,
            password_hash=password_hash,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )
        db.add(pending)

    await db.commit()
    await db.refresh(pending)
    return pending


async def get_pending_signup_by_email(db: AsyncSession, email: str) -> Optional[PendingSignupModel]:
    result = await db.execute(
        select(PendingSignupModel).where(PendingSignupModel.email == email.lower().strip())
    )
    return result.scalar_one_or_none()


async def delete_pending_signup(db: AsyncSession, pending: PendingSignupModel) -> None:
    await db.delete(pending)
    await db.commit()


async def create_email_otp(
    db: AsyncSession,
    email: str,
    purpose: str,
    code_hash: str,
    expires_at: datetime,
    resend_available_at: datetime,
) -> EmailOtpModel:
    normalized_email = email.lower().strip()
    existing = await get_latest_active_email_otp(db, normalized_email, purpose)
    if existing:
        existing.used_at = datetime.utcnow()

    otp = EmailOtpModel(
        email=normalized_email,
        purpose=purpose,
        code_hash=code_hash,
        attempts=0,
        expires_at=expires_at,
        resend_available_at=resend_available_at,
        created_at=datetime.utcnow(),
    )
    db.add(otp)
    await db.commit()
    await db.refresh(otp)
    return otp


async def get_latest_active_email_otp(db: AsyncSession, email: str, purpose: str) -> Optional[EmailOtpModel]:
    result = await db.execute(
        select(EmailOtpModel)
        .where(EmailOtpModel.email == email.lower().strip())
        .where(EmailOtpModel.purpose == purpose)
        .where(EmailOtpModel.used_at.is_(None))
        .order_by(EmailOtpModel.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def increment_email_otp_attempts(db: AsyncSession, otp: EmailOtpModel) -> EmailOtpModel:
    otp.attempts = (otp.attempts or 0) + 1
    await db.commit()
    await db.refresh(otp)
    return otp


async def mark_email_otp_used(db: AsyncSession, otp: EmailOtpModel) -> EmailOtpModel:
    otp.used_at = datetime.utcnow()
    await db.commit()
    await db.refresh(otp)
    return otp


async def map_session_to_user(db: AsyncSession, user_db_id: int, session_uuid: str) -> UserSessionMapModel:
    existing = await get_session_user_map(db, session_uuid)
    if existing:
        return existing

    mapping = UserSessionMapModel(
        user_id=user_db_id,
        session_uuid=session_uuid,
        created_at=datetime.utcnow(),
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return mapping


async def get_session_user_map(
    db: AsyncSession,
    session_uuid: str,
    include_user: bool = False,
) -> Optional[UserSessionMapModel]:
    query = select(UserSessionMapModel).where(UserSessionMapModel.session_uuid == session_uuid)
    if include_user:
        query = query.options(selectinload(UserSessionMapModel.user))

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_history_item(
    db: AsyncSession,
    user_db_id: int,
    session_uuid: str,
    topic: Optional[str],
    filename: str,
    file_path: str,
    slide_count: int,
) -> PresentationHistoryModel:
    item = PresentationHistoryModel(
        user_id=user_db_id,
        session_uuid=session_uuid,
        topic=topic,
        filename=filename,
        file_path=file_path,
        slide_count=slide_count,
        created_at=datetime.utcnow(),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def get_user_history(db: AsyncSession, user_db_id: int, limit: int = 100) -> List[PresentationHistoryModel]:
    result = await db.execute(
        select(PresentationHistoryModel)
        .where(PresentationHistoryModel.user_id == user_db_id)
        .order_by(PresentationHistoryModel.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_history_by_id(db: AsyncSession, history_id: str) -> Optional[PresentationHistoryModel]:
    result = await db.execute(
        select(PresentationHistoryModel)
        .where(PresentationHistoryModel.history_id == history_id)
    )
    return result.scalar_one_or_none()


async def delete_history_item(db: AsyncSession, history_item: PresentationHistoryModel) -> None:
    await db.delete(history_item)
    await db.commit()
