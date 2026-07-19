"""Real Buttondown 发布器 - Phase 4 实现

⚠️ 此文件为占位,Phase 4 启用真实 API 时实现。
技术债务: TD-002
"""
from typing import Any

from src.models.event import AuditedEvent
from src.providers.base import Publisher


class RealButtondownPublisher(Publisher):
    """Real Buttondown 实现 - 调用真实 Buttondown API

    Phase 4 实现,目前抛出 NotImplementedError
    """

    def __init__(self, settings: Any):
        self.settings = settings
        raise NotImplementedError(
            "RealButtondownPublisher 将在 Phase 4 实现。"
            "当前使用 MockButtondownPublisher(ENV=local)。"
        )

    async def publish_markdown(self, audited_list: list[AuditedEvent], output_dir: str) -> list[str]:
        raise NotImplementedError("Phase 4 实现")

    async def publish_newsletter(self, audited_list: list[AuditedEvent]) -> str:
        raise NotImplementedError("Phase 4 实现")
