"""
LLM Provider Factory
Provides a unified interface for different LLM providers (OpenAI, Mistral, etc.)
Allows easy swapping between providers via environment configuration
"""

import os
import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        response_format: Optional[Dict] = None,
        timeout: float = 30.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a chat completion using the provider's API.

        Returns a normalized response dictionary with:
        - content: str (the response text)
        - model: str (model used)
        - usage: dict (token usage stats)
        - raw_response: original API response object
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Return list of available models for this provider"""
        pass

    @abstractmethod
    def supports_structured_output(self, model: str) -> bool:
        """Check if the model supports JSON schema structured outputs"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation"""

    # Models that support structured outputs (JSON schema)
    STRUCTURED_OUTPUT_MODELS = {
        "gpt-4o-mini",
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-11-20",
        "gpt-4o",
    }

    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "o1-mini",
        "o1-preview",
    ]

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI provider with API key"""
        from openai import OpenAI

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=self.api_key)
        logger.info("Initialized OpenAI provider")

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        response_format: Optional[Dict] = None,
        timeout: float = 30.0,
        **kwargs
    ) -> Dict[str, Any]:
        """Create chat completion using OpenAI API"""

        # Build API parameters
        api_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            **kwargs  # Allow additional OpenAI-specific params
        }

        # Add response format if provided
        if response_format:
            api_params["response_format"] = response_format

        # Make API call
        response = self.client.chat.completions.create(**api_params)

        # Normalize response
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            "raw_response": response
        }

    def get_available_models(self) -> List[str]:
        """Return list of available OpenAI models"""
        return self.AVAILABLE_MODELS

    def supports_structured_output(self, model: str) -> bool:
        """Check if model supports JSON schema structured outputs"""
        return model in self.STRUCTURED_OUTPUT_MODELS


class MistralProvider(LLMProvider):
    """Mistral AI provider implementation"""

    AVAILABLE_MODELS = [
        "mistral-large-latest",
        "mistral-small-latest",
        "mistral-medium-latest",
        "open-mistral-7b",
        "open-mixtral-8x7b",
        "open-mixtral-8x22b",
    ]

    # Mistral supports JSON mode but not full JSON schema yet
    JSON_MODE_MODELS = {
        "mistral-large-latest",
        "mistral-small-latest",
        "mistral-medium-latest",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Mistral provider with API key"""
        from mistralai import Mistral

        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY not found in environment variables")

        self.client = Mistral(api_key=self.api_key)
        logger.info("Initialized Mistral provider")

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        response_format: Optional[Dict] = None,
        timeout: float = 30.0,
        **kwargs
    ) -> Dict[str, Any]:
        """Create chat completion using Mistral API"""

        # Build API parameters
        api_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs  # Allow additional Mistral-specific params
        }

        # Handle response format
        if response_format:
            response_type = response_format.get("type")

            if response_type == "json_schema":
                # Mistral doesn't support full JSON schema yet, fall back to json_object
                logger.warning(f"Mistral doesn't support JSON schema, falling back to JSON mode for model {model}")
                if model in self.JSON_MODE_MODELS:
                    api_params["response_format"] = {"type": "json_object"}
            elif response_type == "json_object":
                # Mistral supports JSON mode
                if model in self.JSON_MODE_MODELS:
                    api_params["response_format"] = {"type": "json_object"}
                else:
                    logger.warning(f"Model {model} may not support JSON mode")

        # Make API call (Mistral SDK uses chat.complete())
        response = self.client.chat.complete(**api_params)

        # Normalize response
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            "raw_response": response
        }

    def get_available_models(self) -> List[str]:
        """Return list of available Mistral models"""
        return self.AVAILABLE_MODELS

    def supports_structured_output(self, model: str) -> bool:
        """Mistral doesn't support full JSON schema yet, only JSON mode"""
        return False


class LLMProviderFactory:
    """Factory class for creating LLM provider instances"""

    # Default models per provider
    DEFAULT_MODELS = {
        "openai": "gpt-4o-mini",
        "mistral": "mistral-small-latest",
    }

    @staticmethod
    def create_provider(provider_name: Optional[str] = None) -> LLMProvider:
        """
        Create an LLM provider instance based on configuration.

        Args:
            provider_name: Provider to use ("openai", "mistral").
                         If None, reads from LLM_PROVIDER env var (default: "mistral")

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If provider is not supported or API key is missing
        """
        # Determine provider from parameter or environment
        if provider_name is None:
            provider_name = os.getenv("LLM_PROVIDER", "mistral").lower()
        else:
            provider_name = provider_name.lower()

        logger.info(f"Creating LLM provider: {provider_name}")

        # Create provider instance
        if provider_name == "openai":
            return OpenAIProvider()
        elif provider_name == "mistral":
            return MistralProvider()
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider_name}. "
                f"Supported providers: openai, mistral"
            )

    @staticmethod
    def get_default_model(provider_name: Optional[str] = None) -> str:
        """
        Get the default model for a provider.

        Args:
            provider_name: Provider name. If None, uses LLM_PROVIDER env var

        Returns:
            Default model name
        """
        if provider_name is None:
            provider_name = os.getenv("LLM_PROVIDER", "mistral").lower()
        else:
            provider_name = provider_name.lower()

        return LLMProviderFactory.DEFAULT_MODELS.get(provider_name, "mistral-small-latest")


# Convenience function for backward compatibility
def get_llm_client(provider_name: Optional[str] = None) -> LLMProvider:
    """
    Get an LLM provider client instance.

    This is a convenience function that wraps LLMProviderFactory.create_provider()
    for easier imports in service files.

    Args:
        provider_name: Provider to use ("openai", "mistral")

    Returns:
        LLMProvider instance
    """
    return LLMProviderFactory.create_provider(provider_name)