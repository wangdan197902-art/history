"""补充测试 — 提升 factory/middleware/routes/orchestrator 覆盖率"""
import pytest

from src.config.base import Settings
from src.providers.factory import (
    get_auditor,
    get_illustrator,
    get_publisher,
    get_regionalizer,
    get_translator,
    get_wikipedia_fetcher,
)


class TestFactoryRealRaises:
    """real 模式全部抛 NotImplementedError(Phase 4 占位)"""

    def test_real_anthropic_raises(self):
        s = Settings(ANTHROPIC_PROVIDER="real")
        with pytest.raises(NotImplementedError):
            get_regionalizer(s)

    def test_real_openai_raises(self):
        s = Settings(OPENAI_PROVIDER="real")
        with pytest.raises(NotImplementedError):
            get_translator(s)

    def test_real_gemini_illustrator_raises(self):
        s = Settings(GEMINI_PROVIDER="real")
        with pytest.raises(NotImplementedError):
            get_illustrator(s)

    def test_real_gemini_auditor_raises(self):
        s = Settings(GEMINI_PROVIDER="real")
        with pytest.raises(NotImplementedError):
            get_auditor(s)

    def test_real_buttondown_raises(self):
        s = Settings(BUTTONDOWN_PROVIDER="real")
        with pytest.raises(NotImplementedError):
            get_publisher(s)

    def test_unknown_anthropic_provider(self):
        s = Settings(ANTHROPIC_PROVIDER="invalid")
        with pytest.raises(ValueError):
            get_regionalizer(s)

    def test_unknown_openai_provider(self):
        s = Settings(OPENAI_PROVIDER="invalid")
        with pytest.raises(ValueError):
            get_translator(s)

    def test_unknown_gemini_provider(self):
        s = Settings(GEMINI_PROVIDER="invalid")
        with pytest.raises(ValueError):
            get_illustrator(s)

    def test_unknown_buttondown_provider(self):
        s = Settings(BUTTONDOWN_PROVIDER="invalid")
        with pytest.raises(ValueError):
            get_publisher(s)


class TestProviderBaseHealthCheck:
    """ABC 基类 health_check 默认实现"""

    @pytest.mark.asyncio
    async def test_regionalizer_health_check(self):
        from src.providers.base import Regionalizer
        class Dummy(Regionalizer):
            async def regionalize(self, event, country_code):
                pass
            async def regionalize_pool(self, pool):
                pass
        assert await Dummy().health_check() is True

    @pytest.mark.asyncio
    async def test_translator_health_check(self):
        from src.providers.base import Translator
        class Dummy(Translator):
            async def translate(self, regionalized, target_lang):
                pass
            async def translate_to_all_langs(self, regionalized, target_langs):
                pass
        assert await Dummy().health_check() is True

    @pytest.mark.asyncio
    async def test_illustrator_health_check(self):
        from src.providers.base import Illustrator
        class Dummy(Illustrator):
            async def illustrate(self, translated):
                pass
        assert await Dummy().health_check() is True

    @pytest.mark.asyncio
    async def test_auditor_health_check(self):
        from src.providers.base import Auditor
        class Dummy(Auditor):
            async def audit(self, illustrated):
                pass
        assert await Dummy().health_check() is True

    @pytest.mark.asyncio
    async def test_publisher_health_check(self):
        from src.providers.base import Publisher
        class Dummy(Publisher):
            async def publish_markdown(self, audited_list, output_dir):
                pass
            async def publish_newsletter(self, audited_list):
                pass
        assert await Dummy().health_check() is True


class TestMockServerRoutesEdgeCases:
    """Mock Server 路由边界测试"""

    @pytest.fixture
    def client(self):
        from src.mock_server.app import create_app
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_anthropic_missing_messages(self, client):
        """Anthropic 缺失 messages 字段"""
        response = client.post(
            "/anthropic/messages",
            json={"model": "claude-3-5-sonnet-20241022"},
        )
        assert response.status_code == 400

    def test_anthropic_fallback_scenario(self, client):
        """Anthropic 未知场景走降级"""
        response = client.post(
            "/anthropic/messages",
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": "未知场景 XYZ"}],
            },
        )
        # 应该返回 200(Mock 降级响应)
        assert response.status_code == 200

    def test_openai_missing_body(self, client):
        """OpenAI 缺失 body"""
        response = client.post("/openai/chat/completions")
        assert response.status_code == 400

    def test_openai_missing_messages(self, client):
        """OpenAI 缺失 messages"""
        response = client.post(
            "/openai/chat/completions",
            json={"model": "gpt-4o"},
        )
        assert response.status_code == 400

    def test_gemini_missing_body(self, client):
        """Gemini 缺失 body"""
        response = client.post("/gemini/models/gemini-1.5-flash:generateContent")
        assert response.status_code == 400

    def test_gemini_missing_contents(self, client):
        """Gemini 缺失 contents"""
        response = client.post(
            "/gemini/models/gemini-1.5-flash:generateContent",
            json={"other": "field"},
        )
        assert response.status_code == 400

    def test_buttondown_missing_body(self, client):
        """Buttondown 缺失 body"""
        response = client.post("/buttondown/emails")
        assert response.status_code == 400

    def test_buttondown_list_subscribers(self, client):
        """Buttondown 列出订阅者"""
        response = client.get("/buttondown/subscribers")
        assert response.status_code == 200

    def test_buttondown_missing_email(self, client):
        """Buttondown 添加订阅者缺失 email"""
        response = client.post("/buttondown/subscribers", json={})
        assert response.status_code == 400

    def test_gsc_submit_sitemap(self, client):
        """GSC 提交 sitemap"""
        response = client.put(
            "/gsc/sites/https%3A%2F%2Fexample.com%2F/sitemaps",
            json={"sitemap_url": "https://example.com/sitemap.xml"},
        )
        # PUT 方法应返回成功或 201
        assert response.status_code in (200, 201)

    def test_gsc_missing_body(self, client):
        """GSC 查询缺失 body"""
        response = client.post(
            "/gsc/sites/https%3A%2F%2Fexample.com%2F/searchAnalytics/query"
        )
        assert response.status_code == 400


class TestOrchestratorRunDay:
    """Orchestrator run_day 测试"""

    @pytest.mark.asyncio
    async def test_run_day_single_country(self):
        from src.pipeline.orchestrator import PipelineOrchestrator
        s = Settings()
        orch = PipelineOrchestrator(s, use_cache=False)
        try:
            results = await orch.run_day(
                "07", "04", ["CN"], ["zh"], semaphore_limit=1,
            )
            assert "CN" in results
            assert results["CN"].success is True
        finally:
            await orch.close()

    @pytest.mark.asyncio
    async def test_run_day_multi_country(self):
        """多地区并发"""
        from src.pipeline.orchestrator import PipelineOrchestrator
        s = Settings()
        orch = PipelineOrchestrator(s, use_cache=False)
        try:
            results = await orch.run_day(
                "07", "04", ["CN", "US"], ["zh"], semaphore_limit=2,
            )
            assert "CN" in results
            assert "US" in results
        finally:
            await orch.close()

    @pytest.mark.asyncio
    async def test_run_vertical_slice_multi_dates(self):
        """垂直切片多日期"""
        from src.pipeline.orchestrator import PipelineOrchestrator
        s = Settings()
        orch = PipelineOrchestrator(s, use_cache=False)
        try:
            results = await orch.run_vertical_slice(
                country_code="CN", language="zh",
                sample_dates=["07-04", "01-01"],
            )
            assert len(results) == 2
        finally:
            await orch.close()


class TestOrchestratorCloseResource:
    """Orchestrator 资源关闭"""

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """close 可多次调用"""
        from src.pipeline.orchestrator import PipelineOrchestrator
        s = Settings()
        orch = PipelineOrchestrator(s, use_cache=False)
        await orch.close()
        # 再次关闭不抛错
        await orch.close()
