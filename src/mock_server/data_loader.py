"""Mock 数据加载器

从 tests/fixtures/mock_responses/ 加载预生成的 Mock 数据

目录结构:
    tests/fixtures/mock_responses/
        wikipedia/
            {MM-DD}_{COUNTRY}.json   # 10,980 个事件池
        anthropic/
            {scenario}.json           # 地区化响应
        openai/
            {lang}_{scenario}.json    # 翻译响应
        gemini/
            {scenario}.json           # 配图响应
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from flask import current_app

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "mock_responses"


def load_fixture(service: str, scenario: str) -> dict | list:
    """加载 Mock fixture

    Args:
        service: 服务名(wikipedia/anthropic/openai/gemini/buttondown/gsc)
        scenario: 场景名(如 "07-04_CN" / "regionalize" / "translate_en")

    Returns:
        dict | list: Mock 数据

    Raises:
        FileNotFoundError: 文件不存在时抛出
    """
    fixture_path = FIXTURE_DIR / service / f"{scenario}.json"

    if not fixture_path.exists():
        current_app.logger.warning(f"Fixture not found: {fixture_path}, using fallback")
        return _get_fallback(service, scenario)

    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=512)
def load_fixture_cached(service: str, scenario: str) -> dict | list:
    """带 LRU 缓存的 fixture 加载(适合只读场景)"""
    return load_fixture(service, scenario)


def _get_fallback(service: str, scenario: str) -> dict:
    """降级响应:fixture 不存在时返回默认值"""
    fallbacks = {
        "wikipedia": {
            "events": [
                {
                    "text": f"Mock event for {scenario}",
                    "year": 2000,
                    "pages": [{"title": "Mock", "content_urls": {"page": ""}}],
                    "categories": ["mock"],
                }
            ]
        },
        "anthropic": {
            "id": "msg_mock",
            "type": "message",
            "role": "assistant",
            "model": "claude-3-5-sonnet-20241022",
            "content": [{"type": "text", "text": f"Mock regionalized content for {scenario}"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 50, "output_tokens": 80},
        },
        "openai": {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Mock translated content for {scenario}",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
        },
        "gemini": {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"image_url":"https://mock.example.com/image.jpg","image_alt":"Mock image","image_caption":"Mock caption"}'
                            }
                        ]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 30,
                "candidatesTokenCount": 80,
                "totalTokenCount": 110,
            },
        },
        "buttondown": {
            "id": "mock-email-id",
            "subject": "Mock Newsletter",
            "body": "Mock content",
            "email_type": "public",
        },
        "gsc": {
            "sitemap": [],
            "nextPageToken": None,
        },
    }
    return fallbacks.get(service, {"mock": True, "scenario": scenario})


def list_fixtures(service: str) -> list[str]:
    """列出指定服务的所有 fixture 文件名(不含扩展名)"""
    service_dir = FIXTURE_DIR / service
    if not service_dir.exists():
        return []
    return sorted([f.stem for f in service_dir.glob("*.json")])


def fixture_exists(service: str, scenario: str) -> bool:
    """检查 fixture 是否存在"""
    return (FIXTURE_DIR / service / f"{scenario}.json").exists()


def get_fixture_stats() -> dict[str, int]:
    """获取各服务 fixture 数量统计"""
    stats = {}
    for service in ["wikipedia", "anthropic", "openai", "gemini", "buttondown", "gsc"]:
        service_dir = FIXTURE_DIR / service
        if service_dir.exists():
            stats[service] = len(list(service_dir.glob("*.json")))
        else:
            stats[service] = 0
    return stats
