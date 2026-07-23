"""
30 地区分级清单 + 20 语种列表

地区分级:
  Tier 1 (7 个): 核心地区,优先生产
  Tier 2 (8 个): 重要地区
  Tier 3 (15 个): 拓展地区

语种: 20 种(覆盖全球主要语种 + 欧洲 + 东南亚)
"""

# === 30 地区分级清单 ===
COUNTRIES_TIER_1 = ["CN", "US", "JP", "KR", "UK", "DE", "FR"]  # 7 个核心
COUNTRIES_TIER_2 = ["RU", "BR", "IN", "AU", "CA", "IT", "ES", "MX"]  # 8 个重要
COUNTRIES_TIER_3 = [
    "ID", "TH", "VN", "SG", "MY", "PH", "SA", "AE",
    "EG", "ZA", "NG", "TR", "PL", "NL", "SE",
]  # 15 个拓展

ALL_COUNTRIES = COUNTRIES_TIER_1 + COUNTRIES_TIER_2 + COUNTRIES_TIER_3  # 共 30 个

# 地区中文名
COUNTRY_NAMES = {
    "CN": "中国", "US": "美国", "JP": "日本", "KR": "韩国", "UK": "英国",
    "DE": "德国", "FR": "法国", "RU": "俄罗斯", "BR": "巴西", "IN": "印度",
    "AU": "澳大利亚", "CA": "加拿大", "IT": "意大利", "ES": "西班牙", "MX": "墨西哥",
    "ID": "印度尼西亚", "TH": "泰国", "VN": "越南", "SG": "新加坡", "MY": "马来西亚",
    "PH": "菲律宾", "SA": "沙特阿拉伯", "AE": "阿联酋", "EG": "埃及", "ZA": "南非",
    "NG": "尼日利亚", "TR": "土耳其", "PL": "波兰", "NL": "荷兰", "SE": "瑞典",
}

# 地区英文名(用于多语种 fallback)
COUNTRY_NAMES_EN = {
    "CN": "China", "US": "United States", "JP": "Japan", "KR": "South Korea",
    "UK": "United Kingdom", "DE": "Germany", "FR": "France", "RU": "Russia",
    "BR": "Brazil", "IN": "India", "AU": "Australia", "CA": "Canada",
    "IT": "Italy", "ES": "Spain", "MX": "Mexico", "ID": "Indonesia",
    "TH": "Thailand", "VN": "Vietnam", "SG": "Singapore", "MY": "Malaysia",
    "PH": "Philippines", "SA": "Saudi Arabia", "AE": "United Arab Emirates",
    "EG": "Egypt", "ZA": "South Africa", "NG": "Nigeria", "TR": "Turkey",
    "PL": "Poland", "NL": "Netherlands", "SE": "Sweden",
}

# === 24 语种清单 ===
# 移除 th(无独立子仓),新增 el/fi/hu/no/ro(与 deploy-matrix.yml + hugo.toml 对齐)
LANGUAGES = [
    "zh", "en", "ja", "ko", "es", "fr", "de", "pt", "ru", "ar",
    "it", "nl", "pl", "tr", "vi", "id", "sv", "cs", "da",
    "el", "fi", "hu", "no", "ro",
]

LANGUAGE_NAMES = {
    "zh": "中文", "en": "English", "ja": "日本語", "ko": "한국어",
    "es": "Español", "fr": "Français", "de": "Deutsch", "pt": "Português",
    "ru": "Русский", "ar": "العربية",
    "it": "Italiano", "nl": "Nederlands", "pl": "Polski", "tr": "Türkçe",
    "vi": "Tiếng Việt", "id": "Bahasa Indonesia",
    "sv": "Svenska", "cs": "Čeština", "da": "Dansk",
    "el": "Ελληνικά", "fi": "Suomi", "hu": "Magyar", "no": "Norsk", "ro": "Română",
}

# 语种方向(ar 为 RTL,其余 LTR)
LANGUAGE_DIRECTIONS = {
    "zh": "ltr", "en": "ltr", "ja": "ltr", "ko": "ltr", "es": "ltr",
    "fr": "ltr", "de": "ltr", "pt": "ltr", "ru": "ltr", "ar": "rtl",
    "it": "ltr", "nl": "ltr", "pl": "ltr", "tr": "ltr", "vi": "ltr",
    "id": "ltr", "sv": "ltr", "cs": "ltr", "da": "ltr",
    "el": "ltr", "fi": "ltr", "hu": "ltr", "no": "ltr", "ro": "ltr",
}


def get_country_tier(country_code: str) -> int:
    """返回地区分级 1/2/3,不存在返回 0"""
    if country_code in COUNTRIES_TIER_1:
        return 1
    if country_code in COUNTRIES_TIER_2:
        return 2
    if country_code in COUNTRIES_TIER_3:
        return 3
    return 0


def get_country_name(country_code: str, lang: str = "zh") -> str:
    """获取地区名称(支持多语种 fallback)"""
    if lang == "zh":
        return COUNTRY_NAMES.get(country_code, country_code)
    if lang == "en":
        return COUNTRY_NAMES_EN.get(country_code, country_code)
    # 其他语种暂用英文 fallback(Phase 4 接入 GPT-4o 翻译)
    return COUNTRY_NAMES_EN.get(country_code, country_code)


def get_language_direction(lang: str) -> str:
    """获取语种方向 ltr/rtl"""
    return LANGUAGE_DIRECTIONS.get(lang, "ltr")


def validate_country(country_code: str) -> bool:
    """校验地区代码是否合法"""
    return country_code in ALL_COUNTRIES


def validate_language(lang: str) -> bool:
    """校验语种代码是否合法"""
    return lang in LANGUAGES
