# S03 - 数据模型与 Mock 样本生成

> 阶段：Phase 0 - 环境与契约基础
> 人天：1.5 | 依赖：S01 | 前置：Python 环境就绪

---

## 一、步骤概述

定义事件池（EventPool）数据模型 JSON Schema、地区列表、语种列表、日期范围，并编写 `gen_mock_data.py` 脚本生成 30 地区 × 366 天 = 10,980 个 Mock 事件池 JSON 文件（作为 Mock Server 数据源）。

## 二、任务清单

### 2.1 数据模型定义

文件：`src/models/event.py`

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class Event(BaseModel):
    """单条历史事件"""
    id: str = Field(description="事件唯一 ID，如 evt_20260704_CN_001")
    date: str = Field(description="事件日期 YYYY-MM-DD")
    year: int = Field(description="事件发生的年份")
    title: str = Field(description="事件标题（原始语言）")
    description: str = Field(description="事件描述（原始语言）")
    wikipedia_url: str = Field(description="Wikipedia 原文链接")
    categories: list[str] = Field(default_factory=list, description="事件分类")
    location: Optional[str] = Field(None, description="事件地点")
    deaths: Optional[int] = Field(None, description="死亡人数")
    injuries: Optional[int] = Field(None, description="受伤人数")

class RegionalizedEvent(BaseModel):
    """地区化后的事件"""
    original: Event
    country_code: str
    regional_title: str
    regional_description: str
    neutrality_score: float = Field(ge=0, le=1, description="中立性评分 0-1")
    regional_tags: list[str] = Field(default_factory=list)

class TranslatedEvent(BaseModel):
    """翻译后的事件"""
    regionalized: RegionalizedEvent
    lang: str
    translated_title: str
    translated_description: str

class IllustratedEvent(BaseModel):
    """配图后的事件"""
    translated: TranslatedEvent
    image_url: str
    image_alt: str
    image_caption: str
    image_credit: Optional[str] = None

class AuditedEvent(BaseModel):
    """审核后的事件"""
    illustrated: IllustratedEvent
    audit_pass: bool
    audit_notes: str = ""
    compliance_score: float = Field(ge=0, le=1)

class EventPool(BaseModel):
    """事件池 — 单日单地区的事件集合"""
    date: str
    country_code: str
    events: list[Event] = Field(default_factory=list)
    source: str = "wikipedia"
    fetched_at: str
```

文件：`src/models/countries.py`

```python
# 30 地区分级清单（来自 02_业务架构体系.md）
COUNTRIES_TIER_1 = ["CN", "US", "JP", "KR", "UK", "DE", "FR"]  # 7 个核心
COUNTRIES_TIER_2 = ["RU", "BR", "IN", "AU", "CA", "IT", "ES", "MX"]  # 8 个重要
COUNTRIES_TIER_3 = ["ID", "TH", "VN", "SG", "MY", "PH", "SA", "AE",
                    "EG", "ZA", "NG", "TR", "PL", "NL", "SE"]  # 15 个拓展

ALL_COUNTRIES = COUNTRIES_TIER_1 + COUNTRIES_TIER_2 + COUNTRIES_TIER_3  # 30 个

COUNTRY_NAMES = {
    "CN": "中国", "US": "美国", "JP": "日本", "KR": "韩国", "UK": "英国",
    "DE": "德国", "FR": "法国", "RU": "俄罗斯", "BR": "巴西", "IN": "印度",
    "AU": "澳大利亚", "CA": "加拿大", "IT": "意大利", "ES": "西班牙", "MX": "墨西哥",
    "ID": "印度尼西亚", "TH": "泰国", "VN": "越南", "SG": "新加坡", "MY": "马来西亚",
    "PH": "菲律宾", "SA": "沙特阿拉伯", "AE": "阿联酋", "EG": "埃及", "ZA": "南非",
    "NG": "尼日利亚", "TR": "土耳其", "PL": "波兰", "NL": "荷兰", "SE": "瑞典",
}

LANGUAGES = ["zh", "en", "ja", "ko", "es", "fr", "de", "pt", "ru", "ar"]
LANGUAGE_NAMES = {
    "zh": "中文", "en": "English", "ja": "日本語", "ko": "한국어",
    "es": "Español", "fr": "Français", "de": "Deutsch", "pt": "Português",
    "ru": "Русский", "ar": "العربية",
}
```

### 2.2 Mock 数据生成脚本

文件：`scripts/gen_mock_data.py`

```python
"""生成 30 地区 × 366 天 Mock 事件池 JSON"""
import json
from pathlib import Path
from datetime import date, timedelta
from src.models.event import EventPool, Event
from src.models.countries import ALL_COUNTRIES

FIXTURE_DIR = Path("tests/fixtures/mock_responses/wikipedia")

# 5 个日期样本（覆盖闰年/季节/节假日）
SAMPLE_DATES = ["01-01", "02-29", "07-04", "10-01", "12-25"]

def gen_event(date_str: str, country: str, idx: int) -> Event:
    return Event(
        id=f"evt_{date_str.replace('-', '')}_{country}_{idx:03d}",
        date=f"2026-{date_str}",
        year=1900 + (idx * 13) % 125,
        title=f"Mock 事件 {country} {date_str} #{idx}",
        description=f"这是 {country} 在 {date_str} 的第 {idx} 个 Mock 历史事件。实际内容由 Wikipedia API 提供。",
        wikipedia_url=f"https://en.wikipedia.org/wiki/Mock_{country}_{date_str}",
        categories=["mock", country.lower()],
        location=None,
    )

def gen_event_pool(date_str: str, country: str) -> EventPool:
    events = [gen_event(date_str, country, i) for i in range(3)]  # 每日每地区 3 个事件
    return EventPool(
        date=f"2026-{date_str}",
        country_code=country,
        events=events,
        source="wikipedia_mock",
        fetched_at="2026-07-19T00:00:00Z",
    )

def main():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    # 生成全年 366 天 × 30 地区 = 10,980 个文件
    start = date(2024, 1, 1)  # 闰年
    for day_offset in range(366):
        d = start + timedelta(days=day_offset)
        date_str = d.strftime("%m-%d")
        for country in ALL_COUNTRIES:
            pool = gen_event_pool(date_str, country)
            out_file = FIXTURE_DIR / f"{date_str}_{country}.json"
            out_file.write_text(pool.model_dump_json(indent=2), encoding="utf-8")
    print(f"已生成 {366 * 30} 个 Mock 事件池文件到 {FIXTURE_DIR}")

if __name__ == "__main__":
    main()
```

### 2.3 5 日期 × 30 地区 × 10 语种详细 fixture

文件：`scripts/gen_detailed_fixtures.py`

```python
"""生成 5 日期样本 × 30 地区 × 10 语种的详细 fixture（用于集成测试）"""
# 5 日期：覆盖闰年(02-29)、节假日(01-01/10-01/12-25)、独立日(07-04)
# 每个样本包含完整的 7 阶段输出：fetch → regionalize → translate → illustrate → audit
# 共 5 × 30 × 10 = 1,500 个详细 fixture 文件
# 用于 S17 集成测试
```

### 2.4 数据 Schema 验证

文件：`tests/unit/test_models.py`

```python
import pytest
from src.models.event import EventPool, Event

def test_event_pool_schema():
    pool = EventPool(
        date="2026-07-04",
        country_code="CN",
        events=[],
        source="wikipedia",
        fetched_at="2026-07-19T00:00:00Z",
    )
    assert pool.country_code == "CN"
    assert pool.events == []

def test_event_validation():
    with pytest.raises(ValueError):
        Event(id="", date="2026-07-04", year=2026, title="", description="", wikipedia_url="")
```

## 三、实施步骤

1. 编写 `src/models/event.py`（pydantic 模型）
2. 编写 `src/models/countries.py`（30 地区 + 10 语种）
3. 编写 `src/models/__init__.py`（导出）
4. 编写 `scripts/gen_mock_data.py`
5. 运行 `python scripts/gen_mock_data.py` 生成 10,980 个文件
6. 编写 `scripts/gen_detailed_fixtures.py`（生成 1,500 个详细 fixture）
7. 编写 `tests/unit/test_models.py` 验证 Schema
8. 运行测试确认数据模型正确

## 四、验收命令

```bash
. .venv/bin/activate

# 生成 Mock 数据
time python scripts/gen_mock_data.py
# 期望 < 60s，生成 10,980 个 JSON 文件

# 文件数量验证
find tests/fixtures/mock_responses/wikipedia -name "*.json" | wc -l
# 期望 10980

# 单文件大小验证
ls -la tests/fixtures/mock_responses/wikipedia/01-01_CN.json
# 期望 < 5KB

# 总体积验证
du -sh tests/fixtures/mock_responses/wikipedia/
# 期望 < 200MB

# Schema 测试
pytest tests/unit/test_models.py -v
```

## 五、依赖关系

- **前置依赖**：S01（Python 环境 + pydantic-settings）
- **后续依赖**：S07（Mock 数据加载器）、S17（集成测试）
- **阻塞关系**：S06 Mock Server 依赖本步骤生成的 fixture

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| 10,980 个文件体积过大 | 中 | 每文件 < 5KB，总体积 < 200MB，可接受 |
| Git 仓库膨胀 | 中 | Mock fixture 加入 `.gitignore`，用 `git lfs` 管理 |
| 闰年 02-29 数据缺失 | 低 | 使用 2024 闰年生成，确保 02-29 有数据 |
| Schema 校验失败 | 高 | pydantic 自动校验，测试覆盖 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 10,980 文件生成时间 | < 60s | `time python scripts/gen_mock_data.py` |
| 单文件大小 | < 50 KB | `ls -la` |
| 总体积 | < 200 MB | `du -sh` |
| Schema 校验 | < 1s | `pytest tests/unit/test_models.py` |

## 八、测试要求

- `EventPool` / `Event` 等 pydantic 模型可正确序列化/反序列化
- 10,980 个 Mock 文件全部生成
- Schema 校验通过（`pytest tests/unit/test_models.py`）
- 5 日期 × 30 地区 × 10 语种 fixture 数据完整
