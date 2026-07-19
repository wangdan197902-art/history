"""DiskCache 缓存管理 - 基于 diskcache 库

缓存 stage 输出,避免重复调用 Mock API/真实 API
"""
import hashlib
import json
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import diskcache

from src.models.event import (
    AuditedEvent,
    Event,
    EventPool,
    IllustratedEvent,
    PipelineResult,
    RegionalizedEvent,
    TranslatedEvent,
)


# === Pydantic 模型类型映射 ===
MODEL_TYPES = {
    "Event": Event,
    "EventPool": EventPool,
    "RegionalizedEvent": RegionalizedEvent,
    "TranslatedEvent": TranslatedEvent,
    "IllustratedEvent": IllustratedEvent,
    "AuditedEvent": AuditedEvent,
    "PipelineResult": PipelineResult,
}


class DiskCacheManager:
    """DiskCache 缓存管理器

    用法:
        cache = DiskCacheManager(settings.DISKCACHE_DIR)
        cached = cache.get("fetch_07_04_CN")
        if cached is None:
            pool = await fetcher.fetch_events("07", "04")
            cache.set("fetch_07_04_CN", pool, expire=86400)
    """

    def __init__(self, cache_dir: str = ".cache/pipeline"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(str(self.cache_dir))

    def get(self, key: str) -> Any | None:
        """读取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值(已反序列化),未命中返回 None
        """
        raw = self._cache.get(key)
        if raw is None:
            return None
        return self._deserialize(raw)

    def set(self, key: str, value: Any, expire: int = 86400) -> None:
        """写入缓存

        Args:
            key: 缓存键
            value: 缓存值(pydantic 模型 / dict / list)
            expire: 过期时间(秒),默认 1 天
        """
        serialized = self._serialize(value)
        self._cache.set(key, serialized, expire=expire)

    def delete(self, key: str) -> None:
        """删除缓存项"""
        self._cache.delete(key)

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()

    def stats(self) -> dict:
        """获取缓存统计"""
        return {
            "size": len(self._cache),
            "volume_bytes": self._cache.volume(),
            "cache_dir": str(self.cache_dir),
        }

    def cached_key(self, stage: str, **kwargs) -> str:
        """生成稳定的缓存键

        Args:
            stage: 阶段名(fetch/regionalize/translate/illustrate/audit/publish)
            **kwargs: 用于区分缓存的参数

        Returns:
            str: 稳定哈希键,如 "fetch_07_04_CN_a1b2c3d4"
        """
        # 按 key 排序,保证稳定
        sorted_items = sorted(kwargs.items())
        params_str = json.dumps(sorted_items, sort_keys=True, ensure_ascii=False)
        hash_suffix = hashlib.md5(params_str.encode("utf-8")).hexdigest()[:8]
        return f"{stage}_{hash_suffix}"

    def _serialize(self, value: Any) -> dict:
        """序列化为可存储格式"""
        if isinstance(value, (Event, EventPool, RegionalizedEvent, TranslatedEvent,
                              IllustratedEvent, AuditedEvent, PipelineResult)):
            return {
                "__type__": type(value).__name__,
                "__data__": value.model_dump_json(),
            }
        if isinstance(value, list):
            return {
                "__type__": "list",
                "__items__": [self._serialize(v) for v in value],
            }
        if isinstance(value, dict):
            return {
                "__type__": "dict",
                "__items__": {k: self._serialize(v) for k, v in value.items()},
            }
        return {"__type__": "primitive", "__data__": value}

    def _deserialize(self, raw: Any) -> Any:
        """从存储格式反序列化"""
        if not isinstance(raw, dict):
            return raw
        type_name = raw.get("__type__")
        if type_name in MODEL_TYPES:
            model_cls = MODEL_TYPES[type_name]
            return model_cls.model_validate_json(raw["__data__"])
        if type_name == "list":
            return [self._deserialize(v) for v in raw.get("__items__", [])]
        if type_name == "dict":
            return {k: self._deserialize(v) for k, v in raw.get("__items__", {}).items()}
        if type_name == "primitive":
            return raw.get("__data__")
        return raw

    def close(self) -> None:
        """关闭缓存"""
        self._cache.close()


def cached(stage_name: str, cache_manager: DiskCacheManager, expire: int = 86400):
    """装饰器:自动缓存 stage 输出

    Args:
        stage_name: 阶段名
        cache_manager: 缓存管理器实例
        expire: 过期时间(秒)

    用法:
        @cached("fetch", cache_manager)
        async def my_fetch(month, day, country):
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            # 生成缓存键(基于函数名 + 参数)
            key = cache_manager.cached_key(
                stage_name,
                args=str(args),
                kwargs=str(sorted(kwargs.items())),
            )
            cached_value = cache_manager.get(key)
            if cached_value is not None:
                return cached_value
            result = await fn(*args, **kwargs)
            cache_manager.set(key, result, expire=expire)
            return result
        return wrapper
    return decorator
