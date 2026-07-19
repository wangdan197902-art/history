"""Stage 5: Audit — 内容审核

使用 Gemini(或 Mock)审核配图事件的合规性
"""
import asyncio
from typing import Any

from src.models.event import AuditedEvent, IllustratedEvent
from src.providers.base import Auditor
from src.pipeline.scoring import calculate_compliance_score, calculate_neutrality_score


async def audit_illustrated(
    auditor: Auditor,
    illustrated: IllustratedEvent,
) -> AuditedEvent:
    """审核单个配图事件

    Args:
        auditor: 审核器
        illustrated: 配图后事件

    Returns:
        AuditedEvent: 审核后事件
    """
    audited = await auditor.audit(illustrated)

    # 二次校准评分(基于本地规则)
    text = illustrated.translated.translated_description
    local_compliance = calculate_compliance_score(text)
    local_neutrality = calculate_neutrality_score(text)

    # 取最低值(保守策略)
    audited.compliance_score = min(audited.compliance_score, local_compliance)

    # 如果合规评分过低,标记不通过
    if audited.compliance_score < 0.5:
        audited.audit_pass = False
        audited.audit_issues.append(f"低合规评分: {audited.compliance_score:.2f}")

    # 如果中立性过低,加入警告
    if local_neutrality < 0.4:
        audited.audit_notes += f" [警告: 中立性偏低 {local_neutrality:.2f}]"

    return audited


async def audit_batch(
    auditor: Auditor,
    illustrated_list: list[IllustratedEvent],
    semaphore_limit: int = 8,
) -> list[AuditedEvent]:
    """批量审核

    Args:
        auditor: 审核器
        illustrated_list: 配图后事件列表
        semaphore_limit: 并发限制

    Returns:
        list[AuditedEvent]: 审核后事件列表
    """
    semaphore = asyncio.Semaphore(semaphore_limit)
    results: list[AuditedEvent | None] = [None] * len(illustrated_list)

    async def audit_one(idx: int, illustrated: IllustratedEvent):
        async with semaphore:
            audited = await audit_illustrated(auditor, illustrated)
            return idx, audited

    tasks = [audit_one(i, ill) for i, ill in enumerate(illustrated_list)]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for result in completed:
        if isinstance(result, Exception):
            raise result
        idx, audited = result
        results[idx] = audited

    if any(r is None for r in results):
        missing = [i for i, r in enumerate(results) if r is None]
        raise RuntimeError(f"Audit incomplete, missing indices: {missing}")

    return results  # type: ignore


def filter_passed(audited_list: list[AuditedEvent]) -> list[AuditedEvent]:
    """过滤审核通过的事件

    Args:
        audited_list: 审核后事件列表

    Returns:
        list[AuditedEvent]: 仅包含审核通过的事件
    """
    return [a for a in audited_list if a.audit_pass]


def filter_failed(audited_list: list[AuditedEvent]) -> list[AuditedEvent]:
    """过滤审核未通过的事件

    Args:
        audited_list: 审核后事件列表

    Returns:
        list[AuditedEvent]: 仅包含审核未通过的事件
    """
    return [a for a in audited_list if not a.audit_pass]


def get_audit_stats(audited_list: list[AuditedEvent]) -> dict:
    """获取审核统计

    Returns:
        dict: 总数/通过数/失败数/通过率/平均合规评分
    """
    if not audited_list:
        return {
            "total": 0, "passed": 0, "failed": 0,
            "pass_rate": 0.0, "avg_compliance": 0.0,
        }

    total = len(audited_list)
    passed = sum(1 for a in audited_list if a.audit_pass)
    failed = total - passed
    avg_compliance = sum(a.compliance_score for a in audited_list) / total

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total, 4),
        "avg_compliance": round(avg_compliance, 4),
    }
