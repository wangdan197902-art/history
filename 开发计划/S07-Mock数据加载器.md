# S07 - Mock 数据加载器与 fixture 体系

> 阶段：Phase 1 - Mock 体系建设
> 人天：1.5 | 依赖：S03、S06 | 前置：Mock Server 已实现

---

## 一、步骤概述

完善 Mock 数据加载器，建立完整的 fixture 体系：5 日期样本 × 30 地区 × 10 语种 = 1,500 个详细 fixture，覆盖 7 阶段输出（fetch/regionalize/translate/illustrate/audit/publish）。同时编写 fixture 管理脚本和校验工具。

## 二、任务清单

### 2.1 fixture 目录结构

```
tests/fixtures/mock_responses/
├── wikipedia/              # S03 已生成 10,980 个文件
│   ├── 01-01_CN.json
│   ├── 01-01_US.json
│   └── ...
├── anthropic/              # 地区化重写响应
│   ├── 07-04_CN.json       # 7月4日 中国地区化
│   └── ... (5 日期 × 30 地区 = 150 个)
├── openai/                 # 翻译响应
│   ├── 07-04_CN_zh.json    # 中文翻译
│   └── ... (5 日期 × 30 地区 × 10 语种 = 1,500 个)
├── gemini/                 # 配图响应
│   └── ... (150 个)
├── buttondown/
└── gsc/
```

### 2.2 增强 fixture 生成器

文件：`scripts/gen_detailed_fixtures.py`

```python
"""生成 5 日期 × 30 地区 × 10 语种 详细 fixture"""
import json
from pathlib import Path
from src.models.countries import ALL_COUNTRIES, LANGUAGES, COUNTRY_NAMES, LANGUAGE_NAMES

FIXTURE_BASE = Path("tests/fixtures/mock_responses")
SAMPLE_DATES = ["01-01", "02-29", "07-04", "10-01", "12-25"]

def gen_anthropic_fixture(date_str: str, country: str) -> dict:
    """生成 Anthropic Mock 响应"""
    return {
        "content": [{
            "type": "text",
            "text": f"【地区化】{COUNTRY_NAMES[country]} 在 {date_str} 的历史事件重写。"
        }],
        "usage": {"input_tokens": 150, "output_tokens": 300}
    }

def gen_openai_fixture(date_str: str, country: str, lang: str) -> dict:
    """生成 OpenAI Mock 翻译响应"""
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": f"【{LANGUAGE_NAMES[lang]}翻译】{COUNTRY_NAMES[country]} {date_str} 历史事件。"
            }
        }],
        "usage": {"prompt_tokens": 80, "completion_tokens": 150}
    }

def gen_gemini_fixture(date_str: str, country: str) -> dict:
    """生成 Gemini Mock 配图响应"""
    return {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": f"https://mock-cdn.example.com/{country}_{date_str}.webp"
                }]
            }
        }]
    }

def main():
    for d in SAMPLE_DATES:
        for c in ALL_COUNTRIES:
            # Anthropic
            (FIXTURE_BASE / "anthropic" / f"{d}_{c}.json").parent.mkdir(parents=True, exist_ok=True)
            (FIXTURE_BASE / "anthropic" / f"{d}_{c}.json").write_text(
                json.dumps(gen_anthropic_fixture(d, c), ensure_ascii=False, indent=2), encoding="utf-8")

            # OpenAI (10 语种)
            for lang in LANGUAGES:
                (FIXTURE_BASE / "openai" / f"{d}_{c}_{lang}.json").parent.mkdir(parents=True, exist_ok=True)
                (FIXTURE_BASE / "openai" / f"{d}_{c}_{lang}.json").write_text(
                    json.dumps(gen_openai_fixture(d, c, lang), ensure_ascii=False, indent=2), encoding="utf-8")

            # Gemini
            (FIXTURE_BASE / "gemini" / f"{d}_{c}.json").parent.mkdir(parents=True, exist_ok=True)
            (FIXTURE_BASE / "gemini" / f"{d}_{c}.json").write_text(
                json.dumps(gen_gemini_fixture(d, c), ensure_ascii=False, indent=2), encoding="utf-8")

    print("详细 fixture 生成完成")

if __name__ == "__main__":
    main()
```

### 2.3 fixture 校验工具

文件：`scripts/validate_fixtures.py`

```python
"""校验 fixture 完整性"""
import json
from pathlib import Path
from src.models.countries import ALL_COUNTRIES, LANGUAGES

FIXTURE_BASE = Path("tests/fixtures/mock_responses")
SAMPLE_DATES = ["01-01", "02-29", "07-04", "10-01", "12-25"]

def validate():
    errors = []

    # Wikipedia: 366 × 30 = 10,980 个
    wiki_files = list((FIXTURE_BASE / "wikipedia").glob("*.json"))
    if len(wiki_files) != 366 * 30:
        errors.append(f"Wikipedia fixture 数量错误: {len(wiki_files)} (期望 {366*30})")

    # Anthropic: 5 × 30 = 150 个
    anth_files = list((FIXTURE_BASE / "anthropic").glob("*.json"))
    if len(anth_files) != 5 * 30:
        errors.append(f"Anthropic fixture 数量错误: {len(anth_files)} (期望 {5*30})")

    # OpenAI: 5 × 30 × 10 = 1,500 个
    oai_files = list((FIXTURE_BASE / "openai").glob("*.json"))
    if len(oai_files) != 5 * 30 * 10:
        errors.append(f"OpenAI fixture 数量错误: {len(oai_files)} (期望 {5*30*10})")

    # 校验 JSON 合法性
    for f in wiki_files + anth_files + oai_files:
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"JSON 错误 {f}: {e}")

    if errors:
        for e in errors:
            print(f"❌ {e}")
        return 1
    print("✅ 所有 fixture 校验通过")
    return 0

if __name__ == "__main__":
    exit(validate())
```

### 2.4 fixture 加载器增强

文件：`src/mock_server/data_loader.py`（在 S06 基础上增强）

```python
import json
import random
from pathlib import Path
from typing import Any
from functools import lru_cache

FIXTURE_BASE = Path("tests/fixtures/mock_responses")

@lru_cache(maxsize=1024)
def load_fixture(service: str, scenario: str) -> Any:
    """带 LRU 缓存的 fixture 加载"""
    fixture_path = FIXTURE_BASE / service / f"{scenario}.json"
    if not fixture_path.exists():
        # 降级：返回默认 fixture
        return _default_response(service, scenario)
    return json.loads(fixture_path.read_text(encoding="utf-8"))

def _default_response(service: str, scenario: str) -> dict:
    """fixture 不存在时的默认响应"""
    return {
        "wikipedia": {"events": [], "births": [], "deaths": []},
        "anthropic": {"content": [{"type": "text", "text": "Mock 响应"}]},
        "openai": {"choices": [{"message": {"role": "assistant", "content": "Mock 翻译"}}]},
        "gemini": {"candidates": [{"content": {"parts": [{"text": "mock.webp"}]}}]},
    }.get(service, {})
```

## 三、实施步骤

1. 编写 `scripts/gen_detailed_fixtures.py`
2. 运行生成 1,500+ 详细 fixture
3. 编写 `scripts/validate_fixtures.py` 校验工具
4. 运行校验
5. 增强 `data_loader.py`（添加 LRU 缓存 + 降级）
6. 编写 `tests/unit/test_data_loader.py`

## 四、验收命令

```bash
. .venv/bin/activate

# 生成详细 fixture
python scripts/gen_detailed_fixtures.py

# 校验
python scripts/validate_fixtures.py
# 期望 ✅ 所有 fixture 校验通过

# 单元测试
pytest tests/unit/test_data_loader.py -v
```

## 五、依赖关系

- **前置依赖**：S03（基础 fixture）、S06（Mock Server）
- **后续依赖**：S08（Provider 切换器使用 fixture）
- **阻塞关系**：fixture 不完整则 Mock 响应会降级到默认值

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| fixture 体积过大 | 中 | 总 < 500MB，可接受 |
| LRU 缓存与并发冲突 | 低 | Flask 单进程，无冲突 |
| fixture 路径命名不一致 | 中 | 校验工具检查 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| fixture 生成时间 | < 30s | `time python scripts/gen_detailed_fixtures.py` |
| fixture 校验时间 | < 5s | `time python scripts/validate_fixtures.py` |
| LRU 缓存命中率 | > 90% | 日志统计 |

## 八、测试要求

- 1,500+ 详细 fixture 全部生成
- 校验工具通过
- LRU 缓存正常工作
- fixture 不存在时降级响应正确
