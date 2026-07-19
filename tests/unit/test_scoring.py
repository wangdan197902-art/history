"""评分模块测试"""
import pytest

from src.pipeline.scoring import (
    calculate_neutrality_score,
    calculate_relevance_score,
    calculate_compliance_score,
    get_text_stats,
)


class TestNeutralityScore:
    """中立性评分测试"""

    def test_empty_text(self):
        assert calculate_neutrality_score("") == 0.5

    def test_objective_text(self):
        """客观词汇提升中立性"""
        text = "1949年中华人民共和国宣布成立,这是历史性的重要的事件。"
        score = calculate_neutrality_score(text)
        assert 0.7 <= score <= 1.0

    def test_extreme_words_lower_score(self):
        """极端词汇降低中立性"""
        text = "这是最伟大的神圣事件"
        score = calculate_neutrality_score(text)
        assert score < 0.7

    def test_subjective_words_lower_score(self):
        """主观词降低中立性"""
        text = "显然应该必须这样做"
        score = calculate_neutrality_score(text)
        assert score < 0.7

    def test_score_in_range(self):
        """评分在 0-1 之间"""
        texts = ["", "正常文本", "极端邪恶可耻", "客观发生签订"]
        for t in texts:
            score = calculate_neutrality_score(t)
            assert 0.0 <= score <= 1.0


class TestRelevanceScore:
    """相关性评分测试"""

    def test_empty_text(self):
        assert calculate_relevance_score("", "CN") == 0.0

    def test_default_keywords_match(self):
        """默认关键词匹配"""
        text = "中国在历史上是重要的国家,北京是其首都"
        score = calculate_relevance_score(text, "CN")
        assert score >= 0.5

    def test_no_keywords_country(self):
        """无关键词地区返回 0.5"""
        text = "随便一段文字"
        score = calculate_relevance_score(text, "XX")
        assert score == 0.5

    def test_custom_keywords(self):
        """自定义关键词"""
        text = "苹果 香蕉 橙子"
        score = calculate_relevance_score(
            text, "CN", country_keywords={"CN": ["苹果", "香蕉", "橙子"]}
        )
        # 3 个匹配 → 0.3 + 3*0.2 = 0.9,封顶 1.0
        assert score >= 0.9


class TestComplianceScore:
    """合规性评分测试"""

    def test_empty_text(self):
        assert calculate_compliance_score("") == 1.0

    def test_no_sensitive_words(self):
        """无敏感词"""
        assert calculate_compliance_score("正常文本") == 1.0

    def test_single_sensitive_word(self):
        """单个敏感词"""
        score = calculate_compliance_score("包含反动内容")
        assert score == 0.8

    def test_multiple_sensitive_words(self):
        """多个敏感词"""
        score = calculate_compliance_score("反动 颠覆 分裂 恐怖")
        assert score < 0.5

    def test_custom_sensitive_words(self):
        """自定义敏感词"""
        score = calculate_compliance_score(
            "bad content", sensitive_words={"bad", "content"}
        )
        assert score < 1.0


class TestTextStats:
    """文本统计测试"""

    def test_empty_text(self):
        stats = get_text_stats("")
        assert stats["chars"] == 0
        assert stats["sentences"] == 0
        assert stats["avg_sentence_len"] == 0

    def test_chinese_text(self):
        """中文文本统计"""
        text = "这是第一句。这是第二句！这是第三句？"
        stats = get_text_stats(text)
        assert stats["chars"] == len(text)
        assert stats["sentences"] == 3

    def test_english_text(self):
        """英文文本统计"""
        text = "First sentence. Second sentence! Third one?"
        stats = get_text_stats(text)
        assert stats["sentences"] == 3

    def test_mixed_text(self):
        """中英混合"""
        text = "Hello world. 中文句子！Another one."
        stats = get_text_stats(text)
        assert stats["sentences"] == 3
