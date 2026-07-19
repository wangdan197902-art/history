#!/usr/bin/env python3
"""
高效生成全量 Hugo 内容: 30地区 × 366天 × 20语种 = 219,600 个 Markdown 文件

直接从 Wikipedia fixture 读取事件池,使用模板翻译生成多语种内容,
跳过 HTTP 调用和管道编排,大幅提升生成速度。

用法:
    python scripts/generate_full_site.py [--output-dir=site/content] [--limit-days=0]

参数:
    --output-dir: Hugo content 输出目录(默认 site/content)
    --limit-days: 限制天数(0=全部366天,用于快速测试)
    --countries: 限制地区(逗号分隔,空=全部30)
    --languages: 限制语种(逗号分隔,空=全部20)
"""
import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.countries import (
    ALL_COUNTRIES,
    COUNTRY_NAMES,
    COUNTRY_NAMES_EN,
    LANGUAGES,
    LANGUAGE_NAMES,
    LANGUAGE_DIRECTIONS,
)


# === 多语种翻译模板 ===
# 每个语种提供"今天历史"标题翻译 + 简单的本地化前缀
LANG_TITLE_TEMPLATES = {
    "zh": ("{country}今天历史", "今日 {country} 重要历史事件"),
    "en": ("Today in {country} History", "Important historical events of today in {country}"),
    "ja": ("今日の{country}の歴史", "今日の{country}の重要な歴史イベント"),
    "ko": ("오늘의 {country} 역사", "오늘 {country}의 중요한 역사적 사건"),
    "es": ("Hoy en la Historia de {country}", "Eventos históricos importantes de hoy en {country}"),
    "fr": ("Aujourd'hui dans l'Histoire de {country}", "Événements historiques importants d'aujourd'hui en {country}"),
    "de": ("Heute in der Geschichte von {country}", "Wichtige historische Ereignisse heute in {country}"),
    "pt": ("Hoje na História do {country}", "Eventos históricos importantes de hoje no {country}"),
    "ru": ("Сегодня в истории {country}", "Важные исторические события сегодня в {country}"),
    "ar": ("اليوم في تاريخ {country}", "أحداث تاريخية مهمة اليوم في {country}"),
    "it": ("Oggi nella Storia di {country}", "Importanti eventi storici di oggi in {country}"),
    "nl": ("Vandaag in de Geschiedenis van {country}", "Belangrijke historische gebeurtenissen van vandaag in {country}"),
    "pl": ("Dziś w Historii {country}", "Ważne wydarzenia historyczne dziś w {country}"),
    "tr": ("Bugün {country} Tarihinde", "Bugün {country}'deki önemli tarihi olaylar"),
    "vi": ("Hôm nay trong Lịch sử {country}", "Sự kiện lịch sử quan trọng hôm nay ở {country}"),
    "th": ("วันนี้ในประวัติศาสตร์{country}", "เหตุการณ์ทางประวัติศาสตร์ที่สำคัญของวันนี้ใน{country}"),
    "id": ("Hari Ini dalam Sejarah {country}", "Peristiwa bersejarah penting hari ini di {country}"),
    "sv": ("Idag i {country}s Historia", "Viktiga historiska händelser idag i {country}"),
    "cs": ("Dnes v Historii {country}", "Důležité historické události dnes v {country}"),
    "da": ("I Dag i {country}s Historie", "Vigtige historiske begivenheder i dag i {country}"),
}


def yaml_escape(s: str) -> str:
    """YAML 字符串转义"""
    if not s:
        return ""
    return s.replace('"', '\\"').replace("\n", " ").replace("\r", "")


def get_country_name_for_lang(country_code: str, lang: str) -> str:
    """获取地区在指定语种下的名称"""
    if lang == "zh":
        return COUNTRY_NAMES.get(country_code, country_code)
    return COUNTRY_NAMES_EN.get(country_code, country_code)


def translate_event_title(title: str, description: str, lang: str, country_code: str) -> tuple[str, str]:
    """简单的模板翻译(不调 API,直接用语言前缀)

    生产环境中,这个函数应该调用 GPT-4o 翻译。
    本地全链路测试时使用模板翻译。
    """
    country_name = get_country_name_for_lang(country_code, lang)

    # 语言前缀(表明这是某种语言版本)
    lang_prefix_map = {
        "zh": "",
        "en": "[EN] ",
        "ja": "[JA] ",
        "ko": "[KO] ",
        "es": "[ES] ",
        "fr": "[FR] ",
        "de": "[DE] ",
        "pt": "[PT] ",
        "ru": "[RU] ",
        "ar": "[AR] ",
        "it": "[IT] ",
        "nl": "[NL] ",
        "pl": "[PL] ",
        "tr": "[TR] ",
        "vi": "[VI] ",
        "th": "[TH] ",
        "id": "[ID] ",
        "sv": "[SV] ",
        "cs": "[CS] ",
        "da": "[DA] ",
    }
    prefix = lang_prefix_map.get(lang, "")

    # 中文直接使用原文,其他语言添加前缀(模拟翻译效果)
    if lang == "zh":
        return title, description
    return f"{prefix}{title}", f"{prefix}{description}"


def load_event_pool(month: str, day: str, country: str) -> dict | None:
    """从 fixture 加载事件池"""
    fixture_path = (
        PROJECT_ROOT / "tests" / "fixtures" / "mock_responses" / "wikipedia"
        / f"{month}-{day}_{country}.json"
    )
    if not fixture_path.exists():
        return None
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_markdown_for_day(
    month: str,
    day: str,
    country: str,
    lang: str,
    event_pool: dict,
    output_dir: Path,
) -> str | None:
    """生成单日单地区单语种的 Markdown 文件"""
    events = event_pool.get("events", [])
    if not events:
        return None

    country_name = get_country_name_for_lang(country, lang)
    title_template, desc_template = LANG_TITLE_TEMPLATES.get(
        lang, LANG_TITLE_TEMPLATES["en"]
    )

    page_title = title_template.format(country=country_name)
    page_desc = desc_template.format(country=country_name)
    date_str = f"2024-{month}-{day}"

    # 构造 events YAML
    events_yaml = []
    body_sections = []
    for idx, event in enumerate(events):
        original_title = event.get("title", f"Event {idx}")
        original_desc = event.get("description", "")
        event_year = event.get("year", 2000)

        translated_title, translated_desc = translate_event_title(
            original_title, original_desc, lang, country
        )

        # Mock 图片 URL
        image_url = f"https://mock.example.com/images/{country}/{month}-{day}-{idx}.jpg"
        image_caption = f"{country_name} - {translated_title[:50]}"

        events_yaml.append(
            f"  - year: {event_year}\n"
            f'    title: "{yaml_escape(translated_title)}"\n'
            f'    description: "{yaml_escape(translated_desc)}"\n'
            f'    image_url: "{yaml_escape(image_url)}"\n'
            f'    image_caption: "{yaml_escape(image_caption)}"'
        )

        body_sections.append(
            f"## {event_year} — {translated_title}\n\n"
            f"{translated_desc}\n\n"
            f"![{translated_title}]({image_url})\n\n"
            f"*{image_caption}*\n"
        )

    # 输出路径: site/content/{lang}/{country}/{MM-DD}.md
    out_path = output_dir / lang / country / f"{month}-{day}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""---
title: "{month}-{day} · {yaml_escape(page_title)}"
date: {date_str}
country_code: "{country}"
country_name: "{yaml_escape(country_name)}"
language: "{lang}"
draft: false
events:
{chr(10).join(events_yaml)}
---

# {page_title}

> {page_desc}

{chr(10).join(body_sections)}
"""
    out_path.write_text(content, encoding="utf-8")
    return str(out_path)


def generate_index_pages(output_dir: Path, languages: list[str], countries: list[str]) -> int:
    """生成各语种/地区的 _index.md"""
    count = 0
    for lang in languages:
        lang_name = LANGUAGE_NAMES.get(lang, lang)
        lang_dir = output_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)

        # 语种首页
        index_file = lang_dir / "_index.md"
        title_template, desc_template = LANG_TITLE_TEMPLATES.get(
            lang, LANG_TITLE_TEMPLATES["en"]
        )
        # 用 "World" 替换 country
        title = title_template.format(country="World")
        desc = desc_template.format(country="World")

        index_content = f"""---
title: "{yaml_escape(title)}"
language: "{lang}"
draft: false
weight: 1
---

# {title}

> {desc}

Browse today in history by country:
"""
        for country in countries:
            country_name = get_country_name_for_lang(country, lang)
            index_content += f"- [{country_name}](/{lang}/{country}/)\n"

        index_file.write_text(index_content, encoding="utf-8")
        count += 1

        # 各地区子首页
        for country in countries:
            country_dir = lang_dir / country
            country_dir.mkdir(parents=True, exist_ok=True)
            country_index = country_dir / "_index.md"
            country_name = get_country_name_for_lang(country, lang)
            country_title = title_template.format(country=country_name)
            country_desc = desc_template.format(country=country_name)

            ci_content = f"""---
title: "{yaml_escape(country_title)}"
date: 2024-01-01
country_code: "{country}"
country_name: "{yaml_escape(country_name)}"
language: "{lang}"
draft: false
---

# {country_title}

> {country_desc}

按月份浏览:
"""
            for m in range(1, 13):
                ci_content += f"- [{m:02d}月](/lang/{country}/{m:02d}/)\n"

            country_index.write_text(ci_content, encoding="utf-8")
            count += 1

    return count


def main():
    parser = argparse.ArgumentParser(description="批量生成 Hugo 全量内容")
    parser.add_argument("--output-dir", default="site/content", help="输出目录")
    parser.add_argument("--limit-days", type=int, default=0, help="限制天数(0=全部366)")
    parser.add_argument("--countries", default="", help="限制地区(逗号分隔)")
    parser.add_argument("--languages", default="", help="限制语种(逗号分隔)")
    parser.add_argument("--skip-index", action="store_true", help="跳过 _index.md 生成")
    args = parser.parse_args()

    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    countries = (
        [c.strip() for c in args.countries.split(",") if c.strip()]
        if args.countries
        else ALL_COUNTRIES
    )
    languages = (
        [l.strip() for l in args.languages.split(",") if l.strip()]
        if args.languages
        else LANGUAGES
    )

    # 生成日期列表(2024 闰年,366天)
    start_date = date(2024, 1, 1)
    total_days = 366 if args.limit_days == 0 else min(args.limit_days, 366)
    dates = [(start_date + timedelta(days=i)) for i in range(total_days)]
    date_strs = [(d.strftime("%m"), d.strftime("%d")) for d in dates]

    total_target = len(countries) * len(date_strs) * len(languages)
    print(f"🚀 开始批量生成 Hugo 内容")
    print(f"   输出目录: {output_dir}")
    print(f"   地区数: {len(countries)}")
    print(f"   天数: {len(date_strs)}")
    print(f"   语种数: {len(languages)}")
    print(f"   目标文件数: {total_target:,}")

    start_time = time.time()
    generated = 0
    failed = 0
    last_progress = 0

    for month, day in date_strs:
        for country in countries:
            # 加载事件池
            event_pool = load_event_pool(month, day, country)
            if event_pool is None:
                failed += len(languages)
                continue

            for lang in languages:
                try:
                    result = generate_markdown_for_day(
                        month, day, country, lang, event_pool, output_dir
                    )
                    if result:
                        generated += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    if failed <= 5:
                        print(f"  ❌ 生成失败: {lang}/{country}/{month}-{day}: {e}")

        # 进度日志
        progress = (generated + failed) / total_target * 100
        if progress - last_progress >= 5:
            elapsed = time.time() - start_time
            rate = generated / elapsed if elapsed > 0 else 0
            print(
                f"  进度: {progress:.1f}% ({generated:,}/{total_target:,})"
                f" - 速度: {rate:.0f} 文件/秒 - 已用时: {elapsed:.0f}s"
            )
            last_progress = progress

    elapsed = time.time() - start_time
    print(f"\n✅ 完成!")
    print(f"   生成文件数: {generated:,}")
    print(f"   失败数: {failed:,}")
    print(f"   总耗时: {elapsed:.1f}s")
    print(f"   平均速度: {generated / elapsed:.0f} 文件/秒" if elapsed > 0 else "")

    # 生成索引页
    if not args.skip_index:
        print(f"\n📄 生成索引页...")
        index_count = generate_index_pages(output_dir, languages, countries)
        print(f"   索引页: {index_count}")

    # 验证总体积
    try:
        total_size = sum(f.stat().st_size for f in output_dir.rglob("*.md"))
        print(f"   总体积: {total_size / 1024 / 1024:.2f} MB")
    except Exception:
        pass


if __name__ == "__main__":
    main()
