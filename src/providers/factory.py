"""Provider 工厂函数 - 通过 ENV 切换实现

根据 settings 中的 *_PROVIDER 字段决定实例化 Mock 或 Real 实现。
所有 import 都放在函数内部(延迟导入),避免循环依赖和不必要的模块加载。
"""
from typing import Any

from src.providers.base import (
    Auditor,
    Illustrator,
    Publisher,
    Regionalizer,
    Translator,
    WikipediaFetcher,
)


def get_wikipedia_fetcher(settings: Any) -> WikipediaFetcher:
    """获取 Wikipedia 抓取器"""
    provider = getattr(settings, "WIKIPEDIA_PROVIDER", "mock")
    if provider == "mock":
        from src.providers.impl.mock_wikipedia import MockWikipediaFetcher
        return MockWikipediaFetcher(settings)
    elif provider == "real":
        from src.providers.impl.real_wikipedia import RealWikipediaFetcher
        return RealWikipediaFetcher(settings)
    raise ValueError(f"Unknown Wikipedia provider: {provider}")


def get_regionalizer(settings: Any) -> Regionalizer:
    """获取地区化重写器"""
    provider = getattr(settings, "ANTHROPIC_PROVIDER", "mock")
    if provider == "mock":
        from src.providers.impl.mock_anthropic import MockAnthropicRegionalizer
        return MockAnthropicRegionalizer(settings)
    elif provider == "real":
        from src.providers.impl.real_anthropic import RealAnthropicRegionalizer
        return RealAnthropicRegionalizer(settings)
    raise ValueError(f"Unknown Anthropic provider: {provider}")


def get_translator(settings: Any) -> Translator:
    """获取翻译器"""
    provider = getattr(settings, "OPENAI_PROVIDER", "mock")
    if provider == "mock":
        from src.providers.impl.mock_openai import MockOpenAITranslator
        return MockOpenAITranslator(settings)
    elif provider == "real":
        from src.providers.impl.real_openai import RealOpenAITranslator
        return RealOpenAITranslator(settings)
    raise ValueError(f"Unknown OpenAI provider: {provider}")


def get_illustrator(settings: Any) -> Illustrator:
    """获取配图生成器"""
    provider = getattr(settings, "GEMINI_PROVIDER", "mock")
    if provider == "mock":
        from src.providers.impl.mock_gemini import MockGeminiIllustrator
        return MockGeminiIllustrator(settings)
    elif provider == "real":
        from src.providers.impl.real_gemini import RealGeminiIllustrator
        return RealGeminiIllustrator(settings)
    raise ValueError(f"Unknown Gemini provider: {provider}")


def get_auditor(settings: Any) -> Auditor:
    """获取审核器(使用 Gemini)"""
    provider = getattr(settings, "GEMINI_PROVIDER", "mock")
    if provider == "mock":
        from src.providers.impl.mock_gemini import MockGeminiAuditor
        return MockGeminiAuditor(settings)
    elif provider == "real":
        from src.providers.impl.real_gemini import RealGeminiAuditor
        return RealGeminiAuditor(settings)
    raise ValueError(f"Unknown Gemini provider: {provider}")


def get_publisher(settings: Any) -> Publisher:
    """获取发布器"""
    provider = getattr(settings, "BUTTONDOWN_PROVIDER", "mock")
    if provider == "mock":
        from src.providers.impl.mock_buttondown import MockButtondownPublisher
        return MockButtondownPublisher(settings)
    elif provider == "real":
        from src.providers.impl.real_buttondown import RealButtondownPublisher
        return RealButtondownPublisher(settings)
    raise ValueError(f"Unknown Buttondown provider: {provider}")


def get_provider(name: str, settings: Any):
    """通用 provider 获取(基于名称)

    Args:
        name: provider 名称,可选值:
            wikipedia / anthropic / openai / gemini_illustrator / gemini_auditor / buttondown
        settings: 配置对象

    Returns:
        对应的 provider 实例
    """
    factories = {
        "wikipedia": get_wikipedia_fetcher,
        "anthropic": get_regionalizer,
        "openai": get_translator,
        "gemini_illustrator": get_illustrator,
        "gemini_auditor": get_auditor,
        "buttondown": get_publisher,
    }
    if name not in factories:
        raise ValueError(f"Unknown provider name: {name}. Available: {list(factories.keys())}")
    return factories[name](settings)
