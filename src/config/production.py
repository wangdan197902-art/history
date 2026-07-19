"""生产环境配置 - 使用真实 API

⚠️ Phase 4 启用,需配置 API keys
"""
from src.config.base import Settings


class ProductionSettings(Settings):
    """生产环境配置

    所有 provider 默认为 real,需配置真实 API key
    """
    ENV: str = "production"
    WIKIPEDIA_PROVIDER: str = "real"
    ANTHROPIC_PROVIDER: str = "real"
    OPENAI_PROVIDER: str = "real"
    GEMINI_PROVIDER: str = "real"
    BUTTONDOWN_PROVIDER: str = "real"
    GSC_PROVIDER: str = "real"
