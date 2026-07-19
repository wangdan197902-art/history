# S15 - asyncio 管道编排器

> 阶段：Phase 2 - 内容生产管道
> 人天：1.5 | 依赖：S09-S14 | 前置：6 个阶段全部就绪

---

## 一、步骤概述

实现管道编排器 `orchestrator.py`，串联 7 阶段（fetch → regionalize → translate → illustrate → audit → publish → build），用 asyncio 协程模型，阶段间串行，阶段内并发（30 地区 / 10 语种并发）。

## 二、任务清单

### 2.1 编排器实现

文件：`src/pipeline/orchestrator.py`

```python
import asyncio
import time
from datetime import date, timedelta
from typing import Optional
from src.config.base import Settings
from src.providers import get_provider
from src.pipeline.stage_fetch import fetch_events, fetch_year
from src.pipeline.stage_regionalize import regionalize_pool
from src.pipeline.stage_translate import translate_to_all_langs
from src.pipeline.stage_illustrate import illustrate_events
from src.pipeline.stage_audit import audit_events, filter_passed
from src.pipeline.stage_publish import publish_all
from src.models.event import EventPool, RegionalizedEvent, TranslatedEvent, IllustratedEvent, AuditedEvent

class PipelineResult:
    def __init__(self):
        self.stages: dict[str, float] = {}  # stage_name -> duration_sec
        self.total_events = 0
        self.passed_events = 0
        self.published_files = 0

    def add_stage(self, name: str, duration: float):
        self.stages[name] = duration

    def summary(self) -> dict:
        return {
            "total_duration_sec": sum(self.stages.values()),
            "stages": self.stages,
            "total_events": self.total_events,
            "passed_events": self.passed_events,
            "published_files": self.published_files,
            "pass_rate": self.passed_events / self.total_events if self.total_events else 0,
        }

async def run_pipeline(date_str: str, config: Settings) -> PipelineResult:
    """运行单日完整管道"""
    result = PipelineResult()

    # 阶段 1: fetch
    t = time.perf_counter()
    fetcher = get_provider("wikipedia", config)
    pools = []
    for country in ["CN"]:  # 默认仅 CN，可扩展
        pool = await fetch_events(date_str, fetcher, country)
        pools.append(pool)
    result.add_stage("fetch", time.perf_counter() - t)

    # 阶段 2: regionalize
    t = time.perf_counter()
    regionalizer = get_provider("regionalizer", config)
    all_regionalized = []
    for pool in pools:
        regionalized = await regionalize_pool(pool, regionalizer)
        all_regionalized.extend(regionalized)
    result.add_stage("regionalize", time.perf_counter() - t)

    # 阶段 3: translate
    t = time.perf_counter()
    translator = get_provider("translator", config)
    translated = await translate_to_all_langs(all_regionalized, translator)
    result.add_stage("translate", time.perf_counter() - t)

    # 阶段 4: illustrate
    t = time.perf_counter()
    illustrator = get_provider("illustrator", config)
    illustrated = await illustrate_events(translated, illustrator)
    result.add_stage("illustrate", time.perf_counter() - t)

    # 阶段 5: audit
    t = time.perf_counter()
    auditor = get_provider("auditor", config)
    audited = await audit_events(illustrated, auditor)
    passed = filter_passed(audited)
    result.add_stage("audit", time.perf_counter() - t)
    result.total_events = len(audited)
    result.passed_events = len(passed)

    # 阶段 6: publish
    t = time.perf_counter()
    publisher = get_provider("publisher", config)
    files = await publish_all(passed, date_str, publisher)
    result.add_stage("publish", time.perf_counter() - t)
    result.published_files = len(files)

    return result

async def run_year_pipeline(config: Settings, year: int = 2024) -> list[PipelineResult]:
    """运行全年 366 天管道"""
    start = date(year, 1, 1)
    results = []
    for day_offset in range(366):
        d = start + timedelta(days=day_offset)
        date_str = d.strftime("%m-%d")
        print(f"[{day_offset+1}/366] 处理 {date_str}...")
        result = await run_pipeline(date_str, config)
        results.append(result)
    return results

if __name__ == "__main__":
    import sys
    import json
    from src.config import settings

    target_date = sys.argv[1] if len(sys.argv) > 1 else "07-04"
    result = asyncio.run(run_pipeline(target_date, settings))
    print(json.dumps(result.summary(), indent=2, ensure_ascii=False))
```

### 2.2 性能埋点

文件：`src/pipeline/perf_hooks.py`

```python
import time
import json
from pathlib import Path
from contextlib import asynccontextmanager

@asynccontextmanager
async def perf_timer(stage_name: str, budget_sec: float, log_dir: Path = Path("logs/perf")):
    """性能埋点上下文管理器"""
    start = time.perf_counter()
    yield
    duration = time.perf_counter() - start
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{stage_name}.json"
    log_file.write_text(json.dumps({
        "stage": stage_name,
        "duration_sec": duration,
        "budget_sec": budget_sec,
        "overrun": duration > budget_sec,
    }, indent=2))
```

## 三、实施步骤

1. 编写 `src/pipeline/orchestrator.py`（编排器）
2. 编写 `src/pipeline/perf_hooks.py`（性能埋点）
3. 在每个阶段调用中添加性能埋点
4. 编写 `tests/integration/test_pipeline.py` 集成测试

## 四、验收命令

```bash
. .venv/bin/activate
python -m src.mock_server.app &
sleep 2

# 单日完整管道
time python -m src.pipeline.orchestrator 07-04
# 期望 < 10min（Mock 模式）
# 输出 stage 耗时统计

# 全年管道（可选）
python -c "
import asyncio
from src.config import settings
from src.pipeline.orchestrator import run_year_pipeline
asyncio.run(run_year_pipeline(settings))
"
```

## 五、依赖关系

- 前置：S09-S14（6 个阶段）
- 后续：S16（diskcache）、S17（测试）、S18（垂直切片）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| asyncio fd 耗尽 | 高 | `ulimit -n 65535` + Semaphore(16) |
| 阶段间数据传递 IO | 中 | 内存传递，无磁盘 IO |
| 单阶段失败导致全管道失败 | 中 | tenacity 重试 + 异常隔离 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 单日完整管道 | < 10min | `time` |
| 366 天全量管道 | < 60 小时（首次）/ 6 小时（缓存命中） | `time` |
| 阶段间数据传递 | < 5s/阶段 | 埋点统计 |

## 八、测试要求

- 单日管道端到端跑通
- 6 个阶段全部执行
- 性能埋点正常输出
- 集成测试通过
