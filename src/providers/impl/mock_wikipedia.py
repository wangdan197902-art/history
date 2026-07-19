"""Mock Wikipedia 抓取器 - 调用 Flask Mock Server"""
from typing import Any

import httpx

from src.models.event import Event, EventPool
from src.providers.base import WikipediaFetcher


class MockWikipediaFetcher(WikipediaFetcher):
    """Mock Wikipedia 实现 - 通过 HTTP 调用 Flask Mock Server"""

    def __init__(self, settings: Any):
        self.settings = settings
        self.base_url = f"http://{settings.MOCK_SERVER_HOST}:{settings.MOCK_SERVER_PORT}/wikipedia"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_events(self, month: str, day: str, event_type: str = "all") -> EventPool:
        """从 Mock Server 获取事件"""
        url = f"{self.base_url}/onthisday/{event_type}/{month}/{day}"
        # 从 Mock Server 加载所有 30 个地区的事件
        # 这里简化:只取 CN 作为示例,实际批量处理在 pipeline
        country_code = "CN"  # 默认地区
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()

        # 将 Wikipedia 响应转换为 EventPool
        events = []
        for wiki_event in data.get("events", []):
            events.append(Event(
                id=f"evt_{month}{day}_{country_code}_{len(events):03d}",
                date=f"2024-{month}-{day}",
                year=wiki_event.get("year", 2000),
                title=wiki_event.get("text", "")[:100],
                description=wiki_event.get("text", ""),
                wikipedia_url=wiki_event.get("pages", [{}])[0].get("content_urls", {}).get("page", ""),
                categories=wiki_event.get("categories", []),
            ))

        return EventPool(
            date=f"2024-{month}-{day}",
            country_code=country_code,
            events=events,
            source="wikipedia_mock",
            fetched_at="2024-01-01T00:00:00Z",
        )

    async def fetch_year(self, year: int) -> dict[str, list[EventPool]]:
        """抓取全年事件(简化版)"""
        # Mock: 返回空字典,实际由 pipeline 分批调用 fetch_events
        return {}

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
