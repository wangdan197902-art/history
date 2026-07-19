"""
Provider 工厂与导出

通过 ENV 环境变量切换 Mock / Real 实现:
  ENV=local  → 使用 Mock 实现(调用 Flask Mock Server)
  ENV=production → 使用 Real 实现(调用真实 API)
"""
from src.providers.base import (
    Auditor,
    Illustrator,
    Publisher,
    Regionalizer,
    Translator,
    WikipediaFetcher,
)
from src.providers.factory import get_provider, get_auditor, get_illustrator, get_publisher, get_regionalizer, get_translator, get_wikipedia_fetcher

__all__ = [
    "WikipediaFetcher", "Regionalizer", "Translator",
    "Illustrator", "Auditor", "Publisher",
    "get_provider", "get_wikipedia_fetcher", "get_regionalizer",
    "get_translator", "get_illustrator", "get_auditor", "get_publisher",
]
