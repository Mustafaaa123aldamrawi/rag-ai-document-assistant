from __future__ import annotations

from datetime import date, datetime
from typing import Any

from project_dashboard import build_project_dashboard
from project_engineer import normalize_progress_entry, report_window


REPORT_TYPES = {"daily", "weekly", "monthly", "final"}


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    seen = set()
    for raw in values:
        value = str(raw or "").strip()
        key = value.casefold()
        if value and key not in seen:
            output.append(value)
            seen.add(key)
    return output


def _entry_date(value: Any) -> date | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def _period_entries(
    entries: list[dict],
    period: str,
    anchor_date: date,
) -> tuple[list[dict], date | None, date | None]:
    if period == "final":
        rows = [
            normalize_progress_entry(item)
            for item in entries or []
            if normalize_progress_entry(item)
        ]
        rows.sort(key=lambda item: item["date"])
        dates = [_entry_date(item["date"]) for item in rows]
        dates = [item for item in dates if item is not None]
        return rows, (min(dates) if dates else None), (max(dates) if dates else None)

    start, end = report_window(period, anchor_date)
    rows = []
    for raw in entries or []:
        entry = normalize_progress_entry(raw)
        if not entry:
            continue
        value = _entry_date(entry["date"])
        if value and start <= value <= end:
            rows.append(entry)
    rows.sort(key=lambda item: item["date"])
    return rows, start, end


def _collect(rows: list[dict], key: str) -> list[str]:
    return _dedupe(
        [
            item
            for row in rows
            for item in (row.get(key) or [])
        ]
    )


def _latest_drawing(snapshot: dict) -> dict:
    drawings = snapshot.get("drawing_analyses") or []
    return drawings[0] if drawings else {}


def _handover_gate(snapshot: dict, dashboard: dict) -> dict:
    latest = _latest_drawing(snapshot)
    qa = latest.get("qa") or {}
    kpis = dashboard.get("kpis") or {}
    priority = dashboard.get("priority") or {}
    project = snapshot.get("project") or {}

    checks = [
        {
            "id": "project_phase",
            "label": "Project is in Handover phase",
            "passed": project.get("phase") == "Handover",
            "evidence": project.get("phase"),
        },
        {
            "id": "no_blockers",
            "label": "No open project blockers",
            "passed": int(kpis.get("open_blockers") or 0) == 0,
            "evidence": priority.get("blockers") or [],
        },
        {
            "id": "no_high_findings",
            "label": "No open high-severity engineering findings",
            "passed": int(kpis.get("high_findings") or 0) == 0,
            "evidence": priority.get("high_findings") or [],
        },
        {
            "id": "drawing_review_present",
            "label": "At least one drawing set has been analyzed",
            "passed": bool(latest),
            "evidence": latest.get("file_name"),
        },
        {
            "id": "connection_graph_reviewed",
            "label": "Connection graph has no unresolved extracted connections",
            "passed": (
                bool(latest)
                and int(kpis.get("graph_ambiguous") or 0) == 0
                and int(kpis.get("graph_wires") or 0) > 0
            ),
            "evidence": {
                "graph_wires": int(kpis.get("graph_wires") or 0),
                "graph_ambiguous": int(kpis.get("graph_ambiguous") or 0),
            },
        },
        {
            "id": "visual_conflicts_closed",
            "label": "No unresolved visual-to-graph conflicts",
            "passed": int(kpis.get("visual_conflicts") or 0) == 0,
            "evidence": int(kpis.get("visual_conflicts") or 0),
        },
    ]

    failed = [item for item in checks if not item["passed"]]
    if not failed:
        status = "ready_for_handover_review"
    elif len(failed) <= 2:
        status = "ready_with_open_items"
    else:
        status = "not_ready"

    return {
        "status": status,
        "checks": checks,
        "failed_checks": failed,
        "passed_count": len(checks) - len(failed),
        "total_count": len(checks),
        "note": (
            "This gate reflects recorded project data only. Client acceptance, "
            "commissioning evidence, contractual deliverables, and field verification "
            "must still be completed where required."
        ),
    }


def build_professional_project_report(
    snapshot: dict,
    *,
    period: str,
    anchor_date: date | None = None,
) -> dict:
    if period not in REPORT_TYPES:
        raise ValueError("period must be daily, weekly, monthly, or final")

    anchor = anchor_date or date.today()
    project = snapshot.get("project") or {}
    dashboard = build_project_dashboard(snapshot)
    rows, start, end = _period_entries(
        snapshot.get("progress_entries") or [],
        period,
        anchor,
    )
    latest = _latest_drawing(snapshot)
    qa = latest.get("qa") or {}
    graph = qa.get("connection_graph") or {}
    reconciliation = qa.get("visual_reconciliation") or {}
    findings = qa.get("findings") or []

    completed = _collect(rows, "completed")
    in_progress = _collect(rows, "in_progress")
    issues = _collect(rows, "issues")
    blockers = _collect(rows, "blockers")
    next_actions = _collect(rows, "next_actions")
    rooms = _collect(rows, "rooms")
    responsible = _collect(rows, "responsible_parties")

    high_findings = [
        item for item in findings
        if str(item.get("severity") or "").lower() == "high"
    ]
    review_findings = [
        item for item in findings
        if str(item.get("status") or "").upper() in {"REVIEW", "VERIFY"}
    ]

    title_map = {
        "daily": "Daily AV Project Report",
        "weekly": "Weekly AV Project Report",
        "monthly": "Monthly AV Project Report",
        "final": "Final AV Handover Report",
    }

    summary_parts = []
    if completed:
        summary_parts.append(f"{len(completed)} completed item(s) recorded")
    if issues:
        summary_parts.append(f"{len(issues)} issue(s) recorded")
    if blockers:
        summary_parts.append(f"{len(blockers)} blocker(s) recorded")
    if high_findings:
        summary_parts.append(
            f"{len(high_findings)} high-severity drawing QA finding(s) remain for review"
        )
    if not summary_parts:
        summary_parts.append("No progress or engineering exceptions were recorded for this report period")

    report = {
        "schema_version": 2,
        "report_type": period,
        "title": title_map[period],
        "project": {
            "id": project.get("id"),
            "name": project.get("name"),
            "client": project.get("client"),
            "location": project.get("location"),
            "opportunity_number": project.get("opportunity_number"),
            "phase": project.get("phase"),
            "status": project.get("status"),
        },
        "period": {
            "anchor_date": anchor.isoformat(),
            "date_from": start.isoformat() if start else None,
            "date_to": end.isoformat() if end else None,
            "entries_count": len(rows),
        },
        "executive_summary": {
            "project_health": dashboard.get("health"),
            "phase": dashboard.get("phase"),
            "summary": ". ".join(summary_parts) + ".",
        },
        "progress": {
            "rooms_areas": rooms,
            "completed": completed,
            "in_progress": in_progress,
            "issues_snags": issues,
            "blockers_dependencies": blockers,
            "next_actions": next_actions,
            "responsible_parties": responsible,
            "entries": rows,
        },
        "engineering_review": {
            "latest_drawing": {
                "file_name": latest.get("file_name"),
                "page_count": latest.get("page_count"),
                "created_at": latest.get("created_at"),
            } if latest else None,
            "finding_count": len(findings),
            "high_findings": high_findings[:20],
            "review_findings": review_findings[:30],
            "connection_graph": {
                "devices": int(graph.get("node_count") or 0),
                "wires": int(graph.get("edge_count") or 0),
                "resolved": int(graph.get("resolved_edge_count") or 0),
                "ambiguous": int(graph.get("ambiguous_edge_count") or 0),
                "resolution_percent": round(
                    float(graph.get("resolution_rate") or 0.0) * 100
                ),
            },
            "visual_reconciliation": {
                "confirmed": int(reconciliation.get("confirmed_count") or 0),
                "conflicts": int(reconciliation.get("conflict_count") or 0),
                "no_visual_match": int(
                    reconciliation.get("no_visual_match_count") or 0
                ),
                "visual_only": int(reconciliation.get("visual_only_count") or 0),
            },
        },
        "management_summary": {
            "dashboard_kpis": dashboard.get("kpis") or {},
            "priority_blockers": (dashboard.get("priority") or {}).get("blockers") or [],
            "priority_issues": (dashboard.get("priority") or {}).get("issues") or [],
            "priority_next_actions": (dashboard.get("priority") or {}).get("next_actions") or [],
        },
        "handover_readiness": (
            _handover_gate(snapshot, dashboard)
            if period == "final"
            else None
        ),
        "quality_statement": (
            "Engineering findings are generated from recorded project information, "
            "drawing extraction, and available visual review. REVIEW/VERIFY items "
            "must be confirmed against approved drawings, manufacturer documentation, "
            "site conditions, and commissioning evidence before final closure."
        ),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    report["markdown"] = render_professional_report_markdown(report)
    return report


def _bullets(items: list[str], empty_text: str = "No recorded items.") -> list[str]:
    if not items:
        return [f"- {empty_text}"]
    return [f"- {item}" for item in items]


def render_professional_report_markdown(report: dict) -> str:
    project = report.get("project") or {}
    period = report.get("period") or {}
    progress = report.get("progress") or {}
    engineering = report.get("engineering_review") or {}
    graph = engineering.get("connection_graph") or {}
    visual = engineering.get("visual_reconciliation") or {}

    lines = [
        f"# {report.get('title') or 'AV Project Report'}",
        "",
        f"**Project:** {project.get('name') or 'Not recorded'}",
        f"**Client:** {project.get('client') or 'Not recorded'}",
        f"**Location:** {project.get('location') or 'Not recorded'}",
        f"**Phase:** {project.get('phase') or 'Not recorded'}",
    ]

    if period.get("date_from") or period.get("date_to"):
        lines.append(
            f"**Period:** {period.get('date_from') or '-'} to {period.get('date_to') or '-'}"
        )

    lines += [
        "",
        "## Executive Summary",
        str((report.get("executive_summary") or {}).get("summary") or ""),
        "",
        "## Completed Work",
        *_bullets(progress.get("completed") or []),
        "",
        "## Work in Progress",
        *_bullets(progress.get("in_progress") or []),
        "",
        "## Issues / Snags",
        *_bullets(progress.get("issues_snags") or []),
        "",
        "## Blockers / Dependencies",
        *_bullets(progress.get("blockers_dependencies") or []),
        "",
        "## Next Actions",
        *_bullets(progress.get("next_actions") or []),
        "",
        "## Drawing & Engineering QA",
        (
            f"- Connection graph: {graph.get('resolved', 0)} resolved / "
            f"{graph.get('wires', 0)} total wires; "
            f"{graph.get('ambiguous', 0)} require verification."
        ),
        (
            f"- Visual reconciliation: {visual.get('confirmed', 0)} confirmed; "
            f"{visual.get('conflicts', 0)} conflict(s)."
        ),
        f"- High-severity findings: {len(engineering.get('high_findings') or [])}",
    ]

    for item in engineering.get("high_findings") or []:
        lines.append(f"  - {item.get('title') or 'Engineering finding'}")

    readiness = report.get("handover_readiness")
    if readiness:
        lines += [
            "",
            "## Handover Readiness",
            f"**Status:** {str(readiness.get('status') or '').replace('_', ' ').upper()}",
        ]
        for check in readiness.get("checks") or []:
            marker = "✓" if check.get("passed") else "✗"
            lines.append(f"- {marker} {check.get('label')}")

    lines += [
        "",
        "## Quality Note",
        str(report.get("quality_statement") or ""),
    ]
    return "\n".join(lines).strip()
