# S12 - Stage 4 illustrate 阶段

> 阶段：Phase 2 - 内容生产管道
> 人天：1.5 | 依赖：S08、S11 | 前置：translate 阶段就绪

---

## 一、步骤概述

实现 Stage 4 illustrate 阶段：调用 `Illustrator`（Google Gemini）为每个 TranslatedEvent 生成配图 URL、alt 文本、caption，输出 `list[IllustratedEvent]`，并下载图片为 WebP 格式（< 100KB）。

## 二、任务清单

### 2.1 illustrate 阶段实现

文件：`src/pipeline/stage_illustrate.py`

```python
import asyncio
from src.providers.base import Illustrator
from src.models.event import TranslatedEvent, IllustratedEvent

async def illustrate_events(events: list[TranslatedEvent], illustrator: Illustrator) -> list[IllustratedEvent]:
    """为事件列表生成配图"""
    sem = asyncio.Semaphore(16)
    async def bounded(evt):
        async with sem:
            return await illustrator.illustrate([evt])
    results = await asyncio.gather(*[bounded(e) for e in events])
    return [item for sublist in results for item in sublist]
```

### 2.2 图片下载与处理

文件：`src/pipeline/image_processor.py`

```python
import httpx
from pathlib import Path
from PIL import Image
import io

async def download_and_convert(url: str, save_path: Path, max_size: int = 100 * 1024) -> Path:
    """下载图片并转换为 WebP，控制体积 < 100KB"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=30)
        resp.raise_for_status()

    img = Image.open(io.BytesIO(resp.content))
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # 生成 400w 和 800w 两个版本
    for width, suffix in [(400, "400w"), (800, "800w")]:
        out = save_path.with_name(f"{save_path.stem}_{suffix}.webp")
        img_copy = img.copy()
        img_copy.thumbnail((width, width * 3 // 4))
        quality = 85
        while quality > 30:
            buf = io.BytesIO()
            img_copy.save(buf, format="WEBP", quality=quality)
            if buf.tell() < max_size:
                out.write_bytes(buf.getvalue())
                break
            quality -= 5
    return save_path
```

### 2.3 命令行入口

文件：`src/scripts/illustrate.py`

```python
"""python -m src.scripts.illustrate --date 07-04 --country CN"""
import argparse
import asyncio
from src.config import settings
from src.providers import get_provider
from src.pipeline.stage_fetch import fetch_events
from src.pipeline.stage_regionalize import regionalize_pool
from src.pipeline.stage_translate import translate_to_all_langs
from src.pipeline.stage_illustrate import illustrate_events

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--country", default="CN")
    args = parser.parse_args()

    fetcher = get_provider("wikipedia", settings)
    regionalizer = get_provider("regionalizer", settings)
    translator = get_provider("translator", settings)
    illustrator = get_provider("illustrator", settings)

    pool = await fetch_events(args.date, fetcher, args.country)
    regionalized = await regionalize_pool(pool, regionalizer)
    translated = await translate_to_all_langs(regionalized, translator)
    illustrated = await illustrate_events(translated, illustrator)
    print(f"配图完成: {len(illustrated)} 条")

if __name__ == "__main__":
    asyncio.run(main())
```

## 三、实施步骤

1. 编写 `src/pipeline/stage_illustrate.py`
2. 编写 `src/pipeline/image_processor.py`
3. 编写 `src/scripts/illustrate.py`
4. 单元测试 `tests/unit/test_stage_illustrate.py`

## 四、验收命令

```bash
. .venv/bin/activate
python -m src.mock_server.app &
sleep 2

time python -m src.scripts.illustrate --date 07-04 --country CN
# 期望 < 60s（30 张 Mock 图）
# WebP 输出，单图 < 100KB
# alt/caption 齐全
```

## 五、依赖关系

- 前置：S08、S11
- 后续：S13（audit 消费 IllustratedEvent）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| Gemini 配图 API 失败 | 中 | tenacity 重试 |
| 图片下载超时 | 中 | httpx timeout=30 |
| WebP 体积超限 | 低 | 自动降低 quality |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 单日 30 张 Mock 图 | < 60s | `time` |
| 单图体积 | < 100 KB | `ls -la` |
| 双源响应式（400w/800w） | 100% | 文件存在性检查 |

## 八、测试要求

- 30 张 WebP 图片生成
- 400w 和 800w 双源齐全
- alt/caption 字段完整
- 单图 < 100KB
