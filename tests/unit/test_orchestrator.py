"""管道编排器与缓存测试"""
import asyncio
import pytest

from src.config.base import Settings
from src.models.event import Event, EventPool
from src.pipeline.cache import DiskCacheManager, cached
from src.pipeline.retry import retry_async, retry_with_backoff
from src.pipeline.orchestrator import PipelineOrchestrator


@pytest.fixture
def settings():
    return Settings()


# === Cache 测试 ===

class TestDiskCacheManager:
    def test_basic_set_get(self, tmp_path):
        cache = DiskCacheManager(str(tmp_path / "cache"))
        cache.set("key1", "value1", expire=60)
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self, tmp_path):
        cache = DiskCacheManager(str(tmp_path / "cache"))
        assert cache.get("nonexistent") is None

    def test_delete(self, tmp_path):
        cache = DiskCacheManager(str(tmp_path / "cache"))
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self, tmp_path):
        cache = DiskCacheManager(str(tmp_path / "cache"))
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_stats(self, tmp_path):
        cache = DiskCacheManager(str(tmp_path / "cache"))
        cache.set("k1", "v1")
        stats = cache.stats()
        assert stats["size"] >= 1
        assert "volume_bytes" in stats
        assert "cache_dir" in stats

    def test_cached_key_stable(self, tmp_path):
        """相同参数生成相同键"""
        cache = DiskCacheManager(str(tmp_path / "cache"))
        k1 = cache.cached_key("fetch", month="07", day="04", country="CN")
        k2 = cache.cached_key("fetch", country="CN", day="04", month="07")
        assert k1 == k2

    def test_cached_key_different(self, tmp_path):
        """不同参数生成不同键"""
        cache = DiskCacheManager(str(tmp_path / "cache"))
        k1 = cache.cached_key("fetch", month="07", day="04", country="CN")
        k2 = cache.cached_key("fetch", month="07", day="04", country="US")
        assert k1 != k2

    def test_pydantic_model_cache(self, tmp_path):
        """缓存 pydantic 模型"""
        cache = DiskCacheManager(str(tmp_path / "cache"))
        event = Event(
            id="evt_001", date="2024-07-04", year=1921,
            title="测试", description="测试描述", wikipedia_url="https://example.com",
        )
        cache.set("event_001", event)
        retrieved = cache.get("event_001")
        assert retrieved is not None
        assert retrieved.id == "evt_001"
        assert retrieved.title == "测试"

    def test_event_pool_cache(self, tmp_path):
        """缓存 EventPool"""
        cache = DiskCacheManager(str(tmp_path / "cache"))
        pool = EventPool(
            date="2024-07-04", country_code="CN",
            events=[], source="wikipedia", fetched_at="2024-07-04T00:00:00Z",
        )
        cache.set("pool_001", pool)
        retrieved = cache.get("pool_001")
        assert retrieved is not None
        assert retrieved.country_code == "CN"

    def test_list_cache(self, tmp_path):
        """缓存列表"""
        cache = DiskCacheManager(str(tmp_path / "cache"))
        cache.set("list", [1, 2, 3])
        assert cache.get("list") == [1, 2, 3]

    def test_dict_cache(self, tmp_path):
        """缓存字典"""
        cache = DiskCacheManager(str(tmp_path / "cache"))
        cache.set("dict", {"a": 1, "b": 2})
        assert cache.get("dict") == {"a": 1, "b": 2}


class TestCachedDecorator:
    @pytest.mark.asyncio
    async def test_cached_decorator(self, tmp_path):
        """装饰器缓存"""
        cache = DiskCacheManager(str(tmp_path / "cache"))
        call_count = 0

        @cached("test", cache)
        async def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用相同参数,应该命中缓存
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # 没有再次调用


# === Retry 测试 ===

class TestRetry:
    @pytest.mark.asyncio
    async def test_retry_success_first_try(self):
        """第一次就成功"""
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_async(fn, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self):
        """失败后重试成功"""
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "ok"

        result = await retry_async(fn, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_all_fail(self):
        """重试全部失败"""
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        with pytest.raises(ValueError):
            await retry_async(fn, max_retries=2, base_delay=0.01)
        assert call_count == 3  # 1 + 2 retries

    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        """装饰器形式"""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def fn(x):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return x * 2

        result = await fn(5)
        assert result == 10
        assert call_count == 2


# === Orchestrator 测试 ===

class TestPipelineOrchestrator:
    def test_init(self, settings):
        """初始化"""
        orch = PipelineOrchestrator(settings, use_cache=False)
        assert orch.settings is settings
        assert orch.fetcher is not None
        assert orch.regionalizer is not None
        assert orch.translator is not None
        assert orch.illustrator is not None
        assert orch.auditor is not None
        assert orch.publisher is not None

    @pytest.mark.asyncio
    async def test_run_one_sample(self, settings):
        """运行单日单地区管道"""
        orch = PipelineOrchestrator(settings, use_cache=False)
        try:
            result = await orch.run_one("07", "04", "CN", ["zh"])
            assert result.success is True
            assert result.event_pool is not None
            assert len(result.event_pool.events) > 0
            assert len(result.regionalized) > 0
            assert len(result.translated) > 0
            assert len(result.illustrated) > 0
            assert len(result.audited) > 0
            assert len(result.published_pages) > 0
        finally:
            await orch.close()

    @pytest.mark.asyncio
    async def test_run_vertical_slice(self, settings):
        """垂直切片"""
        orch = PipelineOrchestrator(settings, use_cache=False)
        try:
            results = await orch.run_vertical_slice(
                country_code="CN", language="zh",
                sample_dates=["07-04"],  # 只测 1 个日期加快速度
            )
            assert len(results) == 1
            assert "07-04" in results
            assert results["07-04"].success is True
        finally:
            await orch.close()

    @pytest.mark.asyncio
    async def test_cache_hit_second_run(self, settings, tmp_path):
        """第二次运行命中缓存"""
        # 使用独立缓存目录
        s = Settings(DISKCACHE_DIR=str(tmp_path / "cache"))
        orch1 = PipelineOrchestrator(s, use_cache=True)
        try:
            await orch1.run_one("07", "04", "CN", ["zh"])
        finally:
            await orch1.close()

        # 第二次应该命中缓存
        orch2 = PipelineOrchestrator(s, use_cache=True)
        try:
            result = await orch2.run_one("07", "04", "CN", ["zh"])
            assert result.success is True
            # 缓存应至少有 1 个条目
            assert orch2.cache.stats()["size"] > 0
        finally:
            await orch2.close()

    def test_print_stats(self, settings, capsys):
        """打印统计"""
        from src.models.event import PipelineResult
        orch = PipelineOrchestrator(settings, use_cache=False)
        results = {
            "07-04": PipelineResult(
                date="2024-07-04", country_code="CN", success=True,
                duration_seconds=0.5,
            ),
        }
        orch.print_stats(results)
        captured = capsys.readouterr()
        assert "管道执行统计" in captured.out
        assert "总任务数" in captured.out
