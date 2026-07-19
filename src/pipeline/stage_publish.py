"""Stage 6: Publish — 发布到 Hugo Markdown / 邮件订阅

将审核通过的事件发布为 Hugo Markdown 文件,或发送邮件
"""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.models.event import AuditedEvent
from src.models.countries import get_country_name
from src.providers.base import Publisher


async def publish_markdown(
    publisher: Publisher,
    audited_list: list[AuditedEvent],
    output_dir: str = "site/content",
    filter_passed: bool = True,
) -> list[str]:
    """发布为 Hugo Markdown

    Args:
        publisher: 发布器
        audited_list: 审核后事件列表
        output_dir: 输出根目录(site/content)
        filter_passed: 是否仅发布审核通过的

    Returns:
        list[str]: 已生成的文件路径列表
    """
    # 过滤审核通过的事件
    if filter_passed:
        to_publish = [a for a in audited_list if a.audit_pass]
    else:
        to_publish = audited_list

    if not to_publish:
        return []

    # 按语言和地区分组
    grouped: dict[tuple[str, str], list[AuditedEvent]] = {}
    for audited in to_publish:
        lang = audited.illustrated.translated.lang
        country = audited.illustrated.translated.regionalized.country_code
        key = (lang, country)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(audited)

    # 逐组发布
    all_files: list[str] = []
    for (lang, country), items in grouped.items():
        output_path = Path(output_dir) / lang / country
        files = await publisher.publish_markdown(items, str(output_path))
        all_files.extend(files)

    return all_files


async def publish_newsletter(
    publisher: Publisher,
    audited_list: list[AuditedEvent],
    filter_passed: bool = True,
) -> str:
    """发布邮件订阅

    Args:
        publisher: 发布器
        audited_list: 审核后事件列表
        filter_passed: 是否仅发布审核通过的

    Returns:
        str: 邮件 ID
    """
    if filter_passed:
        to_publish = [a for a in audited_list if a.audit_pass]
    else:
        to_publish = audited_list

    if not to_publish:
        return ""

    return await publisher.publish_newsletter(to_publish)


async def publish_all(
    publisher: Publisher,
    audited_list: list[AuditedEvent],
    output_dir: str = "site/content",
    publish_email: bool = False,
) -> dict[str, Any]:
    """同时发布 Markdown 和邮件

    Args:
        publisher: 发布器
        audited_list: 审核后事件列表
        output_dir: 输出目录
        publish_email: 是否发布邮件

    Returns:
        dict: {"markdown_files": [...], "email_id": "..."}
    """
    markdown_files = await publish_markdown(publisher, audited_list, output_dir)
    email_id = ""
    if publish_email:
        email_id = await publish_newsletter(publisher, audited_list)

    return {
        "markdown_files": markdown_files,
        "email_id": email_id,
        "total_published": len(markdown_files),
    }


def generate_sitemap_entry(
    audited_list: list[AuditedEvent],
    base_url: str = "http://localhost:1313",
) -> list[dict]:
    """生成 sitemap 条目

    Args:
        audited_list: 审核后事件列表
        base_url: 站点基础 URL

    Returns:
        list[dict]: sitemap 条目
    """
    entries = []
    for audited in audited_list:
        if not audited.audit_pass:
            continue

        translated = audited.illustrated.translated
        lang = translated.lang
        country = translated.regionalized.country_code
        date_str = translated.regionalized.original.date
        month_day = date_str[5:]  # MM-DD

        url = f"{base_url}/{lang}/on-this-day/{country}/{month_day}/"
        entries.append({
            "url": url,
            "lastmod": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "changefreq": "monthly",
            "priority": "0.8",
        })

    return entries


def generate_sitemap_xml(
    audited_list: list[AuditedEvent],
    output_path: str = "site/static/sitemap.xml",
    base_url: str = "http://localhost:1313",
) -> str:
    """生成 sitemap.xml 文件

    Args:
        audited_list: 审核后事件列表
        output_path: 输出路径
        base_url: 基础 URL

    Returns:
        str: 输出文件路径
    """
    entries = generate_sitemap_entry(audited_list, base_url)

    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for entry in entries:
        xml_content += "  <url>\n"
        xml_content += f"    <loc>{entry['url']}</loc>\n"
        xml_content += f"    <lastmod>{entry['lastmod']}</lastmod>\n"
        xml_content += f"    <changefreq>{entry['changefreq']}</changefreq>\n"
        xml_content += f"    <priority>{entry['priority']}</priority>\n"
        xml_content += "  </url>\n"
    xml_content += "</urlset>\n"

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(xml_content, encoding="utf-8")

    return str(output_file)


async def publish_with_sitemap(
    publisher: Publisher,
    audited_list: list[AuditedEvent],
    output_dir: str = "site/content",
    sitemap_path: str = "site/static/sitemap.xml",
) -> dict[str, Any]:
    """发布并生成 sitemap

    Args:
        publisher: 发布器
        audited_list: 审核后事件列表
        output_dir: 内容输出目录
        sitemap_path: sitemap 输出路径

    Returns:
        dict: 发布结果
    """
    result = await publish_all(publisher, audited_list, output_dir, publish_email=False)

    sitemap_file = generate_sitemap_xml(audited_list, sitemap_path)
    result["sitemap_file"] = sitemap_file

    return result
