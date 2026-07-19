"""Mock OpenAI 翻译器"""
from typing import Any

import httpx

from src.models.event import RegionalizedEvent, TranslatedEvent
from src.providers.base import Translator


class MockOpenAITranslator(Translator):
    """Mock OpenAI 实现 - 多语种翻译"""

    def __init__(self, settings: Any):
        self.settings = settings
        self.base_url = f"http://{settings.MOCK_SERVER_HOST}:{settings.MOCK_SERVER_PORT}/openai"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def translate(self, regionalized: RegionalizedEvent, target_lang: str) -> TranslatedEvent:
        """调用 Mock GPT-4o 翻译"""
        prompt = f"原文:{regionalized.regional_title}\n描述:{regionalized.regional_description}\n目标语言:{target_lang}\n请翻译:"

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "你是专业翻译,将历史事件翻译为指定语言,保持中立和准确。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": "Bearer mock-key"},
        )
        response.raise_for_status()
        data = response.json()

        translated_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        return TranslatedEvent(
            regionalized=regionalized,
            lang=target_lang,
            translated_title=translated_text[:100] if translated_text else regionalized.regional_title,
            translated_description=translated_text or regionalized.regional_description,
            translator="gpt-4o-mock",
        )

    async def translate_to_all_langs(
        self, regionalized: RegionalizedEvent, target_langs: list[str]
    ) -> list[TranslatedEvent]:
        """翻译到所有目标语言"""
        results = []
        for lang in target_langs:
            translated = await self.translate(regionalized, lang)
            results.append(translated)
        return results

    async def close(self):
        await self.client.aclose()
