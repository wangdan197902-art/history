"""本地环境配置 - 强制使用 Mock"""
from src.config.base import Settings


class LocalSettings(Settings):
    """本地环境配置

    强制所有 provider 为 mock,确保不调用真实 API
    """
    ENV: str = "local"
    WIKIPEDIA_PROVIDER: str = "mock"
    ANTHROPIC_PROVIDER: str = "mock"
    OPENAI_PROVIDER: str = "mock"
    GEMINI_PROVIDER: str = "mock"
    BUTTONDOWN_PROVIDER: str = "mock"
    GSC_PROVIDER: str = "mock"
