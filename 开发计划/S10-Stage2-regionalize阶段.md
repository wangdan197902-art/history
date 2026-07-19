# S10 - Stage 2 regionalize 阶段

> 阶段：Phase 2 - 内容生产管道
> 人天：1.5 | 依赖：S08、S09 | 前置：fetch 阶段就绪

---

## 一、步骤概述

实现 Stage 2 regionalize 阶段：调用 `Regionalizer`（Anthropic Claude）对 EventPool 中的每个事件进行地区化重写，输出 `list[RegionalizedEvent]`，包含中立性评分。

## 二、任务清单

### 2.1 regionalize 阶段实现

文件：`src/pipeline/stage_regionalize.py`

```python
import asyncio
from src.providers.base import Regionalizer
from src.models.event import EventPool, RegionalizedEvent

async def regionalize_pool(pool: EventPool, regionalizer: Regionalizer) -> list[RegionalizedEvent]:
    """对单个事件池进行地区化重写"""
    return await regionalizer.regionalize(pool, pool.country_code)

async def regionalize_year(pools: dict[str, list[EventPool]], regionalizer: Regionalizer) -> dict[str, list[RegionalizedEvent]]:
    """批量地区化全年事件池"""
    sem = asyncio.Semaphore(16)
    results = {}

    async def bounded_regionalize(pool: EventPool):
        async with sem:
            return await regionalize_pool(pool, regionalizer)

    for date_str, pool_list in pools.items():
        tasks = [bounded_regionalize(p) for p in pool_list]
        done = await asyncio.gather(*tasks)
        results[date_str] = [item for sublist in done for item in sublist]

    return results
```

### 2.2 中立性评分逻辑

文件：`src/pipeline/scoring.py`

```python
from src.models.event import RegionalizedEvent

def calculate_neutrality(event: RegionalizedEvent) -> float:
    """计算中立性评分 0-1
    基础规则：
    - 无明显立场词 → 0.9
    - 含"帝国主义/殖民"等敏感词 → 0.6
    - 含"侵略/屠杀"等强立场词 → 0.4
    """
    text = (event.regional_title + event.regional_description).lower()
    strong_words = ["侵略", "屠杀", "帝国主义", "殖民"]
    mild_words = ["争议", "冲突"]

    score = 0.9
    for w in strong_words:
        if w in text:
            score -= 0.3
    for w in mild_words:
        if w in text:
            score -= 0.15
    return max(0.0, min(1.0, score))
```

### 2.3 命令行入口

文件：`src/scripts/regionalize.py`

```python
"""python -m src.scripts.regionalize --date 07-04 --country CN"""
import argparse
import asyncio
from src.config import settings
from src.providers import get_provider
from src.pipeline.stage_fetch import fetch_events
from src.pipeline.stage_regionalize import regionalize_pool

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--country", default="CN")
    args = parser.parse_args()

    fetcher = get_provider("wikipedia", settings)
    regionalizer = get_provider("regionalizer", settings)

    pool = await fetch_events(args.date, fetcher, args.country)
    results = await regionalize_pool(pool, regionalizer)
    for r in results:
        print(r.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

## 三、实施步骤

1. 编写 `src/pipeline/stage_regionalize.py`
2. 编写 `src/pipeline/scoring.py`（中立性评分）
3. 编写 `src/scripts/regionalize.py`
4. 单元测试 `tests/unit/test_stage_regionalize.py`

## 四、验收命令

```bash
. .venv/bin/activate
python -m src.mock_server.app &
sleep 2

time python -m src.scripts.regionalize --date 07-04 --country CN
# 期望 < 90s（30 地区 Mock）
# 中立性评分 0.7+
```

## 五、依赖关系

- 前置：S08、S09
- 后续：S11（translate 消费 RegionalizedEvent）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| 中立性评分失真 | 中 | Phase 4 真实 Claude 验证 |
| Claude 响应慢 | 中 | Semaphore 限流 |
| 地区化内容偏离原意 | 中 | 审核阶段过滤 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 单日 30 地区 | < 90s | `time` |
| 中立性评分 | ≥ 0.7 | 自动校验 |

## 八、测试要求

- 30 地区全部生成 RegionalizedEvent
- 中立性评分 ≥ 0.7
- 字段完整（regional_title / regional_description / neutrality_score）
