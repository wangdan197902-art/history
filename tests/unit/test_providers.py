"""Provider 接口与实现测试"""
import pytest

from src.config.base import Settings
from src.providers.base import (
    Auditor,
    Illustrator,
    Publisher,
    Regionalizer,
    Translator,
    WikipediaFetcher,
)
from src.providers.factory import (
    get_auditor,
    get_illustrator,
    get_publisher,
    get_regionalizer,
    get_translator,
    get_wikipedia_fetcher,
    get_provider,
)
from src.providers.impl.mock_anthropic import MockAnthropicRegionalizer
from src.providers.impl.mock_buttondown import MockButtondownPublisher
from src.providers.impl.mock_gemini import MockGeminiAuditor, MockGeminiIllustrator
from src.providers.impl.mock_openai import MockOpenAITranslator
from src.providers.impl.mock_wikipedia import MockWikipediaFetcher


@pytest.fixture
def settings():
    return Settings()


class TestProviderBase:
    """ABC 接口测试"""

    def test_abc_cannot_instantiate(self):
        """ABC 类不能直接实例化"""
        with pytest.raises(TypeError):
            WikipediaFetcher()  # type: ignore
        with pytest.raises(TypeError):
            Regionalizer()  # type: ignore
        with pytest.raises(TypeError):
            Translator()  # type: ignore
        with pytest.raises(TypeError):
            Illustrator()  # type: ignore
        with pytest.raises(TypeError):
            Auditor()  # type: ignore
        with pytest.raises(TypeError):
            Publisher()  # type: ignore

    @pytest.mark.asyncio
    async def test_health_check_default_true(self):
        """health_check 默认返回 True"""
        class DummyFetcher(WikipediaFetcher):
            async def fetch_events(self, month, day, event_type="all"):
                pass
            async def fetch_year(self, year):
                pass
        f = DummyFetcher()
        assert await f.health_check() is True


class TestFactory:
    """工厂函数测试"""

    def test_get_wikipedia_fetcher_mock(self, settings):
        f = get_wikipedia_fetcher(settings)
        assert isinstance(f, MockWikipediaFetcher)

    def test_get_regionalizer_mock(self, settings):
        r = get_regionalizer(settings)
        assert isinstance(r, MockAnthropicRegionalizer)

    def test_get_translator_mock(self, settings):
        t = get_translator(settings)
        assert isinstance(t, MockOpenAITranslator)

    def test_get_illustrator_mock(self, settings):
        i = get_illustrator(settings)
        assert isinstance(i, MockGeminiIllustrator)

    def test_get_auditor_mock(self, settings):
        a = get_auditor(settings)
        assert isinstance(a, MockGeminiAuditor)

    def test_get_publisher_mock(self, settings):
        p = get_publisher(settings)
        assert isinstance(p, MockButtondownPublisher)

    def test_unknown_provider_raises(self, settings):
        """未知 provider 抛 ValueError"""
        s = Settings(WIKIPEDIA_PROVIDER="invalid")
        with pytest.raises(ValueError):
            get_wikipedia_fetcher(s)

    def test_get_provider_generic(self, settings):
        """通用 provider 获取"""
        f = get_provider("wikipedia", settings)
        assert isinstance(f, MockWikipediaFetcher)
        r = get_provider("anthropic", settings)
        assert isinstance(r, MockAnthropicRegionalizer)

    def test_get_provider_unknown_name(self, settings):
        """未知 provider 名称"""
        with pytest.raises(ValueError):
            get_provider("unknown", settings)

    def test_get_real_provider_raises(self):
        """real 模式当前阶段抛 NotImplementedError(Phase 4 才实现)"""
        from src.providers.impl.real_wikipedia import RealWikipediaFetcher
        s = Settings(WIKIPEDIA_PROVIDER="real")
        with pytest.raises(NotImplementedError):
            get_wikipedia_fetcher(s)


class TestMockProviders:
    """Mock Provider 实例化测试"""

    def test_mock_wikipedia_init(self, settings):
        f = MockWikipediaFetcher(settings)
        assert f.base_url == "http://127.0.0.1:8765/wikipedia"
        assert f.client is not None

    def test_mock_anthropic_init(self, settings):
        r = MockAnthropicRegionalizer(settings)
        assert r.base_url == "http://127.0.0.1:8765/anthropic"

    def test_mock_openai_init(self, settings):
        t = MockOpenAITranslator(settings)
        assert t.base_url == "http://127.0.0.1:8765/openai"

    def test_mock_gemini_illustrator_init(self, settings):
        i = MockGeminiIllustrator(settings)
        assert i.base_url == "http://127.0.0.1:8765/gemini"

    def test_mock_gemini_auditor_init(self, settings):
        a = MockGeminiAuditor(settings)
        assert a.base_url == "http://127.0.0.1:8765/gemini"

    def test_mock_buttondown_init(self, settings):
        p = MockButtondownPublisher(settings)
        assert p.base_url == "http://127.0.0.1:8765/buttondown"


class TestMockProvidersHealthCheck:
    """Mock Provider health_check 测试"""

    @pytest.mark.asyncio
    async def test_wikipedia_health_check(self, settings):
        f = MockWikipediaFetcher(settings)
        assert await f.health_check() is True

    @pytest.mark.asyncio
    async def test_anthropic_health_check(self, settings):
        r = MockAnthropicRegionalizer(settings)
        assert await r.health_check() is True

    @pytest.mark.asyncio
    async def test_openai_health_check(self, settings):
        t = MockOpenAITranslator(settings)
        assert await t.health_check() is True
