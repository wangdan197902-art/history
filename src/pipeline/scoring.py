"""评分模块 — 中立性/相关性/合规性评分

基于关键词和规则的简单评分(Mock 阶段足够用)
Phase 4 可替换为 LLM 评分
"""
import re
from typing import Iterable


# === 中立性评分关键词 ===
# 极端词汇(降低中立性)
EXTREME_WORDS = {
    "邪恶", "伟大", "神圣", "卑鄙", "无耻", "伟大领袖", "伟大导师",
    "evil", "great", "sacred", "infamous", "glorious",
    "极其", "非常", "无比", "最",
}

# 客观词汇(提升中立性)
OBJECTIVE_WORDS = {
    "发生", "召开", "签订", "建立", "成立", "宣布", "通过", "颁布",
    "occurred", "established", "signed", "announced", "passed",
    "历史性", "重要的",
}

# 主观判断词(降低中立性)
SUBJECTIVE_WORDS = {
    "应该", "必须", "显然", "当然", "无疑",
    "should", "must", "obviously", "certainly",
}


def calculate_neutrality_score(text: str) -> float:
    """计算文本中立性评分

    Args:
        text: 待评估文本

    Returns:
        float: 0.0-1.0, 1.0 为完全中立
    """
    if not text:
        return 0.5

    text_lower = text.lower()
    total_words = len(text.split())
    if total_words == 0:
        return 0.5

    extreme_count = sum(1 for w in EXTREME_WORDS if w in text_lower)
    subjective_count = sum(1 for w in SUBJECTIVE_WORDS if w in text_lower)
    objective_count = sum(1 for w in OBJECTIVE_WORDS if w in text_lower)

    # 计算评分
    base_score = 0.7
    base_score -= extreme_count * 0.1
    base_score -= subjective_count * 0.05
    base_score += objective_count * 0.03

    # 限制在 0-1 范围
    return max(0.0, min(1.0, base_score))


def calculate_relevance_score(text: str, country_code: str, country_keywords: dict | None = None) -> float:
    """计算文本与地区的相关性评分

    Args:
        text: 待评估文本
        country_code: 地区代码
        country_keywords: 地区关键词字典(可选)

    Returns:
        float: 0.0-1.0, 1.0 为完全相关
    """
    if not text:
        return 0.0

    # 默认关键词(可扩展)
    default_keywords = {
        "CN": ["中国", "中华", "北京", "上海", "china", "chinese"],
        "US": ["美国", "美利坚", "华盛顿", "纽约", "united states", "america"],
        "JP": ["日本", "东京", "japan", "japanese"],
        "KR": ["韩国", "朝鲜", "首尔", "korea", "korean"],
        "UK": ["英国", "伦敦", "united kingdom", "britain"],
    }

    keywords = country_keywords or default_keywords
    country_keywords_list = keywords.get(country_code, [])

    if not country_keywords_list:
        return 0.5  # 无关键词,默认中等相关

    text_lower = text.lower()
    matches = sum(1 for kw in country_keywords_list if kw.lower() in text_lower)

    # 至少 1 个匹配算 0.5,3 个以上算 1.0
    score = min(1.0, 0.3 + matches * 0.2)
    return score


def calculate_compliance_score(text: str, sensitive_words: Iterable[str] | None = None) -> float:
    """计算合规性评分

    Args:
        text: 待评估文本
        sensitive_words: 敏感词列表

    Returns:
        float: 0.0-1.0, 1.0 为完全合规
    """
    if not text:
        return 1.0

    # 默认敏感词(简化版,实际应从配置加载)
    default_sensitive = {
        "反动", "颠覆", "分裂", "恐怖", "极端",
    }

    sensitive_set = set(sensitive_words) if sensitive_words else default_sensitive
    text_lower = text.lower()

    violations = sum(1 for w in sensitive_set if w in text_lower)
    if violations == 0:
        return 1.0
    return max(0.0, 1.0 - violations * 0.2)


def get_text_stats(text: str) -> dict:
    """获取文本统计信息

    Returns:
        dict: 字数/句数/平均句长
    """
    if not text:
        return {"chars": 0, "sentences": 0, "avg_sentence_len": 0}

    chars = len(text)
    # 简单分句(中英文标点)
    sentences = re.split(r"[。.!?！？\n]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    avg_len = chars / len(sentences) if sentences else 0

    return {
        "chars": chars,
        "sentences": len(sentences),
        "avg_sentence_len": round(avg_len, 1),
    }
