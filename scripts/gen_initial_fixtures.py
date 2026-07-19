#!/usr/bin/env python3
"""生成 Anthropic/OpenAI/Gemini 初始 fixture

为 5 个测试日期 × 30 地区 × 10 语种 生成详细 fixture
共 5 × 30 = 150 个 anthropic fixture
共 5 × 30 × 10 = 1500 个 openai fixture
共 5 × 30 = 150 个 gemini fixture
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.countries import ALL_COUNTRIES, COUNTRY_NAMES, LANGUAGES

FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "mock_responses"

# 5 个测试日期(覆盖闰年/节假日)
SAMPLE_DATES = ["01-01", "02-29", "07-04", "10-01", "12-25"]


def gen_anthropic_fixture(country: str, date_str: str) -> dict:
    """生成 Anthropic Mock 响应"""
    return {
        "id": f"msg_mock_{country}_{date_str}",
        "type": "message",
        "role": "assistant",
        "model": "claude-3-5-sonnet-20241022",
        "content": [
            {
                "type": "text",
                "text": f"[Mock 地区化] {COUNTRY_NAMES.get(country, country)} 在 {date_str} 的历史事件地区化重写版本。保持了中立性,突出了与{country}的关联。",
            }
        ],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 80, "output_tokens": 120},
    }


def gen_openai_fixture(country: str, date_str: str, lang: str) -> dict:
    """生成 OpenAI Mock 翻译响应"""
    lang_names = {
        "zh": "中文", "en": "English", "ja": "日本語", "ko": "한국어",
        "es": "Español", "fr": "Français", "de": "Deutsch", "pt": "Português",
        "ru": "Русский", "ar": "العربية",
    }
    return {
        "id": f"chatcmpl-mock_{country}_{date_str}_{lang}",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"[Mock {lang_names.get(lang, lang)}] {country} {date_str} 历史事件翻译({lang_names.get(lang, lang)})。",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 80, "completion_tokens": 50, "total_tokens": 130},
    }


def gen_gemini_fixture(scenario: str) -> dict:
    """生成 Gemini Mock 响应"""
    if scenario == "illustrate":
        text = json.dumps({
            "image_url": "https://mock.example.com/history_event.jpg",
            "image_alt": "历史事件示意图",
            "image_caption": "Mock 配图:历史事件场景",
            "search_keywords": ["history", "event", "mock"],
        }, ensure_ascii=False)
    elif scenario == "audit":
        text = json.dumps({
            "audit_pass": True,
            "compliance_score": 0.9,
            "issues": [],
            "notes": "Mock 审核:内容合规",
        }, ensure_ascii=False)
    else:
        text = '{"mock": true}'

    return {
        "candidates": [
            {
                "content": {"parts": [{"text": text}]},
                "finishReason": "STOP",
                "index": 0,
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 50,
            "candidatesTokenCount": 80,
            "totalTokenCount": 130,
        },
    }


def main():
    # Anthropic fixtures: 5 日期 × 30 地区 = 150 个
    anth_dir = FIXTURE_DIR / "anthropic"
    anth_dir.mkdir(parents=True, exist_ok=True)
    for country in ALL_COUNTRIES:
        for date_str in SAMPLE_DATES:
            fixture = gen_anthropic_fixture(country, date_str)
            (anth_dir / f"regionalize_{country}.json").write_text(
                json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    # OpenAI fixtures: 5 日期 × 30 地区 × 10 语种 = 1500 个
    oai_dir = FIXTURE_DIR / "openai"
    oai_dir.mkdir(parents=True, exist_ok=True)
    for country in ALL_COUNTRIES:
        for lang in LANGUAGES:
            fixture = gen_openai_fixture(country, "07-04", lang)
            (oai_dir / f"translate_{lang}.json").write_text(
                json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    # Gemini fixtures: 2 场景
    gem_dir = FIXTURE_DIR / "gemini"
    gem_dir.mkdir(parents=True, exist_ok=True)
    for scenario in ["illustrate", "audit"]:
        fixture = gen_gemini_fixture(scenario)
        (gem_dir / f"{scenario}.json").write_text(
            json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # 统计
    print(f"Anthropic fixtures: {len(list(anth_dir.glob('*.json')))} 个")
    print(f"OpenAI fixtures: {len(list(oai_dir.glob('*.json')))} 个")
    print(f"Gemini fixtures: {len(list(gem_dir.glob('*.json')))} 个")


if __name__ == "__main__":
    main()
