"""Mock Server 数据加载器与中间件测试"""
import pytest

from src.mock_server.data_loader import (
    fixture_exists,
    get_fixture_stats,
    list_fixtures,
    load_fixture,
    load_fixture_cached,
    _get_fallback,
)


class TestFixtureLoader:
    def test_load_wikipedia_fixture(self):
        """加载 Wikipedia fixture"""
        data = load_fixture("wikipedia", "01-01_CN")
        assert isinstance(data, dict)
        assert "events" in data

    def test_load_anthropic_fixture(self):
        """加载 Anthropic fixture"""
        data = load_fixture("anthropic", "regionalize_CN")
        assert isinstance(data, dict)

    def test_load_gemini_fixture(self):
        """加载 Gemini fixture"""
        data = load_fixture("gemini", "illustrate")
        assert isinstance(data, dict)

    def test_load_fixture_cached(self):
        """带缓存的加载"""
        data1 = load_fixture_cached("wikipedia", "01-01_CN")
        data2 = load_fixture_cached("wikipedia", "01-01_CN")
        assert data1 == data2

    def test_load_missing_fixture_returns_fallback(self):
        """加载不存在的 fixture 返回降级响应"""
        # 使用 Flask app context
        from src.mock_server.app import create_app
        app = create_app()
        with app.app_context():
            data = _get_fallback("wikipedia", "nonexistent")
            assert "events" in data
            data = _get_fallback("anthropic", "nonexistent")
            assert "content" in data
            data = _get_fallback("openai", "nonexistent")
            assert "choices" in data
            data = _get_fallback("gemini", "nonexistent")
            assert "candidates" in data
            data = _get_fallback("buttondown", "nonexistent")
            assert "id" in data
            data = _get_fallback("gsc", "nonexistent")
            assert "sitemap" in data
            data = _get_fallback("unknown", "x")
            assert data.get("mock") is True

    def test_fixture_exists(self):
        """检查 fixture 存在"""
        assert fixture_exists("wikipedia", "01-01_CN") is True
        assert fixture_exists("wikipedia", "nonexistent") is False

    def test_list_fixtures(self):
        """列出 fixtures"""
        names = list_fixtures("wikipedia")
        assert len(names) > 0
        assert "01-01_CN" in names

    def test_list_fixtures_nonexistent_service(self):
        """列出不存在的服务"""
        names = list_fixtures("nonexistent_service")
        assert names == []

    def test_get_fixture_stats(self):
        """fixture 统计"""
        stats = get_fixture_stats()
        assert "wikipedia" in stats
        assert "anthropic" in stats
        assert stats["wikipedia"] > 0


class TestFaultInjectionMiddleware:
    """故障注入中间件测试"""

    def test_middleware_disabled(self):
        """禁用时直接透传"""
        from src.mock_server.middleware import FaultInjectionMiddleware

        def dummy_app(environ, start_response):
            return "OK"

        middleware = FaultInjectionMiddleware(
            dummy_app, {"FAULT_INJECTION_ENABLED": False}
        )
        assert middleware.enabled is False
        # 应该直接调用原 app
        result = middleware({"PATH_INFO": "/test"}, lambda *args: None)
        assert result == "OK"

    def test_middleware_enabled_but_no_fault(self, monkeypatch):
        """启用但概率为 0"""
        from src.mock_server.middleware import FaultInjectionMiddleware

        def dummy_app(environ, start_response):
            return "OK"

        middleware = FaultInjectionMiddleware(
            dummy_app,
            {"FAULT_INJECTION_ENABLED": True, "FAULT_INJECTION_RATE": 0.0},
        )
        assert middleware.enabled is True
        assert middleware.rate == 0.0
        # rate=0 不会触发故障
        result = middleware({"PATH_INFO": "/test"}, lambda *args: None)
        assert result == "OK"
