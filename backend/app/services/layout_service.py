from enum import Enum
from typing import Any, Dict


class LayoutType(str, Enum):
    TITLE_SLIDE = 'title'
    CONTENT_SLIDE = 'content'
    TWO_COLUMN = 'two_column'


class LayoutService:
    """Decides which layout to use for a slide based on content."""

    def choose_layout(self, slide: Dict[str, Any]) -> LayoutType:
        """Choose layout for a slide.

        Current behavior intentionally prefers single-column content slides.
        - If slide has no content -> TITLE_SLIDE
        - Otherwise -> CONTENT_SLIDE
        """
        content = slide.get('content') or []
        if not content:
            return LayoutType.TITLE_SLIDE
        return LayoutType.CONTENT_SLIDE


layout_service = LayoutService()
