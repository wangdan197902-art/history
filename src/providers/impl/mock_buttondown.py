"""Mock Buttondown 发布器"""
from pathlib import Path
from typing import Any

import httpx

from src.models.event import AuditedEvent
from src.providers.base import Publisher


def _yaml_escape(s: str) -> str:
    """转义 YAML 字符串中的特殊字符"""
    if not s:
        return ""
    return s.replace('"', '\\"').replace("\n", " ").replace("\r", "")


class MockButtondownPublisher(Publisher):
    """Mock Buttondown 实现 - 邮件发布"""

    def __init__(self, settings: Any):
        self.settings = settings
        self.base_url = f"http://{settings.MOCK_SERVER_HOST}:{settings.MOCK_SERVER_PORT}/buttondown"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def publish_markdown(self, audited_list: list[AuditedEvent], output_dir: str) -> list[str]:
        """生成 Hugo Markdown 文件(按日期分组,每日一个文件,包含多事件)"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 按日期分组(同一日多事件合并到一个 .md 文件)
        grouped_by_date: dict[str, list[AuditedEvent]] = {}
        for audited in audited_list:
            date_str = audited.illustrated.translated.regionalized.original.date
            month_day = date_str[5:]  # MM-DD
            grouped_by_date.setdefault(month_day, []).append(audited)

        generated_files = []
        for month_day, items in grouped_by_date.items():
            first = items[0]
            translated = first.illustrated.translated
            lang = translated.lang
            country = translated.regionalized.country_code
            date_str = translated.regionalized.original.date

            filename = f"{month_day}.md"
            filepath = output_path / filename

            # 构造 events 列表(YAML)
            events_yaml = []
            body_sections = []
            for audited in items:
                t = audited.illustrated.translated
                ev_year = t.regionalized.original.year
                ev_title = _yaml_escape(t.translated_title)
                ev_desc = _yaml_escape(t.translated_description)
                ev_img = _yaml_escape(audited.illustrated.image_url)
                ev_cap = _yaml_escape(audited.illustrated.image_caption)
                events_yaml.append(
                    f"  - year: {ev_year}\n"
                    f"    title: \"{ev_title}\"\n"
                    f"    description: \"{ev_desc}\"\n"
                    f"    image_url: \"{ev_img}\"\n"
                    f"    image_caption: \"{ev_cap}\""
                )
                body_sections.append(
                    f"## {ev_year} — {t.translated_title}\n\n"
                    f"{t.translated_description}\n\n"
                    f"![{t.translated_title}]({audited.illustrated.image_url})\n\n"
                    f"*{audited.illustrated.image_caption}*\n"
                )

            content = f"""---
title: "{month_day} · {country} 今天历史"
date: {date_str}
country_code: "{country}"
country_name: "{country}"
language: "{lang}"
draft: false
events:
{chr(10).join(events_yaml)}
---

# {month_day} · {country} 今天历史

{chr(10).join(body_sections)}
"""
            filepath.write_text(content, encoding="utf-8")
            generated_files.append(str(filepath))

        return generated_files

    async def publish_newsletter(self, audited_list: list[AuditedEvent]) -> str:
        """发布邮件(调用 Mock Buttondown API)"""
        if not audited_list:
            return ""

        first = audited_list[0]
        subject = f"今日历史 · {first.illustrated.translated.regionalized.original.date}"
        body = "\n\n".join([
            f"## {a.illustrated.translated.translated_title}\n\n{a.illustrated.translated.translated_description}"
            for a in audited_list
        ])

        payload = {
            "subject": subject,
            "body": body,
            "email_type": "public",
        }

        response = await self.client.post(
            f"{self.base_url}/emails",
            json=payload,
            headers={"Authorization": "Token mock-key"},
        )
        response.raise_for_status()
        data = response.json()

        return data.get("id", "mock-email-id")

    async def close(self):
        await self.client.aclose()
