"""Stage 2: Regionalize — 地区化重写

使用 Claude(或 Mock)将原始事件地区化,确保中立性
"""
import asyncio
from typing import Any

from src.models.event import EventPool, RegionalizedEvent
from src.providers.base import Regionalizer
from src.pipeline.scoring import calculate_neutrality_score, calculate_relevance_score


async def regionalize_event(
    regionalizer: Regionalizer,
    event_pool: EventPool,
    country_code: str | None = None,
) -> list[RegionalizedEvent]:
    """地区化单日事件池

    Args:
        regionalizer: 地区化重写器
        event_pool: 事件池
        country_code: 目标地区(默认使用 pool.country_code)

    Returns:
        list[RegionalizedEvent]: 地区化事件列表
    """
    if country_code is None:
        country_code = event_pool.country_code

    # 批量调用
    results = await regionalizer.regionalize_pool(event_pool)

    # 评分校准
    for regionalized in results:
        # 重新计算中立性评分(基于文本)
        regionalized.neutrality_score = calculate_neutrality_score(
            regionalized.regional_description
        )

    return results


async def regionalize_pool(
    regionalizer: Regionalizer,
    pool: EventPool,
    semaphore_limit: int = 8,
) -> list[RegionalizedEvent]:
    """地区化事件池(并发版)

    Args:
        regionalizer: 地区化重写器
        pool: 事件池
        semaphore_limit: 并发限制(默认 8,因为 LLM 调用较慢)

    Returns:
        list[RegionalizedEvent]: 地区化事件列表(顺序与输入事件一致)
    """
    semaphore = asyncio.Semaphore(semaphore_limit)
    results: list[RegionalizedEvent | None] = [None] * len(pool.events)

    async def regionalize_one(idx: int, event):
        async with semaphore:
            regionalized = await regionalizer.regionalize(event, pool.country_code)
            # 计算评分
            regionalized.neutrality_score = calculate_neutrality_score(
                regionalized.regional_description
            )
            return idx, regionalized

    tasks = [regionalize_one(i, evt) for i, evt in enumerate(pool.events)]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for result in completed:
        if isinstance(result, Exception):
            raise result
        idx, regionalized = result
        results[idx] = regionalized

    # 暴露异常:如有 None,说明有未处理的事件
    if any(r is None for r in results):
        missing = [i for i, r in enumerate(results) if r is None]
        raise RuntimeError(f"Regionalize incomplete, missing indices: {missing}")

    return results  # type: ignore


async def regionalize_multiple_pools(
    regionalizer: Regionalizer,
    pools: list[EventPool],
    semaphore_limit: int = 8,
) -> dict[str, list[RegionalizedEvent]]:
    """地区化多个事件池

    Args:
        regionalizer: 地区化重写器
        pools: 事件池列表(不同地区)
        semaphore_limit: 并发限制

    Returns:
        dict[country_code, list[RegionalizedEvent]]
    """
    semaphore = asyncio.Semaphore(semaphore_limit)
    results: dict[str, list[RegionalizedEvent]] = {}

    async def regionalize_pool_one(pool: EventPool) -> tuple[str, list[RegionalizedEvent]]:
        async with semaphore:
            regionalized_list = await regionalize_pool(regionalizer, pool, semaphore_limit=1)
            return pool.country_code, regionalized_list

    tasks = [regionalize_pool_one(p) for p in pools]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for result in completed:
        if isinstance(result, Exception):
            raise result
        country, regionalized_list = result
        results[country] = regionalized_list

    return results
