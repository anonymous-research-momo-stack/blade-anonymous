"""
Model Factory for LLM providers
支持多种LLM提供商：OpenAI, Anthropic, Ollama
"""

from typing import Optional
from loguru import logger

from app.config import settings


def create_model(provider: Optional[str] = None, model_id: Optional[str] = None):
    """
    根据配置创建对应的LLM模型
    
    Args:
        provider: LLM提供商 ("openai", "anthropic", "ollama")
        model_id: 模型ID
        
    Returns:
        LLM模型实例
        
    Raises:
        ValueError: 当提供商不支持或配置错误时
    """
    # 使用配置中的默认值
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
    """创建OpenAI模型"""
    from agno.models.openai import OpenAIChat

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required for OpenAI models")

    return OpenAIChat(
        id=model_id,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,  # 添加temperature参数，设为0获得最大确定性
        seed=66,        # 添加seed参数，确保可重现性
    )


def _create_anthropic_model(model_id: str):
    """创建Anthropic模型"""
    from agno.models.anthropic import Claude

    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is required for Anthropic models")

    return Claude(
        id=model_id,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0,  # 添加temperature参数，虽然不能完全确定性，但能减少随机性
        # 注意：Anthropic不支持seed参数
    )


def _create_ollama_model(model_id: str):
    """创建Ollama模型"""
    from agno.models.ollama import Ollama

    # Ollama的base_url参数根据文档应该传递给构造函数
    kwargs = {
        "id": model_id,
        "temperature": 0,  # 添加temperature参数
        # Ollama可能支持seed，具体取决于底层模型
    }

    if settings.OLLAMA_BASE_URL:
        kwargs["base_url"] = settings.OLLAMA_BASE_URL

    return Ollama(**kwargs)


def get_supported_providers():
    """获取支持的LLM提供商列表"""
    return ["openai", "anthropic", "ollama"]


def get_default_model_config():
    """获取默认模型配置"""
    return {
        "provider": settings.LLM_PROVIDER,
        "model_id": settings.LLM_MODEL_ID
    }