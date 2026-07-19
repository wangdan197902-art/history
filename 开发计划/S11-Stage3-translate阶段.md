# S11 - Stage 3 translate 阶段

> 阶段：Phase 2 - 内容生产管道
> 人天：1.5 | 依赖：S08、S10 | 前置：regionalize 阶段就绪

---

## 一、步骤概述

实现 Stage 3 translate 阶段：调用 `Translator`（OpenAI GPT-4o）将 RegionalizedEvent 翻译为 10 种语言，输出 `list[TranslatedEvent]`，每事件 × 10 语种 = 10 条翻译。

## 二、任务清单

### 2.1 translate 阶段实现

文件：`src/pipeline/stage_translate.py`

```python
import asyncio
from src.providers.base import Translator
from src.models.event import RegionalizedEvent, TranslatedEvent
from src.models.countries import LANGUAGES

async def translate_event(event: RegionalizedEvent, translator: Translator, target_lang: str) -> TranslatedEvent:
    """翻译单个事件到目标语言"""
    return await translator.translate([event], target_lang)[0]

async def translate_to_all_langs(events: list[RegionalizedEvent], translator: Translator) -> list[TranslatedEvent]:
    """翻译所有事件到 10 语种"""
    sem = asyncio.Semaphore(16)
    tasks = []
    for evt in events:
        for lang in LANGUAGES:
            async def bounded(evt=evt, lang=lang):
                async with sem:
                    return await translate_event(evt, translator, lang)
            tasks.append(bounded())
    return await asyncio.gather(*tasks)
```

### 2.2 命令行入口

文件：`src/scripts/translate.py`

```python
"""python -m src.scripts.translate --date 07-04 --country CN"""
import argparse
import asyncio
from src.config import settings
from src.providers import get_provider
from src.pipeline.stage_fetch import fetch_events
from src.pipeline.stage_regionalize import regionalize_pool
from src.pipeline.stage_translate import translate_to_all_langs

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--country", default="CN")
    args = parser.parse_args()

    fetcher = get_provider("wikipedia", settings)
    regionalizer = get_provider("regionalizer", settings)
    translator = get_provider("translator", settings)

    pool = await fetch_events(args.date, fetcher, args.country)
    regionalized = await regionalize_pool(pool, regionalizer)
    translated = await translate_to_all_langs(regionalized, translator)
    print(f"翻译完成: {len(translated)} 条 (期望 {len(regionalized) * 10})")

if __name__ == "__main__":
    asyncio.run(main())
```

## 三、实施步骤

1. 编写 `src/pipeline/stage_translate.py`
2. 编写 `src/scripts/translate.py`
3. 单元测试 `tests/unit/test_stage_translate.py`

## 四、验收命令

```bash
. .venv/bin/activate
python -m src.mock_server.app &
sleep 2

time python -m src.scripts.translate --date 07-04 --country CN
# 期望 < 180s（10 语种 × 30 地区 Mock）
# locales 字段 10 语种齐全
```

## 五、依赖关系

- 前置：S08、S10
- 后续：S12（illustrate 消费 TranslatedEvent）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| API rate limit | 中 | Semaphore + 退避 |
| 翻译质量 | 中 | Phase 4 GPT-4o 验证 |
| RTL 语种（阿拉伯语）显示 | 低 | Hugo 已配置 languageDirection |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 单日 10 语种 × 30 地区 | < 180s | `time` |
| 翻译完整性 | 10 语种齐全 | 自动校验 |

## 八、测试要求

- 10 语种翻译全部生成
- TranslatedEvent 字段完整
- RTL 语种方向正确
