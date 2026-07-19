#!/usr/bin/env python3
"""
Mac 硬件评估脚本 — 决定 Hugo 构建策略和 asyncio 并发度

输出 JSON:
{
  "memory_gb": 16.0,
  "cpu_count": 8,
  "hugo_strategy": "batch",
  "asyncio_concurrency": 16,
  "macos_version": "14.5.0",
  "recommended": "可执行分批构建,asyncio 并发 16"
}
"""
import json
import platform
import sys


def check_hardware():
    try:
        import psutil
    except ImportError:
        print("ERROR: psutil 未安装,请先运行 'pip install psutil'", file=sys.stderr)
        sys.exit(1)

    mem = psutil.virtual_memory()
    mem_gb = mem.total / (1024**3)
    cpu_count = psutil.cpu_count(logical=True)

    # Hugo 构建策略评估
    if mem_gb >= 32:
        strategy = "full"
        concurrency = 32
        recommended = "可全量构建,asyncio 并发 32"
    elif mem_gb >= 16:
        strategy = "batch"
        concurrency = 16
        recommended = "推荐分批构建(按语种),asyncio 并发 16"
    elif mem_gb >= 8:
        strategy = "batch_conservative"
        concurrency = 8
        recommended = "保守分批构建,asyncio 并发 8(注意 OOM 风险)"
    else:
        strategy = "minimal"
        concurrency = 4
        recommended = "内存不足,仅能跑切片验证,无法全量构建"

    return {
        "memory_gb": round(mem_gb, 1),
        "memory_available_gb": round(mem.available / (1024**3), 1),
        "cpu_count": cpu_count,
        "hugo_strategy": strategy,
        "asyncio_concurrency": concurrency,
        "macos_version": platform.mac_ver()[0],
        "python_version": sys.version.split()[0],
        "recommended": recommended,
    }


def main():
    result = check_hardware()
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 输出建议到 tech-debt-ledger
    print("\n--- 建议记录到 tech-debt-ledger.md ---")
    print(f"- Hugo 构建策略: {result['hugo_strategy']}")
    print(f"- asyncio 并发度: {result['asyncio_concurrency']}")
    print(f"- 内存: {result['memory_gb']} GB")
    print(f"- CPU: {result['cpu_count']} 核")


if __name__ == "__main__":
    main()
