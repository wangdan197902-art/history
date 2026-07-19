# S08 - Provider 切换器与配置双轨制

> 阶段：Phase 1 - Mock 体系建设
> 人天：1.5 | 依赖：S01、S05、S06 | 前置：Provider 接口与 Mock Server 就绪

---

## 一、步骤概述

实现配置双轨制（pydantic-settings + ENV 环境变量切换），编写 6 个 Mock Provider 实现 + 6 个 Real Provider 实现（Real 实现仅占位，Phase 4 启用），通过 `ENV=local|production` 零代码切换。

## 二、任务清单

### 2.1 配置基类

文件：`src/config/base.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 环境切换
    ENV: Literal["local", "production"] = "local"

    # Mock Server
    MOCK_SERVER_HOST: str = "127.0.0.1"
    MOCK_SERVER_PORT: int = 8765
    MOCK_SERVER_BASE_URL: str = "http://127.0.0.1:8765"

    # Provider 选择
    WIKIPEDIA_PROVIDER: Literal["mock", "real"] = "mock"
    ANTHROPIC_PROVIDER: Literal["mock", "real"] = "mock"
    OPENAI_PROVIDER: Literal["mock", "real"] = "mock"
    GEMINI_PROVIDER: Literal["mock", "real"] = "mock"
    BUTTONDOWN_PROVIDER: Literal["mock", "real"] = "mock"
    GSC_PROVIDER: Literal["mock", "real"] = "mock"

    # 管道并发
    ASYNCIO_SEMAPHORE: int = 16
    DISKCACHE_DIR: str = ".cache/pipeline"

    # Hugo
    HUGO_CACHE_DIR: str = "~/.cache/hugo-today-in-history"

    # 真实 API Key（Phase 4 启用）
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    WIKIPEDIA_USER_AGENT: str = "TodayInHistoryArchive/1.0"

    @property
    def mock_base_url(self) -> str:
        return f"http://{self.MOCK_SERVER_HOST}:{self.MOCK_SERVER_PORT}"

    @property
    def is_local(self) -> bool:
        return self.ENV == "local"

settings = Settings()
```

文件：`src/config/__init__.py`

```python
from src.config.base import Settings, settings
__all__ = ["Settings", "settings"]
```

### 2.2 Mock Provider 实现（6 个）

文件：`src/providers/impl/mock_wikipedia.py`

```python
import httpx
from src.providers.base import WikipediaFetcher
from src.config.base import Settings
from src.models.event import EventPool, Event

class MockWikipediaFetcher(WikipediaFetcher):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.mock_base_url

    async def fetch_events(self, date: str, country_code: str = "") -> EventPool:
        """date 格式: MM-DD"""
        month, day = date.split("-")
        url = f"{self.base_url}/wikipedia/onthisday/events/{month}/{day}"
        params = {"country": country_code} if country_code else {}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

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

文件：`src/providers/impl/mock_anthropic.py`

```python
import httpx
from src.providers.base import Regionalizer
from src.config.base import Settings
from src.models.event import EventPool, RegionalizedEvent

class MockAnthropicRegionalizer(Regionalizer):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.mock_base_url

    async def regionalize(self, pool: EventPool, country_code: str) -> list[RegionalizedEvent]:
        url = f"{self.base_url}/anthropic/messages"
        async with httpx.AsyncClient() as client:
            results = []
            for evt in pool.events:
                payload = {
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": f"地区化: {evt.title} -> {country_code}"}]
                }
                resp = await client.post(url, json=payload, timeout=30)
                data = resp.json()
                text = data["content"][0]["text"]
                results.append(RegionalizedEvent(
                    original=evt,
                    country_code=country_code,
                    regional_title=text[:80],
                    regional_description=text,
                    neutrality_score=0.85,
                    regional_tags=[country_code.lower()],
                ))
            return results
```

文件：`src/providers/impl/mock_openai.py` / `mock_gemini.py` / `mock_auditor.py` / `mock_publisher.py` 类似结构。

### 2.3 Real Provider 实现（占位，Phase 4 启用）

文件：`src/providers/impl/real_wikipedia.py`

```python
import httpx
from src.providers.base import WikipediaFetcher
from src.config.base import Settings

class RealWikipediaFetcher(WikipediaFetcher):
    """真实 Wikipedia API — Phase 4 启用"""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = "https://api.wikimedia.org/feed/v1/wikipedia"
        self.headers = {"User-Agent": settings.WIKIPEDIA_USER_AGENT}

    async def fetch_events(self, date: str, country_code: str = "") -> EventPool:
        month, day = date.split("-")
        url = f"{self.base_url}/onthisday/events/{month}/{day}"
        async with httpx.AsyncClient(headers=self.headers) as client:
            resp = await client.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        # 转换为 EventPool（与 Mock 实现相同的逻辑）
        # ...
```

其他 5 个 Real 实现类似占位。

### 2.4 Provider 工厂（增强 S05）

文件：`src/providers/__init__.py`（更新 S05）

```python
from typing import Any
from src.config.base import Settings

_PROVIDER_MAP = {
    "wikipedia": {
        "mock": "src.providers.impl.mock_wikipedia.MockWikipediaFetcher",
        "real": "src.providers.impl.real_wikipedia.RealWikipediaFetcher",
    },
    "regionalizer": {
        "mock": "src.providers.impl.mock_anthropic.MockAnthropicRegionalizer",
        "real": "src.providers.impl.real_anthropic.RealAnthropicRegionalizer",
    },
    "translator": {
        "mock": "src.providers.impl.mock_openai.MockOpenAITranslator",
        "real": "src.providers.impl.real_openai.RealOpenAITranslator",
    },
    "illustrator": {
        "mock": "src.providers.impl.mock_gemini.MockGeminiIllustrator",
        "real": "src.providers.impl.real_gemini.RealGeminiIllustrator",
    },
    "auditor": {
        "mock": "src.providers.impl.mock_auditor.MockAuditor",
        "real": "src.providers.impl.real_auditor.RealAuditor",
    },
    "publisher": {
        "mock": "src.providers.impl.mock_publisher.MockPublisher",
        "real": "src.providers.impl.real_publisher.RealPublisher",
    },
}

def get_provider(name: str, settings: Settings) -> Any:
    """根据配置返回 Provider 实例"""
    provider_map = _PROVIDER_MAP.get(name)
    if not provider_map:
        raise ValueError(f"未知 Provider: {name}")

    # 优先使用 *_PROVIDER 环境变量，否则按 ENV 切换
    env_key = f"{name.upper()}_PROVIDER"
    provider_type = getattr(settings, env_key, None) or ("mock" if settings.is_local else "real")

    cls_path = provider_map.get(provider_type)
    if not cls_path:
        raise ValueError(f"未知 Provider 类型: {name}/{provider_type}")

    module_path, cls_name = cls_path.rsplit(".", 1)
    import importlib
    cls = getattr(importlib.import_module(module_path), cls_name)
    return cls(settings)
```

### 2.5 切换验证脚本

文件：`scripts/test_provider_switch.py`

```python
"""验证 Provider 切换器"""
import os
from src.config.base import Settings
from src.providers import get_provider

def test_local_mode():
    os.environ["ENV"] = "local"
    settings = Settings()
    p = get_provider("wikipedia", settings)
    assert "Mock" in p.__class__.__name__
    print(f"✅ local 模式: {p.__class__.__name__}")

def test_production_mode():
    os.environ["ENV"] = "production"
    settings = Settings()
    p = get_provider("wikipedia", settings)
    assert "Real" in p.__class__.__name__
    print(f"✅ production 模式: {p.__class__.__name__}")

if __name__ == "__main__":
    test_local_mode()
    test_production_mode()
```

## 三、实施步骤

1. 编写 `src/config/base.py`（pydantic-settings）
2. 编写 6 个 Mock Provider 实现（httpx 调用 Mock Server）
3. 编写 6 个 Real Provider 实现（占位，仅类结构）
4. 更新 `src/providers/__init__.py`（工厂函数）
5. 编写 `scripts/test_provider_switch.py`
6. 运行验证脚本
7. 编写 `tests/unit/test_provider_factory.py`

## 四、验收命令

```bash
. .venv/bin/activate

# 启动 Mock Server（前置）
python -m src.mock_server.app &
sleep 2

# 验证切换器
python scripts/test_provider_switch.py
# 期望：local 模式 → Mock 类，production 模式 → Real 类

# 单元测试
pytest tests/unit/test_provider_factory.py -v
```

## 五、依赖关系

- **前置依赖**：S01、S05（Provider 接口）、S06（Mock Server）
- **后续依赖**：S09-S14（管道阶段使用 Provider）
- **阻塞关系**：Provider 切换器未就绪则管道无法运行

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| .env 文件未加载 | 中 | pydantic-settings 自动加载，`env_file=".env"` |
| Mock/Real 实现接口不一致 | 高 | ABC 强制约束 |
| httpx 超时配置错误 | 中 | 显式 `timeout=10/30` |
| API Key 在本地泄露 | 低 | .env 加入 .gitignore |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| Settings 加载 | < 50ms | `time python -c "from src.config import settings"` |
| Provider 实例化 | < 10ms | 单元测试 |
| Mock → Real 切换 | 零代码改动 | 修改 .env |

## 八、测试要求

- `ENV=local` 时返回 Mock 实现
- `ENV=production` 时返回 Real 实现
- 6 个 Provider 全部可实例化
- Mock Provider 可调用 Mock Server
