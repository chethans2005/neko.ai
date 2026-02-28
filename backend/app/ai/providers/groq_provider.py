"""
Groq API Provider

Groq provides extremely fast inference for open-source models.
Free tier: 14,400 requests/day for llama models.
"""
import os
import httpx
import json
from typing import Optional
import asyncio

from .base_provider import BaseLLMProvider, ProviderResponse, ProviderStatus


class GroqProvider(BaseLLMProvider):
    """
    Groq LLM Provider using their REST API.
    
    Supports Llama 3, Mixtral, and other fast inference models.
    """
    
    API_BASE = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "llama-3.1-8b-instant"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("GROQ_API_KEY"))
        self._model = self.DEFAULT_MODEL
        
        if not self.api_key:
            self._status = ProviderStatus.UNAVAILABLE
            self._last_error = "GROQ_API_KEY not configured"
    
    @property
    def name(self) -> str:
        return "Groq"
    
    @property
    def model(self) -> str:
        return self._model
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> ProviderResponse:
        """Generate text using Groq API."""
        
        if not self.is_available:
            return ProviderResponse(
                success=False,
                content="",
                provider_name=self.name,
                model=self.model,
                error=self._last_error or "Provider unavailable"
            )
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.API_BASE,
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
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens")
                
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
        """Generate JSON output using Groq API."""
        
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
