"""
Model Factory for LLM providers
Supports multiple LLM providers: OpenAI, Anthropic, Ollama
"""

from typing import Optional
from loguru import logger

from app.config import settings


def create_model(provider: Optional[str] = None, model_id: Optional[str] = None):
    """
    Create the corresponding LLM model based on configuration

    Args:
        provider: LLM provider ("openai", "anthropic", "ollama")
        model_id: Model ID

    Returns:
        LLM model instance

    Raises:
        ValueError: When provider is unsupported or configuration is invalid
    """
    # Use defaults from configuration
    provider = provider or settings.LLM_PROVIDER
    model_id = model_id or settings.LLM_MODEL_ID
    
    logger.debug(f"Creating model: provider={provider}, model_id={model_id}")
    
    try:
        if provider.lower() == "openai":
            return _create_openai_model(model_id)
        elif provider.lower() == "anthropic":
            return _create_anthropic_model(model_id)
        elif provider.lower() == "ollama":
            return _create_ollama_model(model_id)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    except Exception as e:
        logger.error(f"Failed to create model: {e}")
        raise


def _create_openai_model(model_id: str):
    """Create OpenAI model"""
    from agno.models.openai import OpenAIChat

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required for OpenAI models")

    return OpenAIChat(
        id=model_id,
        api_key=settings.OPENAI_API_KEY,
        temperature=1,  # Add temperature parameter; set to 0 for maximum determinism if needed
        seed=42,        # Add seed parameter to improve reproducibility
    )


def _create_anthropic_model(model_id: str):
    """Create Anthropic model"""
    from agno.models.anthropic import Claude

    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is required for Anthropic models")

    return Claude(
        id=model_id,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=1,  # Add temperature parameter; Anthropic cannot be fully deterministic but this reduces randomness
        # Note: Anthropic does not support a seed parameter
    )


def _create_ollama_model(model_id: str):
    """Create Ollama model"""
    from agno.models.ollama import Ollama

    kwargs = {
        "id": model_id,
    }

    if settings.OLLAMA_BASE_URL:
        kwargs["host"] = settings.OLLAMA_BASE_URL

    return Ollama(**kwargs)
def get_supported_providers():
    """Get list of supported LLM providers"""
    return ["openai", "anthropic", "ollama"]


def get_default_model_config():
    """Get default model configuration"""
    return {
        "provider": settings.LLM_PROVIDER,
        "model_id": settings.LLM_MODEL_ID
    }