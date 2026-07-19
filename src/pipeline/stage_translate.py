"""Stage 3: Translate — 多语种翻译

使用 GPT-4o(或 Mock)将地区化事件翻译为 10 种语言
"""
import asyncio
from typing import Any

from src.models.event import RegionalizedEvent, TranslatedEvent
from src.models.countries import LANGUAGES
from src.providers.base import Translator


async def translate_to_lang(
    translator: Translator,
    regionalized: RegionalizedEvent,
    target_lang: str,
) -> TranslatedEvent:
    """翻译到单个目标语言

    Args:
        translator: 翻译器
        regionalized: 地区化事件
        target_lang: 目标语言(zh/en/ja/ko/es/fr/de/pt/ru/ar)

    Returns:
        TranslatedEvent: 翻译后事件
    """
    if target_lang not in LANGUAGES:
        raise ValueError(f"Unsupported language: {target_lang}. Supported: {LANGUAGES}")

    return await translator.translate(regionalized, target_lang)


async def translate_to_all_langs(
    translator: Translator,
    regionalized: RegionalizedEvent,
    target_langs: list[str] | None = None,
    semaphore_limit: int = 10,
) -> list[TranslatedEvent]:
    """翻译到所有目标语言

    Args:
        translator: 翻译器
        regionalized: 地区化事件
        target_langs: 目标语言列表(默认 10 种)
        semaphore_limit: 并发限制

    Returns:
        list[TranslatedEvent]: 10 个翻译结果(按 target_langs 顺序)
    """
    if target_langs is None:
        target_langs = LANGUAGES

    # 校验
    for lang in target_langs:
        if lang not in LANGUAGES:
            raise ValueError(f"Unsupported language: {lang}")

    semaphore = asyncio.Semaphore(semaphore_limit)
    results: list[TranslatedEvent | None] = [None] * len(target_langs)

    async def translate_one(idx: int, lang: str):
        async with semaphore:
            translated = await translator.translate(regionalized, lang)
            return idx, translated

    tasks = [translate_one(i, lang) for i, lang in enumerate(target_langs)]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for result in completed:
        if isinstance(result, Exception):
            raise result
        idx, translated = result
        results[idx] = translated

    if any(r is None for r in results):
        missing = [target_langs[i] for i, r in enumerate(results) if r is None]
        raise RuntimeError(f"Translation incomplete, missing: {missing}")

    return results  # type: ignore


async def translate_regionalized_list(
    translator: Translator,
    regionalized_list: list[RegionalizedEvent],
    target_langs: list[str] | None = None,
    semaphore_limit: int = 10,
) -> list[list[TranslatedEvent]]:
    """批量翻译多个地区化事件

    Args:
        translator: 翻译器
        regionalized_list: 地区化事件列表
        target_langs: 目标语言列表
        semaphore_limit: 并发限制

    Returns:
        list[list[TranslatedEvent]] — 每个事件对应 N 个翻译
    """
    if target_langs is None:
        target_langs = LANGUAGES

    semaphore = asyncio.Semaphore(semaphore_limit)

    async def translate_one_event(regionalized: RegionalizedEvent) -> list[TranslatedEvent]:
        async with semaphore:
            return await translate_to_all_langs(
                translator, regionalized, target_langs, semaphore_limit=1
            )

    tasks = [translate_one_event(r) for r in regionalized_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 暴露异常
    for r in results:
        if isinstance(r, Exception):
            raise r

    return results  # type: ignore


async def translate_with_retry(
    translator: Translator,
    regionalized: RegionalizedEvent,
    target_lang: str,
    max_retries: int = 3,
) -> TranslatedEvent:
    """带重试的翻译

    Args:
        translator: 翻译器
        regionalized: 地区化事件
        target_lang: 目标语言
        max_retries: 最大重试次数

    Returns:
        TranslatedEvent: 翻译后事件

    Raises:
        Exception: 重试 max_retries 次后仍失败
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await translator.translate(regionalized, target_lang)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # 指数退避

    raise last_exception  # type: ignore
