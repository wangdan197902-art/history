"""Real Wikipedia 抓取器 - Phase 4 实现

⚠️ 此文件为占位,Phase 4 启用真实 API 时实现。
技术债务: TD-002
"""
from typing import Any

from src.models.event import EventPool
from src.providers.base import WikipediaFetcher


class RealWikipediaFetcher(WikipediaFetcher):
    """Real Wikipedia 实现 - 调用真实 Wikipedia API

    Phase 4 实现,目前抛出 NotImplementedError
    """

    def __init__(self, settings: Any):
        self.settings = settings
        raise NotImplementedError(
            "RealWikipediaFetcher 将在 Phase 4 实现。"
            "当前使用 MockWikipediaFetcher(ENV=local)。"
        )

    async def fetch_events(self, month: str, day: str, event_type: str = "all") -> EventPool:
        raise NotImplementedError("Phase 4 实现")

    async def fetch_year(self, year: int) -> dict[str, list[EventPool]]:
        raise NotImplementedError("Phase 4 实现")
