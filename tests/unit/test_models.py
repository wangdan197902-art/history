"""
数据模型单元测试
"""
import pytest
from pydantic import ValidationError

from src.models.event import (
    AuditedEvent,
    Event,
    EventPool,
    IllustratedEvent,
    PipelineResult,
    RegionalizedEvent,
    TranslatedEvent,
)
from src.models.countries import (
    ALL_COUNTRIES,
    COUNTRIES_TIER_1,
    COUNTRIES_TIER_2,
    COUNTRIES_TIER_3,
    LANGUAGES,
    get_country_name,
    get_country_tier,
    get_language_direction,
    validate_country,
    validate_language,
)


class TestEventModel:
    """Event 模型测试"""

    def test_event_valid(self):
        """测试有效事件创建"""
        event = Event(
            id="evt_20260704_CN_001",
            date="2026-07-04",
            year=1921,
            title="中国共产党成立",
            description="中国共产党第一次全国代表大会在上海召开。",
            wikipedia_url="https://en.wikipedia.org/wiki/CCP",
            categories=["mock", "cn"],
            location="Shanghai",
        )
        assert event.id == "evt_20260704_CN_001"
        assert event.year == 1921
        assert event.deaths is None

    def test_event_invalid_date(self):
        """测试无效日期格式"""
        with pytest.raises(ValidationError):
            Event(
                id="evt_001",
                date="2026/07/04",  # 错误格式
                year=1921,
                title="test",
                description="test",
                wikipedia_url="",
            )

    def test_event_invalid_year(self):
        """测试无效年份"""
        with pytest.raises(ValidationError):
            Event(
                id="evt_001",
                date="2026-07-04",
                year=3000,  # 超出范围
                title="test",
                description="test",
                wikipedia_url="",
            )

    def test_event_empty_title(self):
        """测试空标题"""
        with pytest.raises(ValidationError):
            Event(
                id="evt_001",
                date="2026-07-04",
                year=2000,
                title="",  # 空标题
                description="test",
                wikipedia_url="",
            )

    def test_event_negative_deaths(self):
        """测试负数死亡人数"""
        with pytest.raises(ValidationError):
            Event(
                id="evt_001",
                date="2026-07-04",
                year=2000,
                title="test",
                description="test",
                wikipedia_url="",
                deaths=-1,  # 负数
            )


class TestEventPool:
    """EventPool 模型测试"""

    def test_event_pool_valid(self):
        """测试有效事件池"""
        pool = EventPool(
            date="2026-07-04",
            country_code="CN",
            events=[],
            source="wikipedia",
            fetched_at="2026-07-19T00:00:00Z",
        )
        assert pool.country_code == "CN"
        assert pool.events == []
        assert pool.event_count() == 0

    def test_event_pool_with_events(self):
        """测试带事件的事件池"""
        event = Event(
            id="evt_001",
            date="2026-07-04",
            year=1921,
            title="test",
            description="test",
            wikipedia_url="",
        )
        pool = EventPool(
            date="2026-07-04",
            country_code="CN",
            events=[event],
            source="wikipedia",
            fetched_at="2026-07-19T00:00:00Z",
        )
        assert pool.event_count() == 1


class TestRegionalizedEvent:
    """RegionalizedEvent 模型测试"""

    def test_regionalized_valid(self):
        """测试有效地区化事件"""
        event = Event(
            id="evt_001",
            date="2026-07-04",
            year=1921,
            title="test",
            description="test",
            wikipedia_url="",
        )
        regionalized = RegionalizedEvent(
            original=event,
            country_code="CN",
            regional_title="地区化标题",
            regional_description="地区化描述",
            neutrality_score=0.85,
            regional_tags=["中国", "现代史"],
        )
        assert regionalized.neutrality_score == 0.85
        assert len(regionalized.regional_tags) == 2

    def test_regionalized_invalid_neutrality(self):
        """测试无效中立性评分"""
        event = Event(
            id="evt_001",
            date="2026-07-04",
            year=1921,
            title="test",
            description="test",
            wikipedia_url="",
        )
        with pytest.raises(ValidationError):
            RegionalizedEvent(
                original=event,
                country_code="CN",
                regional_title="test",
                regional_description="test",
                neutrality_score=1.5,  # 超出范围
            )


class TestTranslatedEvent:
    """TranslatedEvent 模型测试"""

    def test_translated_valid(self):
        """测试有效翻译事件"""
        event = Event(
            id="evt_001",
            date="2026-07-04",
            year=1921,
            title="test",
            description="test",
            wikipedia_url="",
        )
        regionalized = RegionalizedEvent(
            original=event,
            country_code="CN",
            regional_title="地区化标题",
            regional_description="地区化描述",
        )
        translated = TranslatedEvent(
            regionalized=regionalized,
            lang="en",
            translated_title="Regional Title",
            translated_description="Regional Description",
        )
        assert translated.lang == "en"
        assert translated.translator == "gpt-4o"


class TestCountriesModule:
    """countries 模块测试"""

    def test_countries_count(self):
        """测试地区总数"""
        assert len(ALL_COUNTRIES) == 30
        assert len(COUNTRIES_TIER_1) == 7
        assert len(COUNTRIES_TIER_2) == 8
        assert len(COUNTRIES_TIER_3) == 15

    def test_languages_count(self):
        """测试语种总数"""
        assert len(LANGUAGES) == 10

    def test_get_country_tier(self):
        """测试地区分级查询"""
        assert get_country_tier("CN") == 1
        assert get_country_tier("US") == 1
        assert get_country_tier("RU") == 2
        assert get_country_tier("ID") == 3
        assert get_country_tier("XX") == 0

    def test_get_country_name(self):
        """测试地区名称查询"""
        assert get_country_name("CN") == "中国"
        assert get_country_name("US", "en") == "United States"
        assert get_country_name("XX") == "XX"  # 不存在

    def test_get_language_direction(self):
        """测试语种方向"""
        assert get_language_direction("zh") == "ltr"
        assert get_language_direction("ar") == "rtl"
        assert get_language_direction("xx") == "ltr"  # 默认

    def test_validate_country(self):
        """测试地区代码校验"""
        assert validate_country("CN") is True
        assert validate_country("XX") is False

    def test_validate_language(self):
        """测试语种代码校验"""
        assert validate_language("zh") is True
        assert validate_language("xx") is False


class TestPipelineResult:
    """PipelineResult 模型测试"""

    def test_pipeline_result_default(self):
        """测试默认值"""
        result = PipelineResult(date="2026-07-04", country_code="CN")
        assert result.success is True
        assert result.duration_seconds == 0.0
        assert result.translated == {}

    def test_pipeline_result_serialization(self):
        """测试序列化"""
        result = PipelineResult(date="2026-07-04", country_code="CN")
        data = result.model_dump()
        assert data["date"] == "2026-07-04"
        assert data["country_code"] == "CN"
