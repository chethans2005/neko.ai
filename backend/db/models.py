"""
Database Models - SQLAlchemy ORM Models

Defines the database schema for persistent session storage.
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class SessionModel(Base):
    """
    Session table - stores presentation sessions.
    
    Each session represents a user's presentation workspace with
    topic, template, tone, and associated slides.
    """
    __tablename__ = "sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=generate_uuid)
    topic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    template: Mapped[str] = mapped_column(String(50), default="professional")
    tone: Mapped[str] = mapped_column(String(50), default="professional")
    context_memory: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    slides: Mapped[List["SlideModel"]] = relationship(
        "SlideModel",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    chat_messages: Mapped[List["ChatMessageModel"]] = relationship(
        "ChatMessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Session(id={self.id}, session_id={self.session_id}, topic={self.topic})>"


class SlideModel(Base):
    """
    Slide table - stores individual slides within a session.
    
    Each slide has a position (slide_number) and tracks its
    current version for display.
    """
    __tablename__ = "slides"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    slide_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[str] = mapped_column(JSON, nullable=False)  # List of bullet points
    speaker_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session: Mapped["SessionModel"] = relationship("SessionModel", back_populates="slides")
    versions: Mapped[List["SlideVersionModel"]] = relationship(
        "SlideVersionModel",
        back_populates="slide",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SlideVersionModel.version_number"
    )
    
    def __repr__(self) -> str:
        return f"<Slide(id={self.id}, slide_number={self.slide_number}, title={self.title[:30]}...)>"


class SlideVersionModel(Base):
    """
    Slide Version table - stores version history for slides.
    
    Every edit to a slide creates a new version, enabling
    rollback functionality.
    """
    __tablename__ = "slide_versions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slide_id: Mapped[int] = mapped_column(Integer, ForeignKey("slides.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[str] = mapped_column(JSON, nullable=False)  # List of bullet points
    speaker_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Edit instruction that created this version
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    slide: Mapped["SlideModel"] = relationship("SlideModel", back_populates="versions")
    
    def __repr__(self) -> str:
        return f"<SlideVersion(id={self.id}, slide_id={self.slide_id}, version={self.version_number})>"


class ChatMessageModel(Base):
    """
    Chat Message table - stores conversation history.
    
    Maintains ChatGPT-like context for the session.
    """
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    related_slide: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session: Mapped["SessionModel"] = relationship("SessionModel", back_populates="chat_messages")
    
    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role={self.role}, content={self.content[:30]}...)>"


class UserModel(Base):
    """Users table for email/google authentication."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    provider: Mapped[str] = mapped_column(String(20), default="email")  # email or google
    google_sub: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requests_generated: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    session_links: Mapped[List["UserSessionMapModel"]] = relationship(
        "UserSessionMapModel",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    history_items: Mapped[List["PresentationHistoryModel"]] = relationship(
        "PresentationHistoryModel",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class UserSessionMapModel(Base):
    """Maps presentation sessions to user accounts."""
    __tablename__ = "user_session_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="session_links")


class PresentationHistoryModel(Base):
    """Stores generated PPT history per user for re-download."""
    __tablename__ = "presentation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    history_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=generate_uuid)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    topic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    slide_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="history_items")
