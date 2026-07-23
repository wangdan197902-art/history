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
import hashlib
import json
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# tomllib 为 Python 3.11+ 标准库;3.10 及以下尝试外部 backport tomli,均不可用则降级
try:
    import tomllib  # Python 3.11+ 标准库
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]  # 可选 backport
    except ImportError:
        tomllib = None  # type: ignore[assignment]  # Python <3.11 且无 tomli

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


# === LLM 翻译配置(可选) ===
# 当 llm.config.toml 配置了有效 api_key 时,调用 LLM API 进行真实翻译;
# 否则回退到下方的模板翻译模式(语言前缀)。
try:
    import httpx
    import diskcache
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
    )
    _LLM_DEPS_AVAILABLE = True
except ImportError:
    _LLM_DEPS_AVAILABLE = False

# 全局 LLM 状态(延迟初始化,避免无配置时的开销)
_LLM_CONFIG: dict | None = None
_LLM_CACHE = None
_LLM_STATE_INIT = False


def load_llm_config() -> dict | None:
    """加载 LLM 配置

    优先读取 llm.config.toml(实际值,被 .gitignore 排除);
    不存在则读取 llm.config.example.toml(占位符,api_key 必然为空)。
    返回完整配置 dict;若 api_key 为空或依赖库缺失,返回 None(回退到模板模式)。
    """
    # tomllib 不可用(Python <3.11 且未装 tomli),无法解析 TOML,回退到模板模式
    if tomllib is None:
        print("⚠️ tomllib 不可用(需 Python 3.11+ 或安装 tomli),回退到模板模式")
        return None

    # 优先读取实际配置(用户本地填写)
    config_path = PROJECT_ROOT / "llm.config.toml"
    if not config_path.exists():
        # 回退到示例配置(api_key 必然为空,会走模板模式)
        config_path = PROJECT_ROOT / "llm.config.example.toml"
        if not config_path.exists():
            return None

    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    except Exception as e:
        print(f"⚠️ 读取 LLM 配置失败({config_path.name}): {e},回退到模板模式")
        return None

    llm_cfg = config.get("llm", {})
    api_key = str(llm_cfg.get("api_key", "")).strip()

    # api_key 为空,或依赖库缺失,都走模板模式
    if not api_key:
        return None
    if not _LLM_DEPS_AVAILABLE:
        print("⚠️ httpx/tenacity/diskcache 未安装,回退到模板模式")
        return None

    return config


def _get_llm_state() -> tuple[dict | None, object | None]:
    """延迟初始化并返回 (config, cache) 元组

    首次调用时读取配置并初始化磁盘缓存;后续调用直接返回缓存值。
    线程安全注: 本脚本为单线程顺序执行,无需加锁。
    """
    global _LLM_CONFIG, _LLM_CACHE, _LLM_STATE_INIT
    if not _LLM_STATE_INIT:
        _LLM_STATE_INIT = True
        _LLM_CONFIG = load_llm_config()
        if _LLM_CONFIG is not None:
            cache_dir = PROJECT_ROOT / ".cache" / "llm_translations"
            cache_dir.mkdir(parents=True, exist_ok=True)
            _LLM_CACHE = diskcache.Cache(str(cache_dir))
            llm_cfg = _LLM_CONFIG.get("llm", {})
            print(
                f"🤖 LLM 翻译已启用: model={llm_cfg.get('model')}, "
                f"base_url={llm_cfg.get('base_url')}"
            )
        else:
            print("ℹ️ LLM 未配置(api_key 为空),使用模板翻译模式")
    return _LLM_CONFIG, _LLM_CACHE


def _call_llm_translate(
    title: str, description: str, lang: str, config: dict
) -> tuple[str, str]:
    """调用 LLM API 翻译标题和描述

    使用 OpenAI 兼容的 /chat/completions 接口,带重试逻辑(tenacity)。
    返回 (translated_title, translated_description);失败时抛出异常(由调用方捕获并回退)。
    """
    llm_cfg = config.get("llm", {})
    api_key = llm_cfg.get("api_key", "")
    base_url = str(llm_cfg.get("base_url", "https://api.openai.com/v1")).rstrip("/")
    model = llm_cfg.get("model", "gpt-4o-mini")
    timeout = float(llm_cfg.get("timeout", 30))
    max_retries = int(llm_cfg.get("max_retries", 3))

    lang_name = LANGUAGE_NAMES.get(lang, lang)
    prompt = (
        f"将以下历史事件标题和描述翻译为{lang_name}语种,保留年份和专有名词。\n"
        f'严格按 JSON 格式返回: {{"title": "...", "description": "..."}}\n'
        f"标题: {title}\n"
        f"描述: {description}"
    )

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是专业的历史事件翻译助手。只返回 JSON,不要其他内容。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }

    @retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (httpx.HTTPError, httpx.TimeoutException)
        ),
    )
    def _do_request() -> dict:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    data = _do_request()
    content = data["choices"][0]["message"]["content"].strip()

    # 解析 JSON(容忍前后可能的 markdown 代码块包裹)
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if not json_match:
        raise ValueError(f"LLM 返回内容无法解析为 JSON: {content[:200]}")

    parsed = json.loads(json_match.group(0))
    t_title = str(parsed.get("title", "")).strip()
    t_desc = str(parsed.get("description", "")).strip()

    if not t_title or not t_desc:
        raise ValueError(f"LLM 返回内容字段为空: {parsed}")

    return t_title, t_desc


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
    "el": ("Σήμερα στην Ιστορία του {country}", "Σημαντικά ιστορικά γεγονότα σήμερα στο {country}"),
    "fi": ("Tänään {country}n Historiassa", "Tärkeitä historiallisia tapahtumia tänään {country}ssa"),
    "hu": ("Ma {country} Történelmében", "Fontos történelmi események ma {country}ban"),
    "no": ("I Dag i {country}s Historie", "Viktige historiske hendelser i dag i {country}"),
    "ro": ("Astăzi în Istoria {country}", "Evenimente istorice importante de astăzi în {country}"),
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
    """翻译事件标题和描述

    优先使用 LLM API 翻译(若 llm.config.toml 配置了有效 api_key);
    否则回退到模板模式(语言前缀)。中文直接返回原文。

    生产环境中,当 llm.config.toml 配置了有效 api_key 时调用 LLM API;
    本地全链路测试(api_key 为空)时使用模板翻译。
    """
    # 中文直接使用原文
    if lang == "zh":
        return title, description

    # 尝试 LLM 翻译
    config, cache = _get_llm_state()
    if config is not None and cache is not None:
        # 构造缓存 key(包含 lang + 内容 hash,避免重复翻译相同内容)
        cache_key_raw = f"{lang}|{title}|{description}"
        cache_key = hashlib.sha256(cache_key_raw.encode("utf-8")).hexdigest()

        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            t_title, t_desc = _call_llm_translate(title, description, lang, config)
            result = (t_title, t_desc)
            cache.set(cache_key, result)
            return result
        except Exception as e:
            # 失败时回退到模板模式(仅警告一次,避免刷屏)
            if not getattr(translate_event_title, "_warned_fallback", False):
                print(f"⚠️ LLM 翻译失败,回退到模板模式(仅警告一次): {e}")
                translate_event_title._warned_fallback = True

    # 模板模式(语言前缀,表明这是某种语言版本)
    lang_prefix_map = {
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
            index_content += f"- [{country_name}](/{lang}/{country.lower()}/)\n"

        index_file.write_text(index_content, encoding="utf-8")
        count += 1

        # 搜索页（Pagefind UI 容器，url: "/search/" 强制路由到根目录 /search/）
        # site/content/ 整个目录被 .gitignore 忽略，CI 动态生成内容时必须同时生成 search.md
        # 否则 /{lang}/search/ 返回 404，Pagefind 搜索功能不可用
        # type: "search" 强制 Hugo 使用 layouts/search/single.html 而非 _default/single.html
        # （否则 PagefindUI 初始化代码不会被注入，搜索页退化为普通文章页）
        search_file = lang_dir / "search.md"
        search_content = """---
title: "Search"
url: "/search/"
type: "search"
layout: "search"
draft: false
---

Search across all historical events in this archive.
"""
        search_file.write_text(search_content, encoding="utf-8")
        count += 1

        # 各地区子首页
        for country in countries:
            country_dir = lang_dir / country.lower()
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
