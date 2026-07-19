"""管道阶段单元测试(使用 Mock Provider,需要 Mock Server 运行)"""
import asyncio
from pathlib import Path

import pytest
from PIL import Image

from src.config.base import Settings
from src.models.event import (
    AuditedEvent,
    Event,
    EventPool,
    IllustratedEvent,
    RegionalizedEvent,
    TranslatedEvent,
)
from src.pipeline.scoring import (
    calculate_compliance_score,
    calculate_neutrality_score,
)
from src.pipeline.stage_audit import (
    audit_illustrated,
    filter_failed,
    filter_passed,
    get_audit_stats,
)
from src.pipeline.stage_fetch import fetch_events
from src.pipeline.stage_illustrate import download_image, illustrate_batch
from src.pipeline.stage_publish import (
    generate_sitemap_entry,
    generate_sitemap_xml,
    publish_markdown,
)
from src.pipeline.stage_regionalize import regionalize_pool
from src.pipeline.stage_translate import translate_to_all_langs, translate_to_lang
from src.pipeline.image_processor import (
    convert_to_webp,
    generate_picture_tag,
    generate_responsive_images,
    get_image_info,
)
from src.pipeline.audit_report import generate_audit_report, print_audit_summary
from src.providers.factory import (
    get_auditor,
    get_illustrator,
    get_publisher,
    get_regionalizer,
    get_translator,
    get_wikipedia_fetcher,
)


# === Fixtures ===

@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def sample_event():
    return Event(
        id="evt_test_001",
        date="2024-07-04",
        year=1921,
        title="中国共产党成立",
        description="1921年中国共产党第一次全国代表大会召开",
        wikipedia_url="https://en.wikipedia.org/wiki/CCP",
        categories=["politics"],
    )


@pytest.fixture
def sample_pool(sample_event):
    return EventPool(
        date="2024-07-04",
        country_code="CN",
        events=[sample_event],
        source="wikipedia",
        fetched_at="2024-07-04T00:00:00Z",
    )


@pytest.fixture
def sample_regionalized(sample_event):
    return RegionalizedEvent(
        original=sample_event,
        country_code="CN",
        regional_title="中国共产党成立",
        regional_description="1921年中国共产党第一次全国代表大会召开,标志着中国共产党成立。",
        neutrality_score=0.85,
        regional_tags=["cn", "politics"],
    )


@pytest.fixture
def sample_translated(sample_regionalized):
    return TranslatedEvent(
        regionalized=sample_regionalized,
        lang="zh",
        translated_title="中国共产党成立",
        translated_description="1921年中国共产党第一次全国代表大会召开,标志着中国共产党成立。",
        translator="gpt-4o",
    )


@pytest.fixture
def sample_illustrated(sample_translated):
    return IllustratedEvent(
        translated=sample_translated,
        image_url="https://example.com/image.jpg",
        image_alt="中共一大会址",
        image_caption="上海中共一大会址",
    )


@pytest.fixture
def sample_audited(sample_illustrated):
    return AuditedEvent(
        illustrated=sample_illustrated,
        audit_pass=True,
        audit_notes="审核通过",
        compliance_score=0.95,
    )


# === Stage Fetch 测试 ===

class TestStageFetch:
    @pytest.mark.asyncio
    async def test_fetch_events_invalid_date(self, settings):
        """无效日期抛 ValueError"""
        fetcher = get_wikipedia_fetcher(settings)
        with pytest.raises(ValueError):
            await fetch_events(fetcher, "13", "01")
        with pytest.raises(ValueError):
            await fetch_events(fetcher, "01", "32")

    @pytest.mark.asyncio
    async def test_fetch_events_real_call(self, settings):
        """真实调用 Mock Server"""
        fetcher = get_wikipedia_fetcher(settings)
        try:
            pool = await fetch_events(fetcher, "07", "04", "CN")
            assert pool.country_code == "CN"
            assert isinstance(pool.events, list)
        finally:
            await fetcher.close()


# === Stage Regionalize 测试 ===

class TestStageRegionalize:
    @pytest.mark.asyncio
    async def test_regionalize_pool(self, settings, sample_pool):
        """地区化事件池"""
        regionalizer = get_regionalizer(settings)
        try:
            results = await regionalize_pool(regionalizer, sample_pool, semaphore_limit=2)
            assert len(results) == len(sample_pool.events)
            for r in results:
                assert isinstance(r, RegionalizedEvent)
                assert r.country_code == "CN"
        finally:
            await regionalizer.close()


# === Stage Translate 测试 ===

class TestStageTranslate:
    @pytest.mark.asyncio
    async def test_translate_to_lang_unsupported(self, settings, sample_regionalized):
        """不支持的语言抛 ValueError"""
        translator = get_translator(settings)
        try:
            with pytest.raises(ValueError):
                await translate_to_lang(translator, sample_regionalized, "xx")
        finally:
            await translator.close()

    @pytest.mark.asyncio
    async def test_translate_to_all_langs(self, settings, sample_regionalized):
        """翻译到多语种"""
        translator = get_translator(settings)
        try:
            results = await translate_to_all_langs(
                translator, sample_regionalized, ["zh", "en"], semaphore_limit=2,
            )
            assert len(results) == 2
            assert results[0].lang == "zh"
            assert results[1].lang == "en"
        finally:
            await translator.close()


# === Stage Illustrate 测试 ===

class TestStageIllustrate:
    @pytest.mark.asyncio
    async def test_illustrate_batch(self, settings, sample_translated):
        """批量配图"""
        illustrator = get_illustrator(settings)
        try:
            results = await illustrate_batch(
                illustrator, [sample_translated], semaphore_limit=2,
            )
            assert len(results) == 1
            assert isinstance(results[0], IllustratedEvent)
            assert results[0].image_url
        finally:
            await illustrator.close()


# === Stage Audit 测试 ===

class TestStageAudit:
    @pytest.mark.asyncio
    async def test_audit_illustrated(self, settings, sample_illustrated):
        """审核单个事件"""
        auditor = get_auditor(settings)
        try:
            result = await audit_illustrated(auditor, sample_illustrated)
            assert isinstance(result, AuditedEvent)
            assert 0.0 <= result.compliance_score <= 1.0
        finally:
            await auditor.close()

    def test_filter_passed(self, sample_audited):
        passed = filter_passed([sample_audited])
        assert len(passed) == 1

    def test_filter_failed(self, sample_audited):
        sample_audited.audit_pass = False
        failed = filter_failed([sample_audited])
        assert len(failed) == 1

    def test_get_audit_stats_empty(self):
        stats = get_audit_stats([])
        assert stats["total"] == 0
        assert stats["pass_rate"] == 0.0

    def test_get_audit_stats_with_data(self, sample_audited):
        stats = get_audit_stats([sample_audited])
        assert stats["total"] == 1
        assert stats["passed"] == 1
        assert stats["pass_rate"] == 1.0


# === Stage Publish 测试 ===

class TestStagePublish:
    @pytest.mark.asyncio
    async def test_publish_markdown(self, settings, sample_audited, tmp_path):
        """发布 Markdown"""
        publisher = get_publisher(settings)
        try:
            files = await publish_markdown(
                publisher, [sample_audited], output_dir=str(tmp_path),
            )
            assert len(files) >= 1
            for f in files:
                assert Path(f).exists()
                content = Path(f).read_text(encoding="utf-8")
                assert "title:" in content
                assert "events:" in content
        finally:
            await publisher.close()

    def test_generate_sitemap_entry(self, sample_audited):
        entries = generate_sitemap_entry([sample_audited])
        assert len(entries) == 1
        assert "zh" in entries[0]["url"]
        assert "CN" in entries[0]["url"]

    def test_generate_sitemap_xml(self, sample_audited, tmp_path):
        output = tmp_path / "sitemap.xml"
        path = generate_sitemap_xml(
            [sample_audited],
            output_path=str(output),
            base_url="http://localhost:1313",
        )
        assert Path(path).exists()
        content = Path(path).read_text(encoding="utf-8")
        assert "<?xml" in content
        assert "<urlset" in content


# === Image Processor 测试 ===

class TestImageProcessor:
    @pytest.fixture
    def sample_image(self, tmp_path):
        """创建测试 PNG 图片"""
        img = Image.new("RGB", (800, 600), color="red")
        path = tmp_path / "test.png"
        img.save(path)
        return str(path)

    def test_convert_to_webp(self, sample_image, tmp_path):
        out = str(tmp_path / "out.webp")
        result = convert_to_webp(sample_image, out, quality=80)
        assert Path(result).exists()
        assert Path(result).suffix == ".webp"

    def test_convert_to_webp_with_resize(self, sample_image, tmp_path):
        out = str(tmp_path / "out_small.webp")
        result = convert_to_webp(sample_image, out, quality=80, max_width=400)
        assert Path(result).exists()
        with Image.open(result) as img:
            assert img.width == 400

    def test_convert_to_webp_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            convert_to_webp(str(tmp_path / "nope.png"), str(tmp_path / "out.webp"))

    def test_generate_responsive_images(self, sample_image, tmp_path):
        results = generate_responsive_images(
            sample_image, str(tmp_path / "resp"), sizes=[400, 800],
        )
        assert len(results) == 2
        assert 400 in results
        assert 800 in results

    def test_get_image_info(self, sample_image):
        info = get_image_info(sample_image)
        assert info["width"] == 800
        assert info["height"] == 600
        assert info["format"] == "PNG"

    def test_generate_picture_tag(self):
        paths = {400: "site/static/img_400w.webp", 800: "site/static/img_800w.webp"}
        tag = generate_picture_tag(paths, alt="测试")
        assert "<picture" in tag
        assert "srcset" in tag
        assert "img_800w.webp" in tag


# === Audit Report 测试 ===

class TestAuditReport:
    def test_generate_audit_report(self, sample_audited, tmp_path):
        out_dir = str(tmp_path / "reports")
        result = generate_audit_report(
            [sample_audited], output_dir=out_dir, date_str="2024-07-04",
        )
        assert "markdown" in result
        assert "json" in result
        assert Path(result["markdown"]).exists()
        assert Path(result["json"]).exists()
        # 验证 JSON
        import json
        data = json.loads(Path(result["json"]).read_text(encoding="utf-8"))
        assert data["date"] == "2024-07-04"
        assert data["stats"]["total"] == 1

    def test_generate_audit_report_empty(self, tmp_path):
        out_dir = str(tmp_path / "reports_empty")
        result = generate_audit_report([], output_dir=out_dir, date_str="2024-01-01")
        assert Path(result["markdown"]).exists()

    def test_print_audit_summary(self, sample_audited, capsys):
        print_audit_summary([sample_audited])
        captured = capsys.readouterr()
        assert "审核摘要" in captured.out
        assert "总事件数" in captured.out
