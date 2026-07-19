"""
事件数据模型 - 地区化今天历史档案站

数据流:
  Event (原始) → RegionalizedEvent (地区化) → TranslatedEvent (翻译)
              → IllustratedEvent (配图) → AuditedEvent (审核)

EventPool: 单日单地区的事件集合
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Event(BaseModel):
    """单条历史事件(原始数据)"""

    id: str = Field(description="事件唯一 ID,如 evt_20260704_CN_001")
    date: str = Field(description="事件日期 YYYY-MM-DD")
    year: int = Field(description="事件发生的年份", ge=-3000, le=2100)
    title: str = Field(description="事件标题(原始语言)", min_length=1)
    description: str = Field(description="事件描述(原始语言)", min_length=1)
    wikipedia_url: str = Field(description="Wikipedia 原文链接")
    categories: list[str] = Field(default_factory=list, description="事件分类")
    location: Optional[str] = Field(None, description="事件地点")
    deaths: Optional[int] = Field(None, description="死亡人数", ge=0)
    injuries: Optional[int] = Field(None, description="受伤人数", ge=0)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """校验日期格式 YYYY-MM-DD"""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"日期格式必须为 YYYY-MM-DD, got {v}") from e
        return v


class RegionalizedEvent(BaseModel):
    """地区化后的事件"""

    original: Event = Field(description="原始事件")
    country_code: str = Field(description="地区代码,如 CN/US/JP", min_length=2, max_length=3)
    regional_title: str = Field(description="地区化标题", min_length=1)
    regional_description: str = Field(description="地区化描述", min_length=1)
    neutrality_score: float = Field(
        default=0.7, ge=0, le=1, description="中立性评分 0-1, 1 为完全中立"
    )
    regional_tags: list[str] = Field(default_factory=list, description="地区标签")
    rewrite_log: Optional[str] = Field(None, description="重写日志(用于追溯)")


class TranslatedEvent(BaseModel):
    """翻译后的事件"""

    regionalized: RegionalizedEvent = Field(description="地区化事件")
    lang: str = Field(description="目标语言代码,如 zh/en/ja", min_length=2, max_length=3)
    translated_title: str = Field(description="翻译后标题", min_length=1)
    translated_description: str = Field(description="翻译后描述", min_length=1)
    translator: str = Field(default="gpt-4o", description="翻译引擎")


class IllustratedEvent(BaseModel):
    """配图后的事件"""

    translated: TranslatedEvent = Field(description="翻译后事件")
    image_url: str = Field(description="图片 URL")
    image_alt: str = Field(description="图片 alt 文本", min_length=1)
    image_caption: str = Field(default="", description="图片说明")
    image_credit: Optional[str] = Field(None, description="图片版权信息")
    image_width: Optional[int] = Field(None, description="图片宽度", ge=1)
    image_height: Optional[int] = Field(None, description="图片高度", ge=1)


class AuditedEvent(BaseModel):
    """审核后的事件"""

    illustrated: IllustratedEvent = Field(description="配图后事件")
    audit_pass: bool = Field(description="审核是否通过")
    audit_notes: str = Field(default="", description="审核备注")
    compliance_score: float = Field(
        default=0.8, ge=0, le=1, description="合规评分 0-1"
    )
    audited_by: str = Field(default="gemini-1.5-flash", description="审核引擎")
    audit_issues: list[str] = Field(default_factory=list, description="审核问题清单")


class EventPool(BaseModel):
    """事件池 - 单日单地区的事件集合"""

    date: str = Field(description="日期 YYYY-MM-DD")
    country_code: str = Field(description="地区代码", min_length=2, max_length=3)
    events: list[Event] = Field(default_factory=list, description="事件列表")
    source: str = Field(default="wikipedia", description="数据源")
    fetched_at: str = Field(description="抓取时间 ISO8601")

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"日期格式必须为 YYYY-MM-DD, got {v}") from e
        return v

    def event_count(self) -> int:
        """返回事件数"""
        return len(self.events)


class PipelineResult(BaseModel):
    """管道运行结果(单日单地区)"""

    date: str
    country_code: str
    event_pool: Optional[EventPool] = None
    regionalized: list[RegionalizedEvent] = Field(default_factory=list)
    translated: dict[str, list[TranslatedEvent]] = Field(default_factory=dict)
    illustrated: dict[str, list[IllustratedEvent]] = Field(default_factory=dict)
    audited: dict[str, list[AuditedEvent]] = Field(default_factory=dict)
    published_pages: list[str] = Field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    duration_seconds: float = 0.0
