"""Mock Anthropic 地区化重写器"""
from typing import Any

import httpx

from src.models.event import Event, EventPool, RegionalizedEvent
from src.providers.base import Regionalizer


class MockAnthropicRegionalizer(Regionalizer):
    """Mock Anthropic 实现 - 地区化重写"""

    def __init__(self, settings: Any):
        self.settings = settings
        self.base_url = f"http://{settings.MOCK_SERVER_HOST}:{settings.MOCK_SERVER_PORT}/anthropic"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def regionalize(self, event: Event, country_code: str) -> RegionalizedEvent:
        """调用 Mock Claude API 进行地区化重写"""
        prompt = f"事件:{event.title}\n地区:{country_code}\n请重写为地区化版本,保持中立:"

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2048,
            "system": "你是历史事件地区化专家,请将事件用中立的语气重写,突出与指定地区的关联。",
            "messages": [{"role": "user", "content": prompt}],
        }

        response = await self.client.post(
            f"{self.base_url}/messages",
            json=payload,
            headers={"x-api-key": "mock-key"},
        )
        response.raise_for_status()
        data = response.json()

        rewritten_text = data.get("content", [{}])[0].get("text", event.description)

        return RegionalizedEvent(
            original=event,
            country_code=country_code,
            regional_title=event.title,
            regional_description=rewritten_text,
            neutrality_score=0.85,  # Mock 评分
            regional_tags=[country_code.lower(), "regionalized"],
            rewrite_log=f"Mock Claude regionalized for {country_code}",
        )

    async def regionalize_pool(self, pool: EventPool) -> list[RegionalizedEvent]:
        """批量地区化"""
        results = []
        for event in pool.events:
            regionalized = await self.regionalize(event, pool.country_code)
            results.append(regionalized)
        return results

    async def close(self):
        await self.client.aclose()
