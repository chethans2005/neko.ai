"""PPT Service - delegates rendering to the PPTRenderer

This module keeps the existing public surface but delegates presentation
rendering to `ppt_renderer` so styling is controlled centrally.
"""
import os
import json
import hashlib
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

    def _build_fingerprint(self, session: SessionData, slides: list[dict]) -> str:
        payload = {
            "topic": session.topic,
            "template": session.template.value if hasattr(session.template, "value") else session.template,
            "slides": slides,
        }
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def create_presentation(self, session: SessionData, filename: Optional[str] = None) -> str:
        """Create a presentation file from session data using the renderer."""
        cache_key = session.session_id
        auto_filename = filename is None

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

        fingerprint = self._build_fingerprint(session, slides)

        # Fast path: if rendered payload hasn't changed, reuse last generated file.
        if auto_filename:
            cached = self._session_render_cache.get(cache_key)
            if cached and cached.get("fingerprint") == fingerprint and os.path.exists(cached.get("path", "")):
                return cached["path"]

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
                "fingerprint": fingerprint,
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
