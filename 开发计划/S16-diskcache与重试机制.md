# S16 - diskcache 与重试机制

> 阶段：Phase 2 - 内容生产管道
> 人天：1 | 依赖：S15 | 前置：编排器就绪

---

## 一、步骤概述

实现 diskcache 持久化缓存层（避免重复 Mock 调用）+ tenacity 指数退避重试机制（处理 API 失败）。二次运行管道从 15min 降到 < 30s（缓存命中）。

## 二、任务清单

### 2.1 diskcache 封装

文件：`src/pipeline/cache.py`

```python
import hashlib
import json
from functools import wraps
from diskcache import Cache
from src.config.base import Settings

def get_cache(settings: Settings) -> Cache:
    return Cache(settings.DISKCACHE_DIR)

def cache_key(provider: str, method: str, *args, **kwargs) -> str:
    """生成缓存键: hash(provider + method + args + kwargs)"""
    raw = f"{provider}:{method}:{args}:{sorted(kwargs.items())}"
    return hashlib.md5(raw.encode()).hexdigest()

def cached_call(cache: Cache, key: str, fn, *args, **kwargs):
    """带缓存的函数调用"""
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = fn(*args, **kwargs)
    cache.set(key, result, expire=86400 * 7)  # 7 天过期
    return result
```

### 2.2 异步缓存装饰器

文件：`src/pipeline/async_cache.py`

```python
import asyncio
import hashlib
import json
from functools import wraps
from diskcache import Cache

def async_cached(cache: Cache, ttl: int = 86400 * 7):
    """异步函数缓存装饰器"""
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            # 排除 self/settings 等不可序列化参数
            sig_args = str(args[1:]) if args else ""
            sig_kwargs = str(sorted(kwargs.items()))
            key = hashlib.md5(f"{fn.__name__}:{sig_args}:{sig_kwargs}".encode()).hexdigest()

            cached = cache.get(key)
            if cached is not None:
                return cached

            result = await fn(*args, **kwargs)
            try:
                cache.set(key, result, expire=ttl)
            except (TypeError, ValueError):
                pass  # 不可序列化结果不缓存
            return result
        return wrapper
    return decorator
```

### 2.3 重试机制

文件：`src/pipeline/retry.py`

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

def with_retry(max_attempts: int = 3, base_wait: float = 1.0):
    """重试装饰器: 指数退避"""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_wait, min=base_wait, max=base_wait * 10),
        retry=retry_if_exception_type((httpx.HTTPError, ConnectionError, TimeoutError)),
        reraise=True,
    )
```

### 2.4 集成到 Provider

文件：`src/providers/impl/mock_wikipedia.py`（增强版）

```python
import httpx
from src.providers.base import WikipediaFetcher
from src.config.base import Settings
from src.models.event import EventPool, Event
from src.pipeline.async_cache import async_cached
from src.pipeline.retry import with_retry
from diskcache import Cache

class MockWikipediaFetcher(WikipediaFetcher):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.mock_base_url
        self.cache = Cache(settings.DISKCACHE_DIR)

    @with_retry(max_attempts=3)
    async def _fetch_raw(self, date: str, country_code: str) -> dict:
        month, day = date.split("-")
        url = f"{self.base_url}/wikipedia/onthisday/events/{month}/{day}"
        params = {"country": country_code} if country_code else {}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()

    async def fetch_events(self, date: str, country_code: str = "") -> EventPool:
        # 使用缓存
        @async_cached(self.cache)
        async def _cached_fetch(date, country_code):
            return await self._fetch_raw(date, country_code)

        data = await _cached_fetch(date, country_code)
        events = [
            Event(
                id=e.get("text", "")[:50],
                date=f"2026-{date}",
                year=e.get("year", 2026),
                title=e.get("text", ""),
                description=e.get("text", ""),
                wikipedia_url=e.get("pages", [{}])[0].get("content_urls", {}).get("page", ""),
                categories=e.get("categories", []),
            )
            for e in data.get("events", [])
        ]
        return EventPool(
            date=f"2026-{date}",
            country_code=country_code,
            events=events,
            source="wikipedia_mock",
            fetched_at="2026-07-19T00:00:00Z",
        )
```

### 2.5 缓存统计

文件：`src/pipeline/cache_stats.py`

```python
from diskcache import Cache

def print_cache_stats(cache: Cache):
    """打印缓存统计"""
    print(f"缓存目录: {cache.directory}")
    print(f"缓存条目数: {len(cache)}")
    print(f"缓存大小: {cache.volume() / 1024 / 1024:.2f} MB")
    print(f"命中率: {cache.hits() / max(cache.hits() + cache.misses(), 1) * 100:.1f}%")

def clear_cache(cache: Cache):
    """清空缓存"""
    cache.clear()
    print("缓存已清空")
```

## 三、实施步骤

1. `pip install diskcache tenacity`
2. 编写 `src/pipeline/cache.py`（同步缓存）
3. 编写 `src/pipeline/async_cache.py`（异步装饰器）
4. 编写 `src/pipeline/retry.py`（重试）
5. 增强 6 个 Mock Provider（添加缓存 + 重试）
6. 编写 `src/pipeline/cache_stats.py`
7. 单元测试 `tests/unit/test_cache.py`

## 四、验收命令

```bash
. .venv/bin/activate
python -m src.mock_server.app &
sleep 2

# 首次运行（无缓存）
time python -m src.pipeline.orchestrator 07-04
# 期望 < 10min

# 二次运行（缓存命中）
time python -m src.pipeline.orchestrator 07-04
# 期望 < 30s

# 缓存统计
python -c "
from src.config import settings
from src.pipeline.cache_stats import print_cache_stats
from diskcache import Cache
print_cache_stats(Cache(settings.DISKCACHE_DIR))
"
```

## 五、依赖关系

- 前置：S15
- 后续：S17（测试覆盖）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| 缓存污染（prompt 变更未失效） | 中 | 缓存键含参数 hash |
| diskcache 损坏 | 低 | 启动校验，损坏自动清空 |
| 重试风暴 | 低 | 指数退避 + 最大次数限制 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 首次管道 | < 10min | `time` |
| 缓存命中管道 | < 30s | `time` |
| 缓存命中率 | > 90% | 统计 |

## 八、测试要求

- 首次运行无缓存
- 二次运行命中缓存
- 重试机制正常工作
- 缓存统计准确
