"""
Session Service - ChatGPT-like Session Management

Handles session creation, persistence, and context management
for maintaining conversation history and presentation state.
Uses SQLite database for persistent storage.
"""
import uuid
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

# Add backend directory to path for db module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.schemas import (
    SessionData, SessionResponse, SlideWithHistory, SlideVersion,
    ChatMessage, TemplateType, ToneType
)
from db.database import get_db_session
from db import crud
from db.models import SessionModel, SlideModel


class SessionManager:
    """
    Manages user sessions with ChatGPT-like context persistence.
    
    Features:
    - Session creation and retrieval
    - Slide history and version tracking
    - Chat history for context
    - Database persistence for durability
    """
    
    def __init__(self):
        # In-memory cache for performance
        self.sessions: Dict[str, SessionData] = {}
    
    def _db_session_to_schema(self, db_session: SessionModel) -> SessionData:
        """Convert database session model to Pydantic schema."""
        slides = []
        for db_slide in db_session.slides:
            versions = []
            for idx, db_version in enumerate(db_slide.versions):
                versions.append(SlideVersion(
                    version=idx,
                    title=db_version.title,
                    content=db_version.content_json if isinstance(db_version.content_json, list) else json.loads(db_version.content_json),
                    speaker_notes=db_version.speaker_notes,
                    created_at=db_version.created_at,
                    instruction=db_version.instruction
                ))
            
            slides.append(SlideWithHistory(
                slide_number=db_slide.slide_number,
                versions=versions,
                current_version=db_slide.current_version
            ))
        
        chat_history = []
        for db_msg in db_session.chat_messages:
            chat_history.append(ChatMessage(
                role=db_msg.role,
                content=db_msg.content,
                timestamp=db_msg.created_at,
                related_slide=db_msg.related_slide
            ))
        
        return SessionData(
            session_id=db_session.session_id,
            topic=db_session.topic,
            template=TemplateType(db_session.template),
            tone=ToneType(db_session.tone),
            slides=slides,
            chat_history=chat_history,
            context_memory=db_session.context_memory or "",
            created_at=db_session.created_at,
            last_updated=db_session.updated_at
        )
    
    async def create_session(
        self,
        template: TemplateType = TemplateType.PROFESSIONAL,
        tone: ToneType = ToneType.PROFESSIONAL
    ) -> SessionData:
        """
        Create a new session.
        
        Returns:
            SessionData with new session ID
        """
        session_id = str(uuid.uuid4())
        
        db = await get_db_session()
        try:
            db_session = await crud.create_session(
                db=db,
                session_id=session_id,
                template=template.value,
                tone=tone.value
            )
            
            session = self._db_session_to_schema(db_session)
            self.sessions[session_id] = session
            return session
        finally:
            await db.close()
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get a session by ID.
        
        Checks memory cache first, then loads from database if needed.
        """
        # Check memory cache
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # Load from database
        db = await get_db_session()
        try:
            db_session = await crud.get_session_by_uuid(db, session_id)
            if db_session:
                session = self._db_session_to_schema(db_session)
                self.sessions[session_id] = session
                return session
            return None
        finally:
            await db.close()
    
    async def update_session(
        self,
        session_id: str,
        topic: Optional[str] = None,
        slides: Optional[List[SlideWithHistory]] = None,
        context_memory: Optional[str] = None,
        template: Optional[TemplateType] = None,
        tone: Optional[ToneType] = None
    ) -> Optional[SessionData]:
        """
        Update session data.
        """
        db = await get_db_session()
        try:
            db_session = await crud.get_session_by_uuid(db, session_id)
            if not db_session:
                return None
            
            # Update session fields
            await crud.update_session(
                db=db,
                session_id=session_id,
                topic=topic,
                template=template.value if template else None,
                tone=tone.value if tone else None,
                context_memory=context_memory
            )
            
            # Handle slides update
            if slides is not None:
                # Clear existing slides and recreate
                await crud.delete_slides_for_session(db, db_session.id)
                
                for slide in slides:
                    current_version = slide.versions[slide.current_version]
                    await crud.create_slide(
                        db=db,
                        session_db_id=db_session.id,
                        slide_number=slide.slide_number,
                        title=current_version.title,
                        content=current_version.content,
                        speaker_notes=current_version.speaker_notes,
                        instruction="Initial generation"
                    )
            
            # Refresh and convert
            db_session = await crud.get_session_by_uuid(db, session_id)
            session = self._db_session_to_schema(db_session)
            self.sessions[session_id] = session
            return session
        finally:
            await db.close()
    
    async def add_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        related_slide: Optional[int] = None
    ) -> Optional[SessionData]:
        """
        Add a chat message to session history.
        """
        db = await get_db_session()
        try:
            db_session = await crud.get_session_by_uuid(db, session_id)
            if not db_session:
                return None
            
            await crud.add_chat_message(
                db=db,
                session_db_id=db_session.id,
                role=role,
                content=content,
                related_slide=related_slide
            )
            
            # Get chat count and trim if needed
            messages = await crud.get_chat_history(db, db_session.id, limit=100)
            if len(messages) > 50:
                # We only keep the latest 50 in the returned data
                pass  # The limit already handles this
            
            # Refresh and convert
            db_session = await crud.get_session_by_uuid(db, session_id)
            session = self._db_session_to_schema(db_session)
            self.sessions[session_id] = session
            return session
        finally:
            await db.close()
    
    async def update_slide(
        self,
        session_id: str,
        slide_number: int,
        new_version: SlideVersion
    ) -> Optional[SlideWithHistory]:
        """
        Add a new version to a slide.
        """
        db = await get_db_session()
        try:
            db_slide = await crud.get_slide(db, session_id, slide_number)
            if not db_slide:
                return None
            
            # Add new version
            updated_slide = await crud.update_slide_content(
                db=db,
                slide=db_slide,
                title=new_version.title,
                content=new_version.content,
                speaker_notes=new_version.speaker_notes,
                instruction=new_version.instruction
            )
            
            # Get fresh session to update cache
            db_session = await crud.get_session_by_uuid(db, session_id)
            session = self._db_session_to_schema(db_session)
            self.sessions[session_id] = session
            
            # Return the updated slide from cache
            for slide in session.slides:
                if slide.slide_number == slide_number:
                    return slide
            return None
        finally:
            await db.close()
    
    async def rollback_slide(
        self,
        session_id: str,
        slide_number: int,
        version_index: int
    ) -> Optional[SlideWithHistory]:
        """
        Rollback a slide to a previous version.
        """
        db = await get_db_session()
        try:
            db_slide = await crud.get_slide(db, session_id, slide_number)
            if not db_slide:
                return None
            
            # Rollback to version
            updated_slide = await crud.rollback_slide_version(db, db_slide, version_index)
            if not updated_slide:
                return None
            
            # Get fresh session to update cache
            db_session = await crud.get_session_by_uuid(db, session_id)
            session = self._db_session_to_schema(db_session)
            self.sessions[session_id] = session
            
            # Return the updated slide from cache
            for slide in session.slides:
                if slide.slide_number == slide_number:
                    return slide
            return None
        finally:
            await db.close()
    
    def get_context_for_ai(self, session: SessionData) -> str:
        """
        Build context string for AI from session data.
        
        This creates a summary of the presentation state for AI context.
        """
        context_parts = []
        
        # Add topic
        if session.topic:
            context_parts.append(f"Presentation Topic: {session.topic}")
        
        # Add template and tone
        context_parts.append(f"Template: {session.template.value}")
        context_parts.append(f"Tone: {session.tone.value}")
        
        # Add slide summaries
        if session.slides:
            context_parts.append("\nCurrent Slides:")
            for slide in session.slides:
                current = slide.versions[slide.current_version]
                context_parts.append(f"  Slide {slide.slide_number}: {current.title}")
        
        # Add recent context memory
        if session.context_memory:
            context_parts.append(f"\nContext: {session.context_memory}")
        
        # Add relevant recent chat history
        if session.chat_history:
            recent = session.chat_history[-5:]
            context_parts.append("\nRecent conversation:")
            for msg in recent:
                context_parts.append(f"  {msg.role}: {msg.content[:100]}...")
        
        return "\n".join(context_parts)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        # Remove from memory
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        # Remove from database
        db = await get_db_session()
        try:
            return await crud.delete_session(db, session_id)
        finally:
            await db.close()
    
    async def list_sessions(self) -> List[str]:
        """List all session IDs."""
        db = await get_db_session()
        try:
            sessions = await crud.list_sessions(db)
            return [s.session_id for s in sessions]
        finally:
            await db.close()


# Global session manager instance
session_manager = SessionManager()
