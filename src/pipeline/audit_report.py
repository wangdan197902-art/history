"""审核报告生成器

生成 Markdown / JSON 格式的审核报告
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.models.event import AuditedEvent
from src.pipeline.stage_audit import get_audit_stats, filter_failed


def generate_audit_report(
    audited_list: list[AuditedEvent],
    output_dir: str = "09_报告",
    date_str: str | None = None,
) -> dict[str, str]:
    """生成审核报告

    Args:
        audited_list: 审核后事件列表
        output_dir: 输出目录
        date_str: 日期字符串(默认当前日期)

    Returns:
        dict: {"markdown": md_path, "json": json_path}
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    stats = get_audit_stats(audited_list)
    failed_list = filter_failed(audited_list)

    # === JSON 报告 ===
    json_data = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "failed_items": [
            {
                "id": f.illustrated.translated.regionalized.original.id,
                "title": f.illustrated.translated.translated_title,
                "country": f.illustrated.translated.regionalized.country_code,
                "lang": f.illustrated.translated.lang,
                "compliance_score": f.compliance_score,
                "issues": f.audit_issues,
                "notes": f.audit_notes,
            }
            for f in failed_list
        ],
    }

    json_path = output_path / f"audit_report_{date_str}.json"
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # === Markdown 报告 ===
    md_content = f"""# 审核报告 — {date_str}

> 生成时间: {datetime.now(timezone.utc).isoformat()}

## 一、统计概览

| 指标 | 数值 |
|------|------|
| 总事件数 | {stats['total']} |
| 通过数 | {stats['passed']} |
| 失败数 | {stats['failed']} |
| 通过率 | {stats['pass_rate']:.2%} |
| 平均合规评分 | {stats['avg_compliance']:.4f} |

## 二、未通过事件详情

"""
    if not failed_list:
        md_content += "✅ 所有事件审核通过,无未通过项。\n"
    else:
        md_content += f"共 {len(failed_list)} 个事件未通过审核:\n\n"
        for i, f in enumerate(failed_list, 1):
            md_content += f"""### {i}. {f.illustrated.translated.translated_title}

- **事件 ID**: {f.illustrated.translated.regionalized.original.id}
- **地区**: {f.illustrated.translated.regionalized.country_code}
- **语言**: {f.illustrated.translated.lang}
- **合规评分**: {f.compliance_score:.4f}
- **问题清单**: {', '.join(f.audit_issues) if f.audit_issues else '无'}
- **审核备注**: {f.audit_notes or '无'}

"""

    md_path = output_path / f"audit_report_{date_str}.md"
    md_path.write_text(md_content, encoding="utf-8")

    return {
        "markdown": str(md_path),
        "json": str(json_path),
    }


def print_audit_summary(audited_list: list[AuditedEvent]) -> None:
    """打印审核摘要到控制台

    Args:
        audited_list: 审核后事件列表
    """
    stats = get_audit_stats(audited_list)

    print("\n" + "=" * 50)
    print("📋 审核摘要")
    print("=" * 50)
    print(f"总事件数:     {stats['total']}")
    print(f"通过数:       {stats['passed']} ✅")
    print(f"失败数:       {stats['failed']} ❌")
    print(f"通过率:       {stats['pass_rate']:.2%}")
    print(f"平均合规评分: {stats['avg_compliance']:.4f}")
    print("=" * 50 + "\n")
