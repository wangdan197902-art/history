# S09 - Stage 1 fetch 阶段

> 阶段：Phase 2 - 内容生产管道
> 人天：1 | 依赖：S05、S06、S08 | 前置：Mock Server + Provider 切换器就绪

---

## 一、步骤概述

实现 Stage 1 fetch 阶段：调用 `WikipediaFetcher` 获取某日历史事件，输出 `EventPool`。支持单日 fetch 和批量 fetch（366 天）。

## 二、任务清单

### 2.1 fetch 阶段实现

文件：`src/pipeline/stage_fetch.py`

```python
import asyncio
from datetime import date, timedelta
from src.providers.base import WikipediaFetcher
from src.models.event import EventPool
from src.models.countries import ALL_COUNTRIES

async def fetch_events(date_str: str, fetcher: WikipediaFetcher, country_code: str = "") -> EventPool:
    """获取单日事件池"""
    return await fetcher.fetch_events(date_str, country_code)

async def fetch_year(fetcher: WikipediaFetcher, year: int = 2024) -> dict[str, list[EventPool]]:
    """批量获取全年 366 天 × 30 地区事件池"""
    sem = asyncio.Semaphore(16)
    start = date(year, 1, 1)
    results = {}

    async def bounded_fetch(d: str, c: str):
        async with sem:
            return await fetch_events(d, fetcher, c)

    tasks = []
    for day_offset in range(366):
        d = start + timedelta(days=day_offset)
        date_str = d.strftime("%m-%d")
        for c in ALL_COUNTRIES:
            tasks.append((date_str, c, bounded_fetch(date_str, c)))

    for date_str, country, task in tasks:
        pool = await task
        results.setdefault(date_str, []).append(pool)

    return results
```

### 2.2 命令行入口

文件：`src/scripts/fetch_events.py`

```python
"""命令行入口: python -m src.scripts.fetch_events --date 07-04 --country CN"""
import argparse
import asyncio
import json
from src.config import settings
from src.providers import get_provider
from src.pipeline.stage_fetch import fetch_events

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="日期 MM-DD")
    parser.add_argument("--country", default="CN")
    args = parser.parse_args()

    fetcher = get_provider("wikipedia", settings)
    pool = await fetch_events(args.date, fetcher, args.country)
    print(pool.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

## 三、实施步骤

1. 编写 `src/pipeline/__init__.py`
2. 编写 `src/pipeline/stage_fetch.py`
3. 编写 `src/scripts/fetch_events.py`
4. 单元测试 `tests/unit/test_stage_fetch.py`

## 四、验收命令

```bash
. .venv/bin/activate
python -m src.mock_server.app &
sleep 2

# 单日 fetch
time python -m src.scripts.fetch_events --date 07-04 --country CN
# 期望 < 5s，返回 EventPool JSON

# 366 天全量 fetch
time python -c "
import asyncio
from src.config import settings
from src.providers import get_provider
from src.pipeline.stage_fetch import fetch_year
asyncio.run(fetch_year(get_provider('wikipedia', settings)))
"
# 期望 < 30min（Mock 模式）
```

## 五、依赖关系

- 前置：S05、S06、S08
- 后续：S10（regionalize 消费 EventPool）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| asyncio Semaphore 限制 | 中 | 默认 16，可配置 |
| Mock 响应慢 | 低 | Mock 模式 < 200ms |
| 网络超时 | 中 | httpx timeout=10 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 单日 fetch | < 5s | `time` |
| 366 天全量 | < 30min | `time` |

## 八、测试要求

- 单日 fetch 返回有效 EventPool
- 366 天全量 fetch 完成
- Schema 校验通过
