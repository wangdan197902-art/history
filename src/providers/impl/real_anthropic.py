"""Real Anthropic 地区化重写器 - Phase 4 实现

⚠️ 此文件为占位,Phase 4 启用真实 API 时实现。
技术债务: TD-002
"""
from typing import Any

from src.models.event import Event, EventPool, RegionalizedEvent
from src.providers.base import Regionalizer


class RealAnthropicRegionalizer(Regionalizer):
    """Real Anthropic 实现 - 调用真实 Claude API

    Phase 4 实现,目前抛出 NotImplementedError
    """

    def __init__(self, settings: Any):
        self.settings = settings
        raise NotImplementedError(
            "RealAnthropicRegionalizer 将在 Phase 4 实现。"
            "当前使用 MockAnthropicRegionalizer(ENV=local)。"
        )

    async def regionalize(self, event: Event, country_code: str) -> RegionalizedEvent:
        raise NotImplementedError("Phase 4 实现")

    async def regionalize_pool(self, pool: EventPool) -> list[RegionalizedEvent]:
        raise NotImplementedError("Phase 4 实现")
