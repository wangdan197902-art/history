"""内容生产管道包

7 阶段:
    fetch → regionalize → translate → illustrate → audit → publish → build

每个阶段独立可测试,通过 orchestrator 串联
"""
from src.pipeline.stage_fetch import fetch_events, fetch_year
from src.pipeline.stage_regionalize import regionalize_pool
from src.pipeline.stage_translate import translate_to_all_langs
from src.pipeline.stage_illustrate import illustrate_translated
from src.pipeline.stage_audit import audit_illustrated
from src.pipeline.stage_publish import publish_markdown
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.cache import DiskCacheManager, cached
from src.pipeline.retry import retry_with_backoff, retry_async

__all__ = [
    "fetch_events", "fetch_year",
    "regionalize_pool",
    "translate_to_all_langs",
    "illustrate_translated",
    "audit_illustrated",
    "publish_markdown",
    "PipelineOrchestrator",
    "DiskCacheManager", "cached",
    "retry_with_backoff", "retry_async",
]
