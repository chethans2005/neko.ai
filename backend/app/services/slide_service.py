"""
Slide Service - Slide Management and Operations

Handles slide-level operations including updates, versioning, and formatting.
"""
from typing import List, Optional
from datetime import datetime

from app.models.schemas import SlideWithHistory, SlideVersion, SessionData, ToneType
from app.services.outline_service import outline_service
from app.services.session_service import session_manager


class SlideService:
    """
    Service for managing individual slides.
    
    Handles:
    - Slide updates with version history
    - Incremental regeneration
    - Slide formatting and validation
    """
    
    async def update_slide(
        self,
        session_id: str,
        slide_number: int,
        instruction: str
    ) -> Optional[SlideWithHistory]:
        """
        Update a specific slide based on natural language instruction.
        
        Args:
            session_id: The session ID
            slide_number: 1-based slide number
            instruction: Natural language instruction for modification
            
        Returns:
            Updated SlideWithHistory or None if failed
        """
        session = await session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        slide_idx = slide_number - 1
        if slide_idx < 0 or slide_idx >= len(session.slides):
            raise ValueError(f"Slide {slide_number} not found")
        
        slide = session.slides[slide_idx]
        
        # Build summary of other slides for context
        other_slides = []
        for s in session.slides:
            if s.slide_number != slide_number:
                current = s.versions[s.current_version]
                other_slides.append(f"Slide {s.slide_number}: {current.title}")
        
        # Get session context
        context = session_manager.get_context_for_ai(session)
        
        # Generate new version
        new_version = await outline_service.regenerate_slide(
            slide=slide,
            instruction=instruction,
            topic=session.topic or "General",
            tone=session.tone,
            context=context,
            all_slides_summary="\n".join(other_slides) if other_slides else None
        )
        
        # Update slide with new version
        updated_slide = await session_manager.update_slide(
            session_id=session_id,
            slide_number=slide_number,
            new_version=new_version
        )
        
        # Add to chat history
        await session_manager.add_chat_message(
            session_id=session_id,
            role="user",
            content=instruction,
            related_slide=slide_number
        )
        
        await session_manager.add_chat_message(
            session_id=session_id,
            role="assistant",
            content=f"Updated slide {slide_number}: {new_version.title}",
            related_slide=slide_number
        )
        
        return updated_slide
    
    async def rollback_slide(
        self,
        session_id: str,
        slide_number: int,
        version_index: int
    ) -> Optional[SlideWithHistory]:
        """
        Rollback a slide to a previous version.
        """
        slide = await session_manager.rollback_slide(
            session_id=session_id,
            slide_number=slide_number,
            version_index=version_index
        )
        
        if slide:
            current = slide.versions[slide.current_version]
            await session_manager.add_chat_message(
                session_id=session_id,
                role="assistant",
                content=f"Rolled back slide {slide_number} to version {version_index}: {current.title}",
                related_slide=slide_number
            )
        
        return slide
    
    def get_slides_summary(self, slides: List[SlideWithHistory]) -> str:
        """
        Get a text summary of all slides.
        """
        summary_parts = []
        for slide in slides:
            current = slide.versions[slide.current_version]
            bullet_summary = ", ".join(current.content[:2]) if current.content else "No content"
            summary_parts.append(f"Slide {slide.slide_number}: {current.title} ({bullet_summary}...)")
        
        return "\n".join(summary_parts)
    
    def validate_slide_content(self, slide: SlideVersion) -> List[str]:
        """
        Validate slide content and return any warnings.
        """
        warnings = []
        
        # Check title length
        if len(slide.title) > 100:
            warnings.append("Title is too long (>100 characters)")
        
        # Check bullet points
        if len(slide.content) > 7:
            warnings.append("Too many bullet points (max 7 recommended)")
        
        for i, bullet in enumerate(slide.content, 1):
            if len(bullet) > 200:
                warnings.append(f"Bullet {i} is too long (>200 characters)")
        
        return warnings


# Global slide service instance
slide_service = SlideService()
