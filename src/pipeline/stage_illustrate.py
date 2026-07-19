"""Stage 4: Illustrate — 配图生成

使用 Gemini(或 Mock)为翻译后的事件生成配图
"""
import asyncio
from typing import Any

from src.models.event import IllustratedEvent, TranslatedEvent
from src.providers.base import Illustrator


async def illustrate_translated(
    illustrator: Illustrator,
    translated: TranslatedEvent,
) -> IllustratedEvent:
    """为单个翻译事件生成配图

    Args:
        illustrator: 配图生成器
        translated: 翻译后事件

    Returns:
        IllustratedEvent: 配图后事件
    """
    return await illustrator.illustrate(translated)


async def illustrate_batch(
    illustrator: Illustrator,
    translated_list: list[TranslatedEvent],
    semaphore_limit: int = 8,
) -> list[IllustratedEvent]:
    """批量配图

    Args:
        illustrator: 配图生成器
        translated_list: 翻译后事件列表
        semaphore_limit: 并发限制

    Returns:
        list[IllustratedEvent]: 配图后事件列表(顺序与输入一致)
    """
    semaphore = asyncio.Semaphore(semaphore_limit)
    results: list[IllustratedEvent | None] = [None] * len(translated_list)

    async def illustrate_one(idx: int, translated: TranslatedEvent):
        async with semaphore:
            illustrated = await illustrator.illustrate(translated)
            return idx, illustrated

    tasks = [illustrate_one(i, t) for i, t in enumerate(translated_list)]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for result in completed:
        if isinstance(result, Exception):
            raise result
        idx, illustrated = result
        results[idx] = illustrated

    # 暴露异常
    if any(r is None for r in results):
        missing = [i for i, r in enumerate(results) if r is None]
        raise RuntimeError(f"Illustrate incomplete, missing indices: {missing}")

    return results  # type: ignore


async def illustrate_multi_lang(
    illustrator: Illustrator,
    translated_events: list[TranslatedEvent],
    semaphore_limit: int = 8,
) -> list[IllustratedEvent]:
    """为多语言翻译事件配图

    Args:
        illustrator: 配图生成器
        translated_events: 多语言翻译事件(同一事件的不同语言版本)
        semaphore_limit: 并发限制

    Returns:
        list[IllustratedEvent]: 每个语言版本一个配图
    """
    return await illustrate_batch(illustrator, translated_events, semaphore_limit)


async def download_image(
    image_url: str,
    save_path: str,
    semaphore: asyncio.Semaphore | None = None,
) -> str:
    """下载图片到本地

    Args:
        image_url: 图片 URL
        save_path: 本地保存路径
        semaphore: 并发限制(可选)

    Returns:
        str: 本地文件路径
    """
    import httpx
    from pathlib import Path

    async def _download():
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            Path(save_path).write_bytes(response.content)
        return save_path

    if semaphore:
        async with semaphore:
            return await _download()
    return await _download()
