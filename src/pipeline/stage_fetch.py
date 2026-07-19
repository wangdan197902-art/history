"""Stage 1: Fetch — 抓取历史事件

从 Wikipedia API(或 Mock)抓取某月某日的事件池
"""
import asyncio
from datetime import datetime, timezone
from typing import Any

from src.models.event import Event, EventPool
from src.models.countries import ALL_COUNTRIES
from src.providers.base import WikipediaFetcher


async def fetch_events(
    fetcher: WikipediaFetcher,
    month: str,
    day: str,
    country_code: str = "CN",
    event_type: str = "all",
) -> EventPool:
    """抓取单日单地区事件

    Args:
        fetcher: Wikipedia 抓取器实例
        month: 月份(01-12)
        day: 日期(01-31)
        country_code: 地区代码(默认 CN)
        event_type: 事件类型(all/selected/births/deaths/holidays/events)

    Returns:
        EventPool: 事件池

    Raises:
        ValueError: 日期格式错误
        httpx.HTTPError: 网络请求失败
    """
    # 校验日期
    try:
        datetime.strptime(f"2024-{month}-{day}", "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Invalid date: month={month}, day={day}") from e

    # 调用 fetcher
    pool = await fetcher.fetch_events(month, day, event_type)

    # 覆盖 country_code(因为 Wikipedia API 是全球事件,需指定地区视角)
    pool.country_code = country_code

    return pool


async def fetch_year(
    fetcher: WikipediaFetcher,
    year: int = 2024,
    countries: list[str] | None = None,
    semaphore_limit: int = 16,
) -> dict[str, list[EventPool]]:
    """抓取全年事件(366天 × 30地区)

    Args:
        fetcher: Wikipedia 抓取器
        year: 年份(必须为闰年,如 2024)
        countries: 地区列表(默认全部 30)
        semaphore_limit: 并发限制

    Returns:
        dict[country_code, list[EventPool]] — 每地区 366 个 EventPool
    """
    if countries is None:
        countries = ALL_COUNTRIES

    # 验证闰年
    try:
        datetime.strptime(f"{year}-02-29", "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Year {year} is not a leap year, use 2024")

    # 生成 366 天的 (month, day) 列表
    from datetime import date, timedelta
    dates = []
    start = date(year, 1, 1)
    for i in range(366):
        d = start + timedelta(days=i)
        dates.append((d.strftime("%m"), d.strftime("%d")))

    semaphore = asyncio.Semaphore(semaphore_limit)
    results: dict[str, list[EventPool]] = {c: [] for c in countries}

    async def fetch_one(country: str, month: str, day: str) -> tuple[str, EventPool]:
        async with semaphore:
            pool = await fetch_events(fetcher, month, day, country)
            return country, pool

    # 并发抓取
    tasks = []
    for country in countries:
        for month, day in dates:
            tasks.append(fetch_one(country, month, day))

    completed = await asyncio.gather(*tasks, return_exceptions=True)

    # 整理结果
    for result in completed:
        if isinstance(result, Exception):
            # 暴露异常,不静默吞掉
            raise result
        country, pool = result
        results[country].append(pool)

    return results


async def fetch_date_range(
    fetcher: WikipediaFetcher,
    start_date: str,
    end_date: str,
    countries: list[str] | None = None,
    semaphore_limit: int = 16,
) -> dict[str, list[EventPool]]:
    """抓取指定日期范围的事件

    Args:
        fetcher: Wikipedia 抓取器
        start_date: 起始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD
        countries: 地区列表
        semaphore_limit: 并发限制

    Returns:
        dict[country_code, list[EventPool]]
    """
    if countries is None:
        countries = ALL_COUNTRIES

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    if start > end:
        raise ValueError(f"start_date {start_date} > end_date {end_date}")

    from datetime import timedelta
    dates = []
    current = start
    while current <= end:
        dates.append((current.strftime("%m"), current.strftime("%d")))
        current += timedelta(days=1)

    semaphore = asyncio.Semaphore(semaphore_limit)
    results: dict[str, list[EventPool]] = {c: [] for c in countries}

    async def fetch_one(country: str, month: str, day: str) -> tuple[str, EventPool]:
        async with semaphore:
            pool = await fetch_events(fetcher, month, day, country)
            return country, pool

    tasks = [fetch_one(c, m, d) for c in countries for m, d in dates]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for result in completed:
        if isinstance(result, Exception):
            raise result
        country, pool = result
        results[country].append(pool)

    return results
