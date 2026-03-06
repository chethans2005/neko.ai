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
    
    SYSTEM_PROMPT = """You are a senior presentation strategist.

Return ONLY strict JSON (no markdown, no commentary) with this schema:
{
    "slides": [
        {
            "title": "string",
            "content": ["string", "string", "string", "string"],
            "speaker_notes": "string"
        }
    ]
}

Quality rules:
- Produce exactly the requested number of slides.
- Each slide title: 4-10 words, specific and outcome-oriented.
- Each slide content: exactly 4 concise bullets; each bullet 8-16 words.
- Avoid generic filler, repetition, and buzzwords.
- Keep bullets mutually distinct and logically sequenced.
- Keep facts plausible; do not invent precise statistics unless asked.
- speaker_notes: 1-2 short sentences with delivery guidance.

Structure rules:
- Slide flow should progress logically from context → analysis → actions → conclusion.
- When the topic is strategic/business, include at least one slide with metrics/KPIs framework.
- When the topic is technical, include architecture/trade-off perspective.
"""

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

    def _build_outline_prompt(
        self,
        topic: str,
        num_slides: int,
        tone: ToneType,
        context: Optional[str] = None,
        additional_instructions: Optional[str] = None,
    ) -> str:
        parts = [
            f"Topic: {topic}",
            f"Slides required: {num_slides}",
            f"Tone guidance: {self._get_tone_instructions(tone)}",
        ]

        if context:
            parts.append(f"Prior context: {context}")

        if additional_instructions:
            parts.append(f"Additional constraints: {additional_instructions}")

        parts.append("Ensure output is valid JSON and follows the required schema exactly.")
        return "\n".join(parts)

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
        prompt = self._build_outline_prompt(
            topic=topic,
            num_slides=num_slides,
            tone=tone,
            context=context,
            additional_instructions=additional_instructions,
        )
        
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
        
        system_prompt = f"""You are a senior presentation editor. Modify the slide according to user instruction while preserving coherence with the deck.

Current slide:
- Title: {current.title}
- Content: {json.dumps(current.content)}
- Speaker Notes: {current.speaker_notes or 'None'}

Presentation topic: {topic}
Tone: {self._get_tone_instructions(tone)}

Return ONLY valid JSON with this schema:
{{
    "title": "Updated slide title",
    "content": ["Updated bullet 1", "Updated bullet 2", "Updated bullet 3", "Updated bullet 4"],
    "speaker_notes": "Updated speaker notes"
}}

Rules:
- Keep title specific (4-10 words).
- Return exactly 4 concise bullets (8-16 words each).
- Preserve factual consistency with existing slide unless user asks to change facts.
- Prefer concrete, actionable wording over generic statements.
"""

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
