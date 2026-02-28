from pptx.dml.color import RGBColor


THEMES = {
    "professional": {
        "background": "1E1E2E",
        "title": "FFFFFF",
        "text": "E2E8F0",
        "accent": "4F46E5",
    },
    "startup": {
        "background": "F8FAFC",
        "title": "0F172A",
        "text": "334155",
        "accent": "06B6D4",
    },
    "academic": {
        "background": "FFFFFF",
        "title": "111827",
        "text": "374151",
        "accent": "2563EB",
    },
    "dark_modern": {
        "background": "0F172A",
        "title": "F8FAFC",
        "text": "CBD5E1",
        "accent": "22D3EE",
    },
}


def _hex_to_rgbcolor(hex_str: str) -> RGBColor:
    """Convert hex string (e.g. '1E1E2E') to pptx RGBColor."""
    h = hex_str.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return RGBColor(r, g, b)


class ThemeService:
    def __init__(self, themes: dict):
        self._themes = themes

    def get_theme(self, name: str) -> dict:
        """Return theme with RGBColor values. Falls back to 'professional'."""
        data = self._themes.get(name, self._themes.get('professional'))
        return {
            'background': _hex_to_rgbcolor(data['background']),
            'title': _hex_to_rgbcolor(data['title']),
            'text': _hex_to_rgbcolor(data['text']),
            'accent': _hex_to_rgbcolor(data['accent']),
        }


theme_service = ThemeService(THEMES)
