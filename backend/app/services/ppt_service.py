"""PPT Service - delegates rendering to the PPTRenderer

This module keeps the existing public surface but delegates presentation
rendering to `ppt_renderer` so styling is controlled centrally.
"""
import os
from typing import Optional
from datetime import datetime

from app.models.schemas import SessionData
from app.services.ppt_renderer import ppt_renderer


class PPTService:
    OUTPUT_DIR = "storage/outputs"

    def __init__(self):
        self._ensure_output_dir()
        self._session_render_cache = {}

    def _ensure_output_dir(self):
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def create_presentation(self, session: SessionData, filename: Optional[str] = None) -> str:
        """Create a presentation file from session data using the renderer."""
        cache_key = session.session_id
        session_stamp = str(getattr(session, "last_updated", ""))
        auto_filename = filename is None

        # Fast path: if session content hasn't changed, reuse last rendered file.
        if auto_filename:
            cached = self._session_render_cache.get(cache_key)
            if cached and cached.get("stamp") == session_stamp and os.path.exists(cached.get("path", "")):
                return cached["path"]

        # Build simplified slide data objects that renderer expects
        slides = []
        for slide_wh in session.slides:
            try:
                current = slide_wh.current
            except Exception:
                # support older objects where property may not exist
                current = slide_wh.versions[slide_wh.current_version]

            slides.append({
                'slide_number': slide_wh.slide_number,
                'title': current.title,
                'content': current.content,
                'speaker_notes': current.speaker_notes,
            })

        prs = ppt_renderer.render(slides, theme_name=session.template.value if hasattr(session.template, 'value') else session.template, title=session.topic)

        # filename
        if auto_filename:
            safe_topic = "".join(c if c.isalnum() or c in ' -_' else '_' for c in (session.topic or 'presentation'))
            safe_topic = safe_topic[:50]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_topic}_{timestamp}.pptx"

        filepath = os.path.join(self.OUTPUT_DIR, filename)
        prs.save(filepath)

        if auto_filename:
            self._session_render_cache[cache_key] = {
                "stamp": session_stamp,
                "path": filepath,
            }

        return filepath

    def get_output_path(self, filename: str) -> str:
        return os.path.join(self.OUTPUT_DIR, filename)

    def file_exists(self, filename: str) -> bool:
        return os.path.exists(self.get_output_path(filename))

    def delete_file(self, filename: str) -> bool:
        path = self.get_output_path(filename)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


# Global PPT service instance
ppt_service = PPTService()
