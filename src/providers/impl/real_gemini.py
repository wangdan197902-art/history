"""Real Gemini 配图生成器和审核器 - Phase 4 实现

⚠️ 此文件为占位,Phase 4 启用真实 API 时实现。
技术债务: TD-002
"""
from typing import Any

from src.models.event import AuditedEvent, IllustratedEvent, TranslatedEvent
from src.providers.base import Auditor, Illustrator


class RealGeminiIllustrator(Illustrator):
    """Real Gemini 实现 - 调用真实 Gemini API 生成配图

    Phase 4 实现,目前抛出 NotImplementedError
    """

    def __init__(self, settings: Any):
        self.settings = settings
        raise NotImplementedError(
            "RealGeminiIllustrator 将在 Phase 4 实现。"
            "当前使用 MockGeminiIllustrator(ENV=local)。"
        )

    async def illustrate(self, translated: TranslatedEvent) -> IllustratedEvent:
        raise NotImplementedError("Phase 4 实现")


class RealGeminiAuditor(Auditor):
    """Real Gemini 实现 - 调用真实 Gemini API 审核内容

    Phase 4 实现,目前抛出 NotImplementedError
    """

    def __init__(self, settings: Any):
        self.settings = settings
        raise NotImplementedError(
            "RealGeminiAuditor 将在 Phase 4 实现。"
            "当前使用 MockGeminiAuditor(ENV=local)。"
        )

    async def audit(self, illustrated: IllustratedEvent) -> AuditedEvent:
        raise NotImplementedError("Phase 4 实现")
