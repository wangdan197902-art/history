# S13 - Stage 5 audit 阶段

> 阶段：Phase 2 - 内容生产管道
> 人天：1 | 依赖：S08、S12 | 前置：illustrate 阶段就绪

---

## 一、步骤概述

实现 Stage 5 audit 阶段：调用 `Auditor` 对 IllustratedEvent 进行审核（中立性复核 + 合规性 + 数据完整性），输出 `list[AuditedEvent]`，过滤不合规内容，生成审核报告。

## 二、任务清单

### 2.1 audit 阶段实现

文件：`src/pipeline/stage_audit.py`

```python
import asyncio
from src.providers.base import Auditor
from src.models.event import IllustratedEvent, AuditedEvent
from src.pipeline.scoring import calculate_neutrality

async def audit_events(events: list[IllustratedEvent], auditor: Auditor) -> list[AuditedEvent]:
    """审核事件列表"""
    sem = asyncio.Semaphore(16)
    async def bounded(evt):
        async with sem:
            audited = await auditor.audit([evt])
            return audited[0]
    return await asyncio.gather(*[bounded(e) for e in events])

def filter_passed(events: list[AuditedEvent], min_neutrality: float = 0.7, min_compliance: float = 0.8) -> list[AuditedEvent]:
    """过滤审核通过的事件"""
    return [e for e in events
            if e.audit_pass
            and e.illustrated.translated.regionalized.neutrality_score >= min_neutrality
            and e.compliance_score >= min_compliance]
```

### 2.2 审核报告生成

文件：`src/pipeline/audit_report.py`

```python
import json
from pathlib import Path
from datetime import datetime
from src.models.event import AuditedEvent

def generate_audit_report(events: list[AuditedEvent], date: str) -> dict:
    """生成审核报告"""
    total = len(events)
    passed = sum(1 for e in events if e.audit_pass)
    failed = total - passed
    return {
        "date": date,
        "generated_at": datetime.utcnow().isoformat(),
        "total_events": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / total if total else 0,
        "failures": [
            {"id": e.illustrated.translated.original.id, "reason": e.audit_notes}
            for e in events if not e.audit_pass
        ],
    }

def save_report(report: dict, output_dir: Path = Path("09_报告")):
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"audit_{report['date']}.json"
    out_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
```

### 2.3 命令行入口

文件：`src/scripts/audit.py`

```python
"""python -m src.scripts.audit --date 07-04 --country CN"""
import argparse
import asyncio
from src.config import settings
from src.providers import get_provider
# 导入前序阶段
from src.pipeline.stage_fetch import fetch_events
from src.pipeline.stage_regionalize import regionalize_pool
from src.pipeline.stage_translate import translate_to_all_langs
from src.pipeline.stage_illustrate import illustrate_events
from src.pipeline.stage_audit import audit_events, filter_passed
from src.pipeline.audit_report import generate_audit_report, save_report

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--country", default="CN")
    args = parser.parse_args()

    fetcher = get_provider("wikipedia", settings)
    regionalizer = get_provider("regionalizer", settings)
    translator = get_provider("translator", settings)
    illustrator = get_provider("illustrator", settings)
    auditor = get_provider("auditor", settings)

    pool = await fetch_events(args.date, fetcher, args.country)
    regionalized = await regionalize_pool(pool, regionalizer)
    translated = await translate_to_all_langs(regionalized, translator)
    illustrated = await illustrate_events(translated, illustrator)
    audited = await audit_events(illustrated, auditor)

    report = generate_audit_report(audited, args.date)
    save_report(report)
    print(f"审核完成: {report['passed']}/{report['total_events']} 通过")

if __name__ == "__main__":
    asyncio.run(main())
```

## 三、实施步骤

1. 编写 `src/pipeline/stage_audit.py`
2. 编写 `src/pipeline/audit_report.py`
3. 编写 `src/scripts/audit.py`
4. 单元测试 `tests/unit/test_stage_audit.py`

## 四、验收命令

```bash
. .venv/bin/activate
python -m src.mock_server.app &
sleep 2

time python -m src.scripts.audit --date 07-04 --country CN
# 期望 < 30s
# 09_报告/audit_07-04.json 生成
```

## 五、依赖关系

- 前置：S08、S12
- 后续：S14（publish 消费 AuditedEvent）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| 中立性评分失真 | 中 | 真实 Claude 验证 |
| 审核标准过严 | 低 | 可调阈值 |
| 报告格式错误 | 低 | JSON Schema 校验 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 单日审核 | < 30s | `time` |
| 通过率 | > 90% | 报告统计 |

## 八、测试要求

- 审核报告 JSON 生成
- 通过率统计正确
- 不合规事件被过滤
