"""异步重试工具 - 基于 tenacity 的指数退避

用于包装 Provider 调用,在网络抖动或 Mock 故障注入下自动重试
"""
import asyncio
from functools import wraps
from typing import Any, Callable, Tuple, Type

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
):
    """异步重试装饰器(指数退避)

    Args:
        max_retries: 最大重试次数(总尝试 = max_retries + 1)
        base_delay: 基础延迟(秒),实际延迟 = base_delay * 2^attempt
        max_delay: 最大延迟(秒)
        exceptions: 触发重试的异常类型

    Returns:
        装饰器函数

    用法:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        async def fetch_data():
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_retries + 1),
                wait=wait_exponential(multiplier=base_delay, max=max_delay),
                retry=retry_if_exception_type(exceptions),
                reraise=True,
            ):
                with attempt:
                    try:
                        return await fn(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        raise
            # 理论不可达(reraise=True),保险兜底
            if last_exception:
                raise last_exception
            raise RuntimeError("retry_with_backoff: unreachable")
        return wrapper
    return decorator


async def retry_async(
    coro_fn: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    **kwargs,
) -> Any:
    """函数式重试调用

    Args:
        coro_fn: 异步函数
        *args: 位置参数
        max_retries: 最大重试次数
        base_delay: 基础延迟
        exceptions: 触发重试的异常类型
        **kwargs: 关键字参数

    Returns:
        函数返回值

    Raises:
        Exception: 重试 max_retries 次后仍失败
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_fn(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
    raise last_exception  # type: ignore[misc]
