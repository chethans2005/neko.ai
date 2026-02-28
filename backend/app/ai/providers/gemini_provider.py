"""
Google Gemini API Provider

Gemini provides powerful AI models with a generous free tier.
Free tier: 60 requests/minute for gemini-1.5-flash.
"""
import os
import httpx
import json
from typing import Optional

from .base_provider import BaseLLMProvider, ProviderResponse, ProviderStatus


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini LLM Provider.
    
    Uses the Gemini API with free tier access.
    """
    
    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
    DEFAULT_MODEL = "gemini-2.0-flash"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("GEMINI_API_KEY"))
        self._model = self.DEFAULT_MODEL
        
        if not self.api_key:
            self._status = ProviderStatus.UNAVAILABLE
            self._last_error = "GEMINI_API_KEY not configured"
    
    @property
    def name(self) -> str:
        return "Gemini"
    
    @property
    def model(self) -> str:
        return self._model
    
    def _get_url(self) -> str:
        """Get the API URL with key."""
        return f"{self.API_BASE}/{self._model}:generateContent?key={self.api_key}"
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> ProviderResponse:
        """Generate text using Gemini API."""
        
        if not self.is_available:
            return ProviderResponse(
                success=False,
                content="",
                provider_name=self.name,
                model=self.model,
                error=self._last_error or "Provider unavailable"
            )
        
        # Build the content parts
        parts = []
        if system_prompt:
            parts.append({"text": f"System Instructions: {system_prompt}\n\n"})
        parts.append({"text": prompt})
        
        payload = {
            "contents": [
                {
                    "parts": parts
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topK": 40,
                "topP": 0.95
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self._get_url(),
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 429:
                    error_msg = "Rate limit exceeded"
                    self.mark_rate_limited(error_msg)
                    return ProviderResponse(
                        success=False,
                        content="",
                        provider_name=self.name,
                        model=self.model,
                        error=error_msg
                    )
                
                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                    self.mark_error(error_msg)
                    return ProviderResponse(
                        success=False,
                        content="",
                        provider_name=self.name,
                        model=self.model,
                        error=error_msg
                    )
                
                data = response.json()
                
                # Extract content from Gemini response
                candidates = data.get("candidates", [])
                if not candidates:
                    return ProviderResponse(
                        success=False,
                        content="",
                        provider_name=self.name,
                        model=self.model,
                        error="No response candidates"
                    )
                
                content_parts = candidates[0].get("content", {}).get("parts", [])
                content = "".join(part.get("text", "") for part in content_parts)
                
                # Get token count if available
                usage = data.get("usageMetadata", {})
                tokens = usage.get("totalTokenCount")
                
                self.mark_available()
                
                return ProviderResponse(
                    success=True,
                    content=content,
                    provider_name=self.name,
                    model=self.model,
                    tokens_used=tokens
                )
                
        except httpx.TimeoutException:
            error_msg = "Request timeout"
            self.mark_error(error_msg)
            return ProviderResponse(
                success=False,
                content="",
                provider_name=self.name,
                model=self.model,
                error=error_msg
            )
        except Exception as e:
            error_msg = str(e)
            self.mark_error(error_msg)
            return ProviderResponse(
                success=False,
                content="",
                provider_name=self.name,
                model=self.model,
                error=error_msg
            )
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3
    ) -> ProviderResponse:
        """Generate JSON output using Gemini API."""
        
        # Enhance system prompt to enforce JSON output
        json_system = system_prompt or ""
        json_system += "\n\nIMPORTANT: You MUST respond with valid JSON only. No markdown, no code blocks, no explanations. Just pure JSON."
        
        response = await self.generate_text(
            prompt=prompt,
            system_prompt=json_system,
            temperature=temperature,
            max_tokens=4096
        )
        
        if response.success:
            # Clean up potential markdown formatting
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Validate JSON
            try:
                json.loads(content)
                response.content = content
            except json.JSONDecodeError as e:
                response.success = False
                response.error = f"Invalid JSON response: {str(e)}"
        
        return response
