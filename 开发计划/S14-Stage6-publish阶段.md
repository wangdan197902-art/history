# S14 - Stage 6 publish 阶段

> 阶段：Phase 2 - 内容生产管道
> 人天：1.5 | 依赖：S08、S13 | 前置：audit 阶段就绪

---

## 一、步骤概述

实现 Stage 6 publish 阶段：调用 `Publisher` 将 AuditedEvent 转换为 Hugo Markdown 文件，按 `content/{lang}/{country}/{MM-DD}.md` 结构生成，单日 30 地区 × 10 语种 = 300 个 .md 文件，含完整 frontmatter。

## 二、任务清单

### 2.1 publish 阶段实现

文件：`src/pipeline/stage_publish.py`

```python
import asyncio
from pathlib import Path
from datetime import datetime
from src.providers.base import Publisher
from src.models.event import AuditedEvent
from src.models.countries import COUNTRY_NAMES

class HugoMarkdownPublisher(Publisher):
    """生成 Hugo Markdown 文件"""

    def __init__(self, settings):
        self.settings = settings
        self.content_dir = Path("site/content")

    async def publish(self, events: list[AuditedEvent], date: str, country: str, lang: str) -> str:
        """生成单个 Markdown 文件
        路径: site/content/{lang}/{country}/{MM-DD}.md
        """
        target_dir = self.content_dir / lang / country
        target_dir.mkdir(parents=True, exist_ok=True)
        out_file = target_dir / f"{date}.md"

        frontmatter = self._gen_frontmatter(date, country, lang, events)
        body = self._gen_body(events)

        content = f"---\n{frontmatter}\n---\n\n{body}\n"
        out_file.write_text(content, encoding="utf-8")
        return str(out_file)

    def _gen_frontmatter(self, date: str, country: str, lang: str, events: list[AuditedEvent]) -> str:
        year = "2026"
        return f"""title: "{date} · {COUNTRY_NAMES.get(country, country)} 今天历史"
date: {year}-{date}T00:00:00Z
country_code: "{country}"
country_name: "{COUNTRY_NAMES.get(country, country)}"
language: "{lang}"
draft: false
event_count: {len(events)}
last_updated: "{datetime.utcnow().isoformat()}Z"
"""

    def _gen_body(self, events: list[AuditedEvent]) -> str:
        if not events:
            return f"# 今日暂无事件\n\n本日未发现历史事件。"
        sections = []
        for evt in events:
            t = evt.illustrated.translated
            section = f"""## {t.translated_title}

{t.translated_description}

**年份**: {t.regionalized.original.year}
**中立性评分**: {t.regionalized.neutrality_score:.2f}

![{evt.illustrated.image_alt}]({evt.illustrated.image_url})

*{evt.illustrated.image_caption}*

---
"""
            sections.append(section)
        return "\n".join(sections)

async def publish_all(events: list[AuditedEvent], date: str, publisher: Publisher) -> list[str]:
    """发布所有事件到对应的 Markdown 文件"""
    sem = asyncio.Semaphore(16)
    # 按 (lang, country) 分组
    grouped = {}
    for e in events:
        lang = e.illustrated.translated.lang
        country = e.illustrated.translated.regionalized.country_code
        grouped.setdefault((lang, country), []).append(e)

    async def bounded(lang, country, evts):
        async with sem:
            return await publisher.publish(evts, date, country, lang)

    tasks = [bounded(l, c, evts) for (l, c), evts in grouped.items()]
    return await asyncio.gather(*tasks)
```

### 2.2 命令行入口

文件：`src/scripts/publish.py`

```python
"""python -m src.scripts.publish --date 07-04"""
import argparse
import asyncio
from src.config import settings
from src.providers import get_provider
from src.pipeline.stage_fetch import fetch_events
from src.pipeline.stage_regionalize import regionalize_pool
from src.pipeline.stage_translate import translate_to_all_langs
from src.pipeline.stage_illustrate import illustrate_events
from src.pipeline.stage_audit import audit_events, filter_passed
from src.pipeline.stage_publish import publish_all

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--country", default="CN")
    args = parser.parse_args()

    # 完整管道
    fetcher = get_provider("wikipedia", settings)
    regionalizer = get_provider("regionalizer", settings)
    translator = get_provider("translator", settings)
    illustrator = get_provider("illustrator", settings)
    auditor = get_provider("auditor", settings)
    publisher = get_provider("publisher", settings)

    pool = await fetch_events(args.date, fetcher, args.country)
    regionalized = await regionalize_pool(pool, regionalizer)
    translated = await translate_to_all_langs(regionalized, translator)
    illustrated = await illustrate_events(translated, illustrator)
    audited = await audit_events(illustrated, auditor)
    passed = filter_passed(audited)

    files = await publish_all(passed, args.date, publisher)
    print(f"发布完成: {len(files)} 个 Markdown 文件")

if __name__ == "__main__":
    asyncio.run(main())
```

## 三、实施步骤

1. 编写 `src/pipeline/stage_publish.py`（含 HugoMarkdownPublisher）
2. 注册 HugoMarkdownPublisher 为 `mock_publisher`（在 `src/providers/impl/mock_publisher.py`）
3. 编写 `src/scripts/publish.py`
4. 单元测试 `tests/unit/test_stage_publish.py`

## 四、验收命令

```bash
. .venv/bin/activate
python -m src.mock_server.app &
sleep 2

time python -m src.scripts.publish --date 07-04 --country CN
# 期望 < 30s
# 30 × 10 = 300 个 .md 文件生成
# site/content/{lang}/{country}/07-04.md 存在

# 文件结构验证
find site/content -name "07-04.md" | wc -l
# 期望 300
```

## 五、依赖关系

- 前置：S08、S13
- 后续：S15（管道编排器调用所有阶段）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| Markdown 格式错误 | 中 | Hugo 验证 |
| frontmatter 字段缺失 | 中 | 模板强制 |
| 文件路径冲突 | 低 | 按 (lang, country) 唯一 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 单日 300 个 .md 生成 | < 30s | `time` |
| 文件数量 | 300 | `find \| wc -l` |

## 八、测试要求

- 300 个 Markdown 文件生成
- frontmatter 完整（title/date/country_code/language/event_count）
- Hugo 可识别（无格式错误）
