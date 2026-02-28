"""
AI Router - Multi-Provider Automatic Switching

This module handles automatic switching between AI providers
when one fails due to rate limits or errors.
"""
import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from .providers.base_provider import BaseLLMProvider, ProviderResponse, ProviderStatus
from .providers.groq_provider import GroqProvider
from .providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class AIRouter:
    """
    Routes AI requests to available providers with automatic failover.
    
    Implements:
    - Automatic provider switching on failure
    - Rate limit cooldown periods
    - Provider health tracking
    - Graceful degradation
    """
    
    COOLDOWN_MINUTES = 1  # Wait before retrying a rate-limited provider
    
    def __init__(self):
        self.providers: List[BaseLLMProvider] = []
        self._cooldowns: dict[str, datetime] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all configured providers in priority order."""
        # Add providers in order of preference
        groq = GroqProvider()
        gemini = GeminiProvider()
        
        # Only add providers that have API keys configured
        if groq.status != ProviderStatus.UNAVAILABLE:
            self.providers.append(groq)
            logger.info(f"✓ Groq provider initialized ({groq.model})")
        else:
            logger.warning("✗ Groq provider unavailable (no API key)")
        
        if gemini.status != ProviderStatus.UNAVAILABLE:
            self.providers.append(gemini)
            logger.info(f"✓ Gemini provider initialized ({gemini.model})")
        else:
            logger.warning("✗ Gemini provider unavailable (no API key)")
        
        if not self.providers:
            logger.error("No AI providers available! Check your API keys.")
    
    def _is_in_cooldown(self, provider_name: str) -> bool:
        """Check if a provider is in cooldown period."""
        if provider_name not in self._cooldowns:
            return False
        
        cooldown_end = self._cooldowns[provider_name]
        if datetime.now() > cooldown_end:
            del self._cooldowns[provider_name]
            return False
        
        return True
    
    def _set_cooldown(self, provider_name: str):
        """Set cooldown for a provider."""
        self._cooldowns[provider_name] = datetime.now() + timedelta(minutes=self.COOLDOWN_MINUTES)
        logger.warning(f"Provider {provider_name} in cooldown for {self.COOLDOWN_MINUTES} minutes")
    
    def get_available_providers(self) -> List[BaseLLMProvider]:
        """Get list of currently available providers."""
        available = []
        for provider in self.providers:
            if not self._is_in_cooldown(provider.name):
                if provider.status in [ProviderStatus.AVAILABLE, ProviderStatus.ERROR]:
                    available.append(provider)
        return available
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> ProviderResponse:
        """
        Generate text using available providers with automatic failover.
        
        Tries each provider in order until one succeeds.
        """
        available = self.get_available_providers()
        
        if not available:
            return ProviderResponse(
                success=False,
                content="",
                provider_name="none",
                model="none",
                error="All AI providers are currently unavailable. Please try again later."
            )
        
        last_error = None
        
        for provider in available:
            logger.info(f"Trying provider: {provider.name}")
            
            try:
                response = await provider.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                if response.success:
                    logger.info(f"Success with {provider.name}")
                    return response
                
                # Handle specific errors
                if provider.status == ProviderStatus.RATE_LIMITED:
                    self._set_cooldown(provider.name)
                
                last_error = response.error
                logger.warning(f"Provider {provider.name} failed: {response.error}")
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Exception with {provider.name}: {e}")
                continue
        
        return ProviderResponse(
            success=False,
            content="",
            provider_name="none",
            model="none",
            error=f"All providers failed. Last error: {last_error}"
        )
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3
    ) -> ProviderResponse:
        """
        Generate JSON using available providers with automatic failover.
        """
        available = self.get_available_providers()
        
        if not available:
            return ProviderResponse(
                success=False,
                content="",
                provider_name="none",
                model="none",
                error="All AI providers are currently unavailable. Please try again later."
            )
        
        last_error = None
        
        for provider in available:
            logger.info(f"Trying provider for JSON: {provider.name}")
            
            try:
                response = await provider.generate_json(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature
                )
                
                if response.success:
                    logger.info(f"JSON success with {provider.name}")
                    return response
                
                if provider.status == ProviderStatus.RATE_LIMITED:
                    self._set_cooldown(provider.name)
                
                last_error = response.error
                logger.warning(f"Provider {provider.name} JSON failed: {response.error}")
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Exception with {provider.name}: {e}")
                continue
        
        return ProviderResponse(
            success=False,
            content="",
            provider_name="none",
            model="none",
            error=f"All providers failed for JSON generation. Last error: {last_error}"
        )
    
    def get_status(self) -> dict:
        """Get status of all providers."""
        status = {}
        for provider in self.providers:
            status[provider.name] = {
                "status": provider.status.value,
                "model": provider.model,
                "in_cooldown": self._is_in_cooldown(provider.name),
                "last_error": provider.get_error()
            }
        return status


# Global router instance
ai_router = AIRouter()
