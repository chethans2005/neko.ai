"""Example usage for PPT renderer - creates a sample presentation."""
from datetime import datetime
import os

from app.services.ppt_renderer import ppt_renderer


def create_example_presentation(theme: str = 'professional', out_dir: str = 'storage/outputs') -> str:
    slides = [
        { 'slide_number': 1, 'title': 'Welcome', 'content': [], 'speaker_notes': 'Opening remarks' },
        { 'slide_number': 2, 'title': 'Agenda', 'content': ['Introduction', 'Problem', 'Solution', 'Next Steps'], 'speaker_notes': '' },
        { 'slide_number': 3, 'title': 'Key Metrics', 'content': ['Growth 45%', 'Retention 72%', 'ARR $5.2M'], 'speaker_notes': 'Discuss KPIs' },
        { 'slide_number': 4, 'title': 'Conclusion', 'content': ['Summary of results', 'Call to action'], 'speaker_notes': '' },
    ]

    prs = ppt_renderer.render(slides, theme_name=theme, title='Demo Presentation')

    os.makedirs(out_dir, exist_ok=True)
    filename = f"demo_{theme}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
    path = os.path.join(out_dir, filename)
    prs.save(path)
    return path


if __name__ == '__main__':
    path = create_example_presentation('professional')
    print('Created demo presentation at:', path)
