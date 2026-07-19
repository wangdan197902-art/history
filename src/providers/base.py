"""Provider 接口抽象层 - 6 个 ABC 基类

抽象层定义:
  - WikipediaFetcher: 抓取历史事件
  - Regionalizer: 地区化重写
  - Translator: 多语种翻译
  - Illustrator: 配图生成
  - Auditor: 内容审核
  - Publisher: 发布到 Hugo/邮件

每个 ABC 提供:
  - 抽象方法(子类必须实现)
  - 通用方法 health_check() 返回 bool
"""
from abc import ABC, abstractmethod
from typing import Any

from src.models.event import (
    AuditedEvent,
    Event,
    EventPool,
    IllustratedEvent,
    RegionalizedEvent,
    TranslatedEvent,
)


class WikipediaFetcher(ABC):
    """Wikipedia 事件抓取器接口"""

    @abstractmethod
    async def fetch_events(self, month: str, day: str, event_type: str = "all") -> EventPool:
        """抓取某月某日的历史事件

        Args:
            month: 月份(01-12)
            day: 日期(01-31)
            event_type: 事件类型(all/selected/births/deaths/holidays/events)

        Returns:
            EventPool: 事件池
        """
        ...

    @abstractmethod
    async def fetch_year(self, year: int) -> dict[str, list[EventPool]]:
        """抓取全年事件(366天 × 30地区)

        Returns:
            dict[country_code, list[EventPool]]
        """
        ...

    async def health_check(self) -> bool:
        """健康检查"""
        return True


class Regionalizer(ABC):
    """地区化重写器接口"""

    @abstractmethod
    async def regionalize(self, event: Event, country_code: str) -> RegionalizedEvent:
        """将原始事件地区化重写

        Args:
            event: 原始事件
            country_code: 目标地区代码(CN/US/JP/...)

        Returns:
            RegionalizedEvent: 地区化事件(含中立性评分)
        """
        ...

    @abstractmethod
    async def regionalize_pool(self, pool: EventPool) -> list[RegionalizedEvent]:
        """批量地区化事件池"""
        ...

    async def health_check(self) -> bool:
        """健康检查"""
        return True


class Translator(ABC):
    """多语种翻译器接口"""

    @abstractmethod
    async def translate(self, regionalized: RegionalizedEvent, target_lang: str) -> TranslatedEvent:
        """翻译地区化事件到目标语言

        Args:
            regionalized: 地区化事件
            target_lang: 目标语言代码(zh/en/ja/ko/es/fr/de/pt/ru/ar)

        Returns:
            TranslatedEvent: 翻译后事件
        """
        ...

    @abstractmethod
    async def translate_to_all_langs(
        self, regionalized: RegionalizedEvent, target_langs: list[str]
    ) -> list[TranslatedEvent]:
        """翻译到所有目标语言"""
        ...

    async def health_check(self) -> bool:
        """健康检查"""
        return True


class Illustrator(ABC):
    """配图生成器接口"""

    @abstractmethod
    async def illustrate(self, translated: TranslatedEvent) -> IllustratedEvent:
        """为翻译后的事件生成配图

        Args:
            translated: 翻译后事件

        Returns:
            IllustratedEvent: 配图后事件
        """
        ...

    async def health_check(self) -> bool:
        """健康检查"""
        return True


class Auditor(ABC):
    """内容审核器接口"""

    @abstractmethod
    async def audit(self, illustrated: IllustratedEvent) -> AuditedEvent:
        """审核配图事件

        Args:
            illustrated: 配图后事件

        Returns:
            AuditedEvent: 审核后事件(含合规评分)
        """
        ...

    async def health_check(self) -> bool:
        """健康检查"""
        return True


class Publisher(ABC):
    """发布器接口"""

    @abstractmethod
    async def publish_markdown(self, audited_list: list[AuditedEvent], output_dir: str) -> list[str]:
        """发布为 Hugo Markdown 文件

        Args:
            audited_list: 审核后事件列表
            output_dir: 输出目录(site/content/{lang}/{country}/)

        Returns:
            list[str]: 已生成的文件路径列表
        """
        ...

    @abstractmethod
    async def publish_newsletter(self, audited_list: list[AuditedEvent]) -> str:
        """发布邮件订阅

        Returns:
            str: 邮件 ID
        """
        ...

    async def health_check(self) -> bool:
        """健康检查"""
        return True
