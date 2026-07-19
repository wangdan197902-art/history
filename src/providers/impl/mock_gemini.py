"""Mock Gemini 配图生成器和审核器"""
import json
from typing import Any

import httpx

from src.models.event import AuditedEvent, IllustratedEvent, TranslatedEvent
from src.providers.base import Auditor, Illustrator


class MockGeminiIllustrator(Illustrator):
    """Mock Gemini 实现 - 配图生成"""

    def __init__(self, settings: Any):
        self.settings = settings
        self.base_url = f"http://{settings.MOCK_SERVER_HOST}:{settings.MOCK_SERVER_PORT}/gemini"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def illustrate(self, translated: TranslatedEvent) -> IllustratedEvent:
        """调用 Mock Gemini 生成配图描述"""
        prompt = f"为以下历史事件生成图片描述和搜索关键词:{translated.translated_title}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
        }

        response = await self.client.post(
            f"{self.base_url}/models/gemini-1.5-flash:generateContent",
            json=payload,
            params={"key": "mock-key"},
        )
        response.raise_for_status()
        data = response.json()

        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
        try:
            img_data = json.loads(text)
            image_url = img_data.get("image_url", f"https://mock.example.com/{translated.translated_title[:20]}.jpg")
            image_alt = img_data.get("image_alt", translated.translated_title)
            image_caption = img_data.get("image_caption", translated.translated_description[:100])
        except json.JSONDecodeError:
            image_url = f"https://mock.example.com/image_{hash(translated.translated_title)}.jpg"
            image_alt = translated.translated_title
            image_caption = translated.translated_description[:100]

        return IllustratedEvent(
            translated=translated,
            image_url=image_url,
            image_alt=image_alt,
            image_caption=image_caption,
            image_credit="Mock Gemini",
        )

    async def close(self):
        await self.client.aclose()


class MockGeminiAuditor(Auditor):
    """Mock Gemini 实现 - 内容审核"""

    def __init__(self, settings: Any):
        self.settings = settings
        self.base_url = f"http://{settings.MOCK_SERVER_HOST}:{settings.MOCK_SERVER_PORT}/gemini"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def audit(self, illustrated: IllustratedEvent) -> AuditedEvent:
        """调用 Mock Gemini 审核内容"""
        prompt = f"审核以下历史事件内容的合规性:\n标题:{illustrated.translated.translated_title}\n描述:{illustrated.translated.translated_description}\n图片URL:{illustrated.image_url}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 512},
        }

        response = await self.client.post(
            f"{self.base_url}/models/gemini-1.5-flash:generateContent",
            json=payload,
            params={"key": "mock-key"},
        )
        response.raise_for_status()
        data = response.json()

        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        # Mock: 默认通过审核
        return AuditedEvent(
            illustrated=illustrated,
            audit_pass=True,
            audit_notes=text[:200] if text else "Mock audit passed",
            compliance_score=0.9,
            audited_by="gemini-1.5-flash-mock",
            audit_issues=[],
        )

    async def close(self):
        await self.client.aclose()
