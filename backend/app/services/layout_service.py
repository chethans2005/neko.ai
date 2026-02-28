from enum import Enum
from typing import Any, Dict


class LayoutType(str, Enum):
    TITLE_SLIDE = 'title'
    CONTENT_SLIDE = 'content'
    TWO_COLUMN = 'two_column'


class LayoutService:
    """Decides which layout to use for a slide based on content."""

    def choose_layout(self, slide: Dict[str, Any]) -> LayoutType:
        """Choose layout using simple heuristics based on content length.

        - If slide has no content -> TITLE_SLIDE
        - If content length <= 3 -> CONTENT_SLIDE
        - Else -> TWO_COLUMN
        """
        content = slide.get('content') or []
        if not content:
            return LayoutType.TITLE_SLIDE
        if len(content) <= 3:
            return LayoutType.CONTENT_SLIDE
        return LayoutType.TWO_COLUMN


layout_service = LayoutService()
