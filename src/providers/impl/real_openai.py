"""Real OpenAI 翻译器 - Phase 4 实现

⚠️ 此文件为占位,Phase 4 启用真实 API 时实现。
技术债务: TD-002
"""
from typing import Any

from src.models.event import RegionalizedEvent, TranslatedEvent
from src.providers.base import Translator


class RealOpenAITranslator(Translator):
    """Real OpenAI 实现 - 调用真实 GPT-4o API

    Phase 4 实现,目前抛出 NotImplementedError
    """

    def __init__(self, settings: Any):
        self.settings = settings
        raise NotImplementedError(
            "RealOpenAITranslator 将在 Phase 4 实现。"
            "当前使用 MockOpenAITranslator(ENV=local)。"
        )

    async def translate(self, regionalized: RegionalizedEvent, target_lang: str) -> TranslatedEvent:
        raise NotImplementedError("Phase 4 实现")

    async def translate_to_all_langs(
        self, regionalized: RegionalizedEvent, target_langs: list[str]
    ) -> list[TranslatedEvent]:
        raise NotImplementedError("Phase 4 实现")
