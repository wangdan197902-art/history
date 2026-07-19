"""asyncio 管道编排器

串联 6 阶段: fetch → regionalize → translate → illustrate → audit → publish

支持模式:
  - slice: 垂直切片(5 个样本日期 × 1 地区 × 1 语种)
  - sample: 单日单地区
  - full: 全年全地区(批量)

入口: python -m src.pipeline.orchestrator --mode=slice --country=CN --language=zh
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.base import get_settings
from src.models.event import (
    AuditedEvent,
    EventPool,
    IllustratedEvent,
    PipelineResult,
    RegionalizedEvent,
    TranslatedEvent,
)
from src.models.countries import ALL_COUNTRIES, LANGUAGES
from src.pipeline.cache import DiskCacheManager
from src.pipeline.retry import retry_async
from src.providers.factory import (
    get_auditor,
    get_illustrator,
    get_publisher,
    get_regionalizer,
    get_translator,
    get_wikipedia_fetcher,
)


# 默认垂直切片样本日期(覆盖闰年/节假日)
DEFAULT_SAMPLE_DATES = ["01-01", "02-29", "07-04", "10-01", "12-25"]


class PipelineOrchestrator:
    """管道编排器

    协调 6 个 Provider 完成 fetch→regionalize→translate→illustrate→audit→publish
    """

    def __init__(self, settings: Any = None, use_cache: bool = True):
        self.settings = settings or get_settings()
        self.use_cache = use_cache
        self.cache = DiskCacheManager(self.settings.DISKCACHE_DIR) if use_cache else None

        # 实例化 6 个 provider
        self.fetcher = get_wikipedia_fetcher(self.settings)
        self.regionalizer = get_regionalizer(self.settings)
        self.translator = get_translator(self.settings)
        self.illustrator = get_illustrator(self.settings)
        self.auditor = get_auditor(self.settings)
        self.publisher = get_publisher(self.settings)

    async def run_one(
        self,
        month: str,
        day: str,
        country_code: str,
        languages: list[str] | None = None,
        output_dir: str = "site/content",
    ) -> PipelineResult:
        """单日单地区完整管道

        Args:
            month: 月份(01-12)
            day: 日期(01-31)
            country_code: 地区代码
            languages: 目标语种(默认所有 10 种)
            output_dir: Hugo 内容输出目录

        Returns:
            PipelineResult: 完整管道结果
        """
        if languages is None:
            languages = self.settings.languages_list

        start_time = time.time()
        date_str = f"2024-{month}-{day}"
        result = PipelineResult(date=date_str, country_code=country_code)

        try:
            # === Stage 1: Fetch ===
            cache_key_fetch = self._cache_key("fetch", month=month, day=day, country=country_code)
            event_pool = self._get_cached(cache_key_fetch)
            if event_pool is None:
                event_pool = await retry_async(
                    self.fetcher.fetch_events, month, day, "all",
                    max_retries=2, base_delay=0.5,
                )
                # 设置 country_code(Wikipedia API 返回的是全球事件)
                event_pool.country_code = country_code
                self._set_cached(cache_key_fetch, event_pool)
            result.event_pool = event_pool

            if not event_pool.events:
                result.success = True
                result.error = "no events fetched"
                result.duration_seconds = round(time.time() - start_time, 3)
                return result

            # === Stage 2: Regionalize ===
            cache_key_reg = self._cache_key("regionalize", date=date_str, country=country_code)
            regionalized_list = self._get_cached(cache_key_reg)
            if regionalized_list is None:
                regionalized_list = await retry_async(
                    self._regionalize_pool_safe, event_pool,
                    max_retries=2, base_delay=0.5,
                )
                self._set_cached(cache_key_reg, regionalized_list)
            result.regionalized = regionalized_list

            # === Stage 3: Translate (每事件×N语种) ===
            for regionalized in regionalized_list:
                cache_key_tr = self._cache_key(
                    "translate",
                    event_id=regionalized.original.id,
                    country=country_code,
                )
                translations = self._get_cached(cache_key_tr)
                if translations is None:
                    translations = []
                    for lang in languages:
                        translated = await retry_async(
                            self.translator.translate, regionalized, lang,
                            max_retries=2, base_delay=0.5,
                        )
                        translations.append(translated)
                    self._set_cached(cache_key_tr, translations)
                result.translated[regionalized.original.id] = translations

            # === Stage 4: Illustrate (每翻译事件一个配图) ===
            for event_id, translations in result.translated.items():
                illustrated_list = []
                for translated in translations:
                    cache_key_il = self._cache_key(
                        "illustrate", event_id=event_id, lang=translated.lang,
                    )
                    illustrated = self._get_cached(cache_key_il)
                    if illustrated is None:
                        illustrated = await retry_async(
                            self.illustrator.illustrate, translated,
                            max_retries=2, base_delay=0.5,
                        )
                        self._set_cached(cache_key_il, illustrated)
                    illustrated_list.append(illustrated)
                result.illustrated[event_id] = illustrated_list

            # === Stage 5: Audit ===
            for event_id, illustrated_list in result.illustrated.items():
                audited_list = []
                for illustrated in illustrated_list:
                    cache_key_au = self._cache_key(
                        "audit", event_id=event_id, lang=illustrated.translated.lang,
                    )
                    audited = self._get_cached(cache_key_au)
                    if audited is None:
                        audited = await self.auditor.audit(illustrated)
                        self._set_cached(cache_key_au, audited)
                    audited_list.append(audited)
                result.audited[event_id] = audited_list

            # === Stage 6: Publish (按 lang+country 分组) ===
            all_audited = []
            for audited_list in result.audited.values():
                all_audited.extend(audited_list)

            # 使用 stage_publish 的 publish_markdown 按 (lang, country) 分目录
            from src.pipeline.stage_publish import publish_markdown as _publish_markdown
            published = await _publish_markdown(
                self.publisher, all_audited, output_dir=output_dir,
            )
            result.published_pages = published

            result.success = True
            result.duration_seconds = round(time.time() - start_time, 3)

        except Exception as e:
            result.success = False
            result.error = f"{type(e).__name__}: {e}"
            result.duration_seconds = round(time.time() - start_time, 3)
            # 暴露异常,但记录到 result 中
            raise

        return result

    async def run_day(
        self,
        month: str,
        day: str,
        countries: list[str] | None = None,
        languages: list[str] | None = None,
        semaphore_limit: int = 5,
    ) -> dict[str, PipelineResult]:
        """单日多地区管道

        Args:
            month: 月份
            day: 日期
            countries: 地区列表(默认全部 30)
            languages: 语种列表
            semaphore_limit: 并发限制(默认 5,避免 Mock Server 压力)

        Returns:
            dict[country_code, PipelineResult]
        """
        if countries is None:
            countries = self.settings.countries_list

        semaphore = asyncio.Semaphore(semaphore_limit)
        results: dict[str, PipelineResult] = {}

        async def run_one_with_sem(country: str) -> tuple[str, PipelineResult]:
            async with semaphore:
                try:
                    r = await self.run_one(month, day, country, languages)
                    return country, r
                except Exception as e:
                    # 单地区失败不影响其他地区,但记录失败
                    failed_result = PipelineResult(
                        date=f"2024-{month}-{day}",
                        country_code=country,
                        success=False,
                        error=f"{type(e).__name__}: {e}",
                    )
                    return country, failed_result

        tasks = [run_one_with_sem(c) for c in countries]
        completed = await asyncio.gather(*tasks)
        for country, r in completed:
            results[country] = r

        return results

    async def run_vertical_slice(
        self,
        country_code: str = "CN",
        language: str = "zh",
        sample_dates: list[str] | None = None,
    ) -> dict[str, PipelineResult]:
        """垂直切片 - 5 个样本日期 × 1 地区 × 1 语种

        用于 Phase 2.5 切片验证和 Phase 3 Hugo 集成测试
        """
        if sample_dates is None:
            sample_dates = DEFAULT_SAMPLE_DATES

        results: dict[str, PipelineResult] = {}
        for date_str in sample_dates:
            month, day = date_str.split("-")
            try:
                r = await self.run_one(month, day, country_code, [language])
                results[date_str] = r
            except Exception as e:
                results[date_str] = PipelineResult(
                    date=f"2024-{date_str}",
                    country_code=country_code,
                    success=False,
                    error=f"{type(e).__name__}: {e}",
                )
        return results

    async def run_full_year(
        self,
        year: int = 2024,
        countries: list[str] | None = None,
        batch_size: int = 30,
    ) -> dict[str, dict[str, PipelineResult]]:
        """全年全地区管道(分批执行)

        Args:
            year: 年份(必须为闰年,默认 2024)
            countries: 地区列表
            batch_size: 每批日期数(避免内存爆炸)

        Returns:
            dict[country_code, dict[date_str, PipelineResult]]
        """
        if countries is None:
            countries = self.settings.countries_list

        from datetime import date, timedelta
        try:
            datetime.strptime(f"{year}-02-29", "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Year {year} is not a leap year, use 2024") from e

        # 生成 366 天的 (month, day) 列表
        all_dates = []
        start = date(year, 1, 1)
        for i in range(366):
            d = start + timedelta(days=i)
            all_dates.append((d.strftime("%m"), d.strftime("%d")))

        results: dict[str, dict[str, PipelineResult]] = {c: {} for c in countries}

        # 分批执行
        for batch_start in range(0, len(all_dates), batch_size):
            batch = all_dates[batch_start:batch_start + batch_size]
            for month, day in batch:
                date_str = f"{month}-{day}"
                day_results = await self.run_day(month, day, countries)
                for country, r in day_results.items():
                    results[country][date_str] = r

        return results

    async def _regionalize_pool_safe(self, pool: EventPool) -> list[RegionalizedEvent]:
        """安全地区化(逐事件,单个失败不影响整体)"""
        results: list[RegionalizedEvent | None] = [None] * len(pool.events)
        for idx, event in enumerate(pool.events):
            try:
                regionalized = await self.regionalizer.regionalize(event, pool.country_code)
                results[idx] = regionalized
            except Exception as e:
                # 单个事件地区化失败,记录但继续
                print(f"⚠️ Regionalize failed for {event.id}: {e}", file=sys.stderr)
                # 用原始事件作为降级
                results[idx] = RegionalizedEvent(
                    original=event,
                    country_code=pool.country_code,
                    regional_title=event.title,
                    regional_description=event.description,
                    neutrality_score=0.5,
                    regional_tags=["fallback"],
                    rewrite_log=f"Fallback due to error: {e}",
                )

        # 暴露异常:如果有 None
        if any(r is None for r in results):
            raise RuntimeError("Regionalize produced None results")
        return results  # type: ignore[return-value]

    def _cache_key(self, stage: str, **kwargs) -> str | None:
        if not self.use_cache:
            return None
        return self.cache.cached_key(stage, **kwargs)

    def _get_cached(self, key: str | None) -> Any:
        if not self.use_cache or key is None:
            return None
        return self.cache.get(key)

    def _set_cached(self, key: str | None, value: Any) -> None:
        if not self.use_cache or key is None:
            return
        self.cache.set(key, value)

    async def close(self) -> None:
        """关闭所有资源"""
        for provider in [self.fetcher, self.regionalizer, self.translator,
                         self.illustrator, self.auditor, self.publisher]:
            close_fn = getattr(provider, "close", None)
            if close_fn:
                try:
                    await close_fn()
                except Exception as e:
                    print(f"⚠️ Close provider failed: {e}", file=sys.stderr)
        if self.cache:
            self.cache.close()

    def print_stats(self, results: dict[str, PipelineResult]) -> None:
        """打印统计信息"""
        total = len(results)
        success = sum(1 for r in results.values() if r.success)
        failed = total - success
        total_events = sum(
            len(r.event_pool.events) for r in results.values() if r.event_pool
        )
        total_published = sum(len(r.published_pages) for r in results.values())
        total_duration = sum(r.duration_seconds for r in results.values())

        # 审核通过率
        total_audited = 0
        total_passed = 0
        for r in results.values():
            for audited_list in r.audited.values():
                total_audited += len(audited_list)
                total_passed += sum(1 for a in audited_list if a.audit_pass)

        pass_rate = (total_passed / total_audited * 100) if total_audited > 0 else 0

        print("\n" + "=" * 60)
        print("📊 管道执行统计")
        print("=" * 60)
        print(f"总任务数:       {total}")
        print(f"成功数:         {success} ✅")
        print(f"失败数:         {failed} {'❌' if failed else ''}")
        print(f"总事件数:       {total_events}")
        print(f"审核总数:       {total_audited}")
        print(f"审核通过:       {total_passed} ({pass_rate:.1f}%)")
        print(f"发布文件数:     {total_published}")
        print(f"总耗时:         {total_duration:.2f}s")
        if self.use_cache:
            stats = self.cache.stats()
            print(f"缓存条目:       {stats['size']}")
            print(f"缓存体积:       {stats['volume_bytes'] / 1024:.1f} KB")
        print("=" * 60 + "\n")


async def _main():
    parser = argparse.ArgumentParser(description="地区化今天历史档案站 - 管道编排器")
    parser.add_argument(
        "--mode",
        choices=["slice", "sample", "full", "day"],
        default="slice",
        help="执行模式: slice=垂直切片, sample=单日单地区, full=全年, day=单日多地区",
    )
    parser.add_argument("--country", default="CN", help="地区代码(默认 CN)")
    parser.add_argument("--language", default="zh", help="语种(默认 zh)")
    parser.add_argument("--month", default="07", help="月份(sample/day 模式)")
    parser.add_argument("--day", default="04", help="日期(sample/day 模式)")
    parser.add_argument("--year", type=int, default=2024, help="年份(full 模式,必须闰年)")
    parser.add_argument("--no-cache", action="store_true", help="禁用缓存")
    parser.add_argument("--output-dir", default="site/content", help="Hugo 内容输出目录")

    args = parser.parse_args()

    print(f"🚀 启动管道编排器 [mode={args.mode}, country={args.country}, lang={args.language}]")
    print(f"   ENV={getattr(get_settings(), 'ENV', 'local')}, cache={'OFF' if args.no_cache else 'ON'}")

    orchestrator = PipelineOrchestrator(use_cache=not args.no_cache)

    try:
        if args.mode == "slice":
            results = await orchestrator.run_vertical_slice(
                country_code=args.country,
                language=args.language,
            )
        elif args.mode == "sample":
            r = await orchestrator.run_one(
                args.month, args.day, args.country, [args.language],
                output_dir=args.output_dir,
            )
            results = {f"{args.month}-{args.day}": r}
        elif args.mode == "day":
            results = await orchestrator.run_day(
                args.month, args.day, [args.country], [args.language],
            )
        elif args.mode == "full":
            print("⚠️ full 模式将处理 366×30=10980 个组合,可能耗时较长")
            results_flat = await orchestrator.run_full_year(args.year, [args.country])
            # 展平为 date -> result
            results = results_flat.get(args.country, {})
        else:
            print(f"❌ 未知模式: {args.mode}")
            sys.exit(1)

        orchestrator.print_stats(results)

        # 打印失败的
        failures = {k: v for k, v in results.items() if not v.success}
        if failures:
            print(f"\n⚠️ {len(failures)} 个任务失败:")
            for k, r in failures.items():
                print(f"  - {k}: {r.error}")
    finally:
        await orchestrator.close()


def main():
    """同步入口(供 python -m 调用)"""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
