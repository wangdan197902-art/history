# S21 - Hugo 10 万页全量构建

> 阶段：Phase 3 - Hugo 集成与 10 万页构建
> 人天：2 | 依赖：S19、S20 | 前置：模板与图片就绪

---

## 一、步骤概述

生成 366 天 × 30 地区 × 10 语种 = 109,800 个 Markdown 文件并全量构建。使用 `--cacheDir` 持久化 + 分批构建（按语种）+ `rsync` 合并，目标 < 10min（16GB Mac）。

## 二、任务清单

### 2.1 批量生成 Markdown 脚本

文件：`scripts/gen_blank_pages.py`

```python
"""生成 366 × 30 × 10 = 109,800 个空白 Markdown 文件（含 frontmatter）"""
import asyncio
from pathlib import Path
from datetime import date, timedelta
from src.config import settings
from src.providers import get_provider
from src.pipeline.orchestrator import run_pipeline
from src.models.countries import ALL_COUNTRIES, LANGUAGES, COUNTRY_NAMES

async def gen_all_pages():
    """生成全年所有页面"""
    # 简化版：直接生成空白 frontmatter 的 Markdown（实际内容由管道填充）
    content_dir = Path("site/content")
    start = date(2024, 1, 1)

    for day_offset in range(366):
        d = start + timedelta(days=day_offset)
        date_str = d.strftime("%m-%d")
        for lang in LANGUAGES:
            for country in ALL_COUNTRIES:
                target_dir = content_dir / lang / country
                target_dir.mkdir(parents=True, exist_ok=True)
                out_file = target_dir / f"{date_str}.md"
                if out_file.exists():
                    continue  # 已存在不覆盖（保留管道生成的内容）
                out_file.write_text(f"""---
title: "{date_str} · {COUNTRY_NAMES.get(country, country)} 今天历史"
date: 2024-{date_str}T00:00:00Z
country_code: "{country}"
country_name: "{COUNTRY_NAMES.get(country, country)}"
language: "{lang}"
draft: false
event_count: 0
---

# {date_str} · {COUNTRY_NAMES.get(country, country)} 今天历史

本日暂无事件数据（待管道生成）。
""", encoding="utf-8")
        if day_offset % 30 == 0:
            print(f"  进度: {day_offset}/366")

    total = sum(1 for _ in content_dir.rglob("*.md"))
    print(f"生成完成: {total} 个 Markdown 文件")

if __name__ == "__main__":
    asyncio.run(gen_all_pages())
```

### 2.2 分批构建脚本

文件：`scripts/hugo_batch_build.sh`

```bash
#!/bin/bash
set -e

# Hugo 分批构建（按语种）
LANGS=("zh" "en" "ja" "ko" "es" "fr" "de" "pt" "ru" "ar")
PUBLIC_DIR="site/public"
CACHE_DIR="$HOME/.cache/hugo-today-in-history"

mkdir -p "$CACHE_DIR"
rm -rf "$PUBLIC_DIR"
mkdir -p "$PUBLIC_DIR"

echo "=== Hugo 分批构建 ==="
echo "缓存目录: $CACHE_DIR"
echo "目标: 109,800 页面 < 10min"

START_TIME=$(date +%s)

for lang in "${LANGS[@]}"; do
    echo ""
    echo "[$(date +%H:%M:%S)] 构建语种: $lang"
    BATCH_DIR="site/public_batch_${lang}"
    rm -rf "$BATCH_DIR"
    mkdir -p "$BATCH_DIR"

    # 限制内存 2GB
    ulimit -v 2097152 2>/dev/null || true

    # Hugo 构建单语种
    cd site
    hugo --quiet \
         --cacheDir "$CACHE_DIR" \
         --destination "../$BATCH_DIR" \
         --renderSegments "content/$lang"
    cd ..

    # 合并到 public
    rsync -a "$BATCH_DIR/" "$PUBLIC_DIR/"
    rm -rf "$BATCH_DIR"
    echo "  ✅ $lang 完成"
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# 统计
PAGE_COUNT=$(find "$PUBLIC_DIR" -name "*.html" | wc -l)
TOTAL_SIZE=$(du -sh "$PUBLIC_DIR" | cut -f1)

echo ""
echo "=== 构建完成 ==="
echo "总耗时: ${DURATION}s"
echo "HTML 页面数: $PAGE_COUNT"
echo "总体积: $TOTAL_SIZE"

# 性能预算检查
if [ $DURATION -gt 600 ]; then
    echo "⚠️  超时: ${DURATION}s > 600s 预算"
    exit 1
fi
if [ $PAGE_COUNT -lt 100000 ]; then
    echo "⚠️  页面数不足: $PAGE_COUNT < 100000"
    exit 1
fi
echo "✅ 性能预算达标"
```

### 2.3 单次构建脚本（16GB+ Mac 用）

文件：`scripts/hugo_build.sh`

```bash
#!/bin/bash
set -e

CACHE_DIR="$HOME/.cache/hugo-today-in-history"
mkdir -p "$CACHE_DIR"

echo "=== Hugo 单次构建 ==="
START_TIME=$(date +%s)

cd site
hugo --quiet \
     --cacheDir "$CACHE_DIR" \
     --minify \
     --gc
cd ..

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

PAGE_COUNT=$(find site/public -name "*.html" | wc -l)
TOTAL_SIZE=$(du -sh site/public | cut -f1)
PEAK_MEM=$(ps -o rss= -p $$ | awk '{print $1/1024 " MB"}')

echo "=== 构建完成 ==="
echo "总耗时: ${DURATION}s"
echo "HTML 页面数: $PAGE_COUNT"
echo "总体积: $TOTAL_SIZE"
echo "峰值内存: $PEAK_MEM"

# 性能预算检查
if [ $DURATION -gt 600 ]; then
    echo "⚠️  超时: ${DURATION}s > 600s 预算"
    exit 1
fi
echo "✅ 性能预算达标"
```

### 2.4 性能基准测试

文件：`scripts/perf_bench_build.py`

```python
"""Hugo 构建性能基准测试"""
import subprocess
import json
import time
import statistics
from pathlib import Path

def run_build():
    """运行单次构建"""
    start = time.perf_counter()
    result = subprocess.run(
        ["bash", "scripts/hugo_build.sh"],
        capture_output=True,
        text=True
    )
    duration = time.perf_counter() - start
    return {
        "duration_sec": duration,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

def main():
    """运行 3 轮取中位数"""
    results = []
    for i in range(3):
        print(f"第 {i+1}/3 轮构建...")
        r = run_build()
        results.append(r)
        print(f"  耗时: {r['duration_sec']:.1f}s")

    durations = [r["duration_sec"] for r in results]
    report = {
        "runs": results,
        "median_duration_sec": statistics.median(durations),
        "min_duration_sec": min(durations),
        "max_duration_sec": max(durations),
        "passes_budget": statistics.median(durations) < 600,
    }
    Path("09_报告").mkdir(parents=True, exist_ok=True)
    Path("09_报告/hugo_build_bench.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n中位数: {report['median_duration_sec']:.1f}s")
    print(f"预算达标: {'是' if report['passes_budget'] else '否'}")

if __name__ == "__main__":
    main()
```

### 2.5 构建产物分析

文件：`scripts/analyze_public.py`

```python
"""分析构建产物"""
import json
from pathlib import Path
from collections import Counter

def main():
    public = Path("site/public")
    html_files = list(public.rglob("*.html"))
    webp_files = list(public.rglob("*.webp"))

    # HTML 体积分布
    html_sizes = [f.stat().st_size for f in html_files]
    html_p50 = sorted(html_sizes)[len(html_sizes)//2]
    html_p90 = sorted(html_sizes)[int(len(html_sizes)*0.9)]
    html_p99 = sorted(html_sizes)[int(len(html_sizes)*0.99)]

    # 单页 HTML 体积
    oversized = [f for f, s in zip(html_files, html_sizes) if s > 50 * 1024]

    report = {
        "total_html": len(html_files),
        "total_webp": len(webp_files),
        "html_size_p50_kb": round(html_p50 / 1024, 1),
        "html_size_p90_kb": round(html_p90 / 1024, 1),
        "html_size_p99_kb": round(html_p99 / 1024, 1),
        "oversized_html_count": len(oversized),
        "oversaged_examples": [str(f) for f in oversized[:5]],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    Path("09_报告").mkdir(parents=True, exist_ok=True)
    Path("09_报告/public_analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
```

## 三、实施步骤

1. 编写 `scripts/gen_blank_pages.py` 生成 109,800 个 Markdown
2. 运行生成脚本（约 5min）
3. 编写 `scripts/hugo_build.sh` 单次构建
4. 编写 `scripts/hugo_batch_build.sh` 分批构建
5. 评估硬件（S01 评估结果）选择构建策略
6. 运行构建，记录耗时
7. 编写 `scripts/perf_bench_build.py` 基准测试
8. 编写 `scripts/analyze_public.py` 产物分析
9. 运行基准测试 + 产物分析

## 四、验收命令

```bash
. .venv/bin/activate

# 1. 生成 Markdown
time python scripts/gen_blank_pages.py
# 期望: 109,800 个 .md 文件，< 5min

# 2. 根据硬件选择构建方式
# 16GB+ Mac: 单次构建
time bash scripts/hugo_build.sh
# 8GB Mac: 分批构建
time bash scripts/hugo_batch_build.sh

# 期望:
# - 总耗时 < 10min (16GB)
# - HTML 页面数 ≥ 100,000
# - 峰值内存 < 4GB

# 3. 基准测试
python scripts/perf_bench_build.py

# 4. 产物分析
python scripts/analyze_public.py
# 期望:
# - 单页 HTML 体积 P50 < 50KB
# - 超大页面数 < 100
```

## 五、依赖关系

- 前置：S19、S20
- 后续：S22（Pagefind 索引）、S23（预览）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| 8GB Mac OOM | 高 | 分批构建 + ulimit |
| 构建超时 | 中 | --cacheDir 持久化 |
| 单页体积超限 | 低 | minify + gc |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| Hugo 10 万页构建 | < 10min (16GB) | `time` |
| HTML 页面数 | ≥ 100,000 | `find \| wc -l` |
| 构建峰值内存 | < 4GB | `ps` |
| 单页 HTML P50 | < 50 KB | `analyze_public.py` |
| 总体积 | < 2GB | `du -sh` |

## 八、测试要求

- 109,800 个 HTML 页面生成
- 构建耗时 < 10min
- 峰值内存 < 4GB
- 单页 HTML P50 < 50KB
- 总体积 < 2GB
