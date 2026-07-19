# S05 - Provider 接口抽象

> 阶段：Phase 1 - Mock 体系建设
> 人天：2 | 依赖：S01、S03、S04 | 前置：OpenAPI 契约已定义

---

## 一、步骤概述

编写 6 个 Provider 抽象基类（ABC）：`WikipediaFetcher` / `Regionalizer` / `Translator` / `Illustrator` / `Auditor` / `Publisher`，定义统一接口契约。每接口将有两份实现（Mock + Real），通过配置切换。

## 二、任务清单

### 2.1 Provider 基类

文件：`src/providers/base.py`

```python
from abc import ABC, abstractmethod
from typing import Any
from src.models.event import EventPool, RegionalizedEvent, TranslatedEvent, IllustratedEvent, AuditedEvent

class WikipediaFetcher(ABC):
    """Wikipedia OnThisDay 数据获取"""
    @abstractmethod
    async def fetch_events(self, date: str, country_code: str = "") -> EventPool:
        """获取某日历史事件"""
        pass

class Regionalizer(ABC):
    """地区化重写（Claude）"""
    @abstractmethod
    async def regionalize(self, pool: EventPool, country_code: str) -> list[RegionalizedEvent]:
        pass

class Translator(ABC):
    """多语种翻译（GPT-4o）"""
    @abstractmethod
    async def translate(self, events: list[RegionalizedEvent], target_lang: str) -> list[TranslatedEvent]:
        pass

class Illustrator(ABC):
    """配图生成（Gemini）"""
    @abstractmethod
    async def illustrate(self, events: list[TranslatedEvent]) -> list[IllustratedEvent]:
        pass

class Auditor(ABC):
    """内容审核"""
    @abstractmethod
    async def audit(self, events: list[IllustratedEvent]) -> list[AuditedEvent]:
        pass

class Publisher(ABC):
    """Markdown 生成与发布"""
    @abstractmethod
    async def publish(self, events: list[AuditedEvent], date: str, country: str, lang: str) -> str:
        """返回生成的 Markdown 文件路径"""
        pass
```

### 2.2 Provider 工厂函数

文件：`src/providers/__init__.py`

```python
from typing import Any
from src.config.base import Settings

def get_provider(name: str, settings: Settings) -> Any:
    """根据配置返回 Provider 实例
    name: 'wikipedia' | 'regionalizer' | 'translator' | 'illustrator' | 'auditor' | 'publisher'
    """
    env = settings.ENV  # local | production
    mapping = {
        ("wikipedia", "local"): "src.providers.impl.mock_wikipedia.MockWikipediaFetcher",
        ("wikipedia", "production"): "src.providers.impl.real_wikipedia.RealWikipediaFetcher",
        # ... 其他 5 个 Provider 同理
    }
    cls_path = mapping.get((name, env))
    if not cls_path:
        raise ValueError(f"未知 Provider: {name}/{env}")
    module_path, cls_name = cls_path.rsplit(".", 1)
    import importlib
    cls = getattr(importlib.import_module(module_path), cls_name)
    return cls(settings)
```

### 2.3 占位实现文件（仅创建文件结构，实际实现在 S06-S08）

需要创建以下空文件：
- `src/providers/impl/__init__.py`
- `src/providers/impl/mock_wikipedia.py`
- `src/providers/impl/mock_anthropic.py`（Regionalizer）
- `src/providers/impl/mock_openai.py`（Translator）
- `src/providers/impl/mock_gemini.py`（Illustrator）
- `src/providers/impl/mock_auditor.py`
- `src/providers/impl/mock_publisher.py`
- `src/providers/impl/real_wikipedia.py`
- `src/providers/impl/real_anthropic.py`
- `src/providers/impl/real_openai.py`
- `src/providers/impl/real_gemini.py`
- `src/providers/impl/real_auditor.py`
- `src/providers/impl/real_publisher.py`

每个占位文件内容：
```python
"""Provider 实现占位 — S06/S08 实现"""
from src.providers.base import WikipediaFetcher  # 替换为对应基类
from src.config.base import Settings

class MockWikipediaFetcher(WikipediaFetcher):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def fetch_events(self, date: str, country_code: str = "") -> EventPool:
        raise NotImplementedError("S06 实现")
```

## 三、实施步骤

1. 编写 `src/providers/base.py`（6 个 ABC）
2. 编写 `src/providers/__init__.py`（工厂函数）
3. 创建 `src/providers/impl/` 目录
4. 创建 13 个占位实现文件（6 Mock + 6 Real + 1 init）
5. 编写 `tests/unit/test_providers_base.py` 验证 ABC 接口

## 四、验收命令

```bash
. .venv/bin/activate
pytest tests/unit/test_providers_base.py -v
python -c "from src.providers import get_provider; print('OK')"
```

## 五、依赖关系

- **前置依赖**：S01、S03（数据模型）、S04（契约）
- **后续依赖**：S06（Mock 实现）、S08（Real 实现 + 切换器）
- **阻塞关系**：Provider 接口未定义则无法实现 Mock/Real

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| 接口设计过早抽象 | 中 | S18 垂直切片验证 |
| 异步接口设计错误 | 中 | 全部用 `async def`，保持一致 |
| 工厂函数映射错误 | 低 | 单元测试覆盖 |

## 七、性能预算

无显著性能开销（仅接口定义）。

## 八、测试要求

- 6 个 ABC 类可被实例化（子类继承）
- 工厂函数 `get_provider()` 返回正确实例
- 异步方法签名正确（`async def`）
