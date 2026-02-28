"""
Base LLM Provider Interface

All AI providers must implement this interface for consistent behavior.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class ProviderStatus(str, Enum):
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class ProviderResponse:
    """Standard response from any LLM provider."""
    success: bool
    content: str
    provider_name: str
    model: str
    tokens_used: Optional[int] = None
    error: Optional[str] = None
    

class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All AI providers (Groq, Gemini, OpenRouter, etc.) must implement this interface.
    This ensures consistent behavior and easy swapping between providers.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._status = ProviderStatus.AVAILABLE
        self._last_error: Optional[str] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass
    
    @property
    @abstractmethod
    def model(self) -> str:
        """Return the model being used."""
        pass
    
    @property
    def status(self) -> ProviderStatus:
        """Return current provider status."""
        return self._status
    
    @property
    def is_available(self) -> bool:
        """Check if provider is available for requests."""
        return self._status == ProviderStatus.AVAILABLE
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> ProviderResponse:
        """
        Generate text from the LLM.
        
        Args:
            prompt: The user prompt/question
            system_prompt: Optional system message for context
            temperature: Creativity level (0.0-1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            ProviderResponse with the generated content
        """
        pass
    
    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3
    ) -> ProviderResponse:
        """
        Generate JSON output from the LLM.
        
        Uses lower temperature for more consistent structured output.
        
        Args:
            prompt: The user prompt requesting JSON
            system_prompt: Optional system message
            temperature: Lower for more consistent output
            
        Returns:
            ProviderResponse with JSON string content
        """
        pass
    
    def mark_rate_limited(self, error_message: str = "Rate limited"):
        """Mark this provider as rate limited."""
        self._status = ProviderStatus.RATE_LIMITED
        self._last_error = error_message
    
    def mark_error(self, error_message: str):
        """Mark this provider as having an error."""
        self._status = ProviderStatus.ERROR
        self._last_error = error_message
    
    def mark_available(self):
        """Mark this provider as available again."""
        self._status = ProviderStatus.AVAILABLE
        self._last_error = None
    
    def get_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error
