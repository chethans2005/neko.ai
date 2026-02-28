"""
Outline Service - AI-Powered Presentation Outline Generation

Generates presentation outlines based on topic and context.
"""
import json
from typing import List, Optional
from datetime import datetime

from app.ai.router import ai_router
from app.models.schemas import SlideContent, SlideWithHistory, SlideVersion, ToneType


class OutlineService:
    """
    Service for generating presentation outlines using AI.
    
    Creates structured outlines that can be converted to slides.
    """
    
    SYSTEM_PROMPT = """You are an expert presentation designer. Create clear, engaging, and well-structured presentation outlines.

Your task is to generate a presentation outline with the specified number of slides.

Each slide should have:
- A compelling title (max 10 words)
- 4-6 bullet points of substantive content (each bullet should be informative, 10-20 words)
- Optional speaker notes with additional context

Create comprehensive, detailed slides that provide real value. Avoid generic or vague bullet points.

Respond ONLY with valid JSON in this exact format:
{
    "slides": [
        {
            "title": "Slide Title",
            "content": ["Detailed bullet point 1", "Detailed bullet point 2", "Detailed bullet point 3", "Detailed bullet point 4", "Detailed bullet point 5"],
            "speaker_notes": "Optional notes for the presenter"
        }
    ]
}

Make the presentation flow logically from introduction to conclusion."""

    def _get_tone_instructions(self, tone: ToneType) -> str:
        """Get tone-specific instructions."""
        instructions = {
            ToneType.PROFESSIONAL: "Use formal, business-appropriate language. Focus on key metrics and outcomes.",
            ToneType.CASUAL: "Use conversational, friendly language. Make it engaging and approachable.",
            ToneType.TECHNICAL: "Use precise technical terminology. Include detailed specifications and technical concepts.",
            ToneType.CREATIVE: "Use dynamic, imaginative language. Include creative metaphors and engaging visuals descriptions.",
            ToneType.ACADEMIC: "Use scholarly language with proper citations format. Include theoretical frameworks and methodology.",
        }
        return instructions.get(tone, instructions[ToneType.PROFESSIONAL])

    async def generate_outline(
        self,
        topic: str,
        num_slides: int = 5,
        tone: ToneType = ToneType.PROFESSIONAL,
        context: Optional[str] = None,
        additional_instructions: Optional[str] = None
    ) -> List[SlideWithHistory]:
        """
        Generate a presentation outline.
        
        Args:
            topic: The presentation topic
            num_slides: Number of slides to generate
            tone: The presentation tone
            context: Previous context from session
            additional_instructions: Extra user instructions
            
        Returns:
            List of SlideWithHistory objects
        """
        # Build the prompt
        prompt_parts = [
            f"Create a {num_slides}-slide presentation about: {topic}",
            f"\nTone: {self._get_tone_instructions(tone)}"
        ]
        
        if context:
            prompt_parts.append(f"\nContext: {context}")
        
        if additional_instructions:
            prompt_parts.append(f"\nAdditional instructions: {additional_instructions}")
        
        prompt = "\n".join(prompt_parts)
        
        # Generate using AI
        response = await ai_router.generate_json(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.7
        )
        
        if not response.success:
            raise Exception(f"Failed to generate outline: {response.error}")
        
        # Parse the response
        try:
            data = json.loads(response.content)
            slides_data = data.get("slides", [])
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid AI response format: {e}")
        
        # Convert to SlideWithHistory objects
        slides = []
        for i, slide_data in enumerate(slides_data, 1):
            version = SlideVersion(
                version=0,
                title=slide_data.get("title", f"Slide {i}"),
                content=slide_data.get("content", []),
                speaker_notes=slide_data.get("speaker_notes"),
                created_at=datetime.now(),
                instruction="Initial generation"
            )
            
            slide = SlideWithHistory(
                slide_number=i,
                current_version=0,
                versions=[version]
            )
            slides.append(slide)
        
        return slides

    async def regenerate_slide(
        self,
        slide: SlideWithHistory,
        instruction: str,
        topic: str,
        tone: ToneType,
        context: Optional[str] = None,
        all_slides_summary: Optional[str] = None
    ) -> SlideVersion:
        """
        Regenerate a single slide based on user instruction.
        
        Args:
            slide: The current slide to modify
            instruction: User's modification instruction
            topic: Presentation topic for context
            tone: Presentation tone
            context: Session context
            all_slides_summary: Summary of all slides for coherence
            
        Returns:
            New SlideVersion
        """
        current = slide.versions[slide.current_version]
        
        system_prompt = f"""You are an expert presentation designer. Modify the given slide based on the user's instruction.

Current slide:
- Title: {current.title}
- Content: {json.dumps(current.content)}
- Speaker Notes: {current.speaker_notes or 'None'}

Presentation topic: {topic}
Tone: {self._get_tone_instructions(tone)}

Respond ONLY with valid JSON:
{{
    "title": "Updated slide title",
    "content": ["Updated bullet 1", "Updated bullet 2", "Updated bullet 3"],
    "speaker_notes": "Updated speaker notes"
}}"""

        prompt_parts = [f"Instruction: {instruction}"]
        
        if context:
            prompt_parts.append(f"Context: {context}")
        
        if all_slides_summary:
            prompt_parts.append(f"Other slides in presentation: {all_slides_summary}")
        
        prompt = "\n".join(prompt_parts)
        
        response = await ai_router.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5
        )
        
        if not response.success:
            raise Exception(f"Failed to regenerate slide: {response.error}")
        
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid AI response format: {e}")
        
        new_version = SlideVersion(
            version=len(slide.versions),
            title=data.get("title", current.title),
            content=data.get("content", current.content),
            speaker_notes=data.get("speaker_notes", current.speaker_notes),
            created_at=datetime.now(),
            instruction=instruction
        )
        
        return new_version


# Global outline service instance
outline_service = OutlineService()
