from __future__ import annotations

from datetime import datetime
from typing import Any

from project_engineer import PROJECT_PHASES


def _items(entries: list[dict], key: str) -> list[str]:
    output: list[str] = []
    seen = set()
    for entry in entries or []:
        for item in entry.get(key) or []:
            value = str(item or "").strip()
            marker = value.casefold()
            if value and marker not in seen:
                output.append(value)
                seen.add(marker)
    return output


def _latest_drawing(snapshot: dict) -> dict | None:
    drawings = snapshot.get("drawing_analyses") or []
    return drawings[0] if drawings else None


def _phase_progress(phase: str) -> dict:
    try:
        index = PROJECT_PHASES.index(phase)
    except ValueError:
        index = 0
    total = max(len(PROJECT_PHASES), 1)
    return {
        "phase_index": index,
        "phase_number": index + 1,
        "phase_count": total,
        "phase_progress_percent": round((index / max(total - 1, 1)) * 100),
        "current_phase": phase,
        "next_phase": PROJECT_PHASES[index + 1] if index + 1 < total else None,
    }


def build_project_dashboard(snapshot: dict) -> dict:
    project = snapshot.get("project") or {}
    entries = snapshot.get("progress_entries") or []
    reports = snapshot.get("reports") or []
    latest = _latest_drawing(snapshot)
    qa = (latest or {}).get("qa") or {}
    graph = qa.get("connection_graph") or {}
    reconciliation = qa.get("visual_reconciliation") or {}

    findings = qa.get("findings") or []
    high_findings = [
        item for item in findings
        if str(item.get("severity") or "").lower() == "high"
    ]
    review_findings = [
        item for item in findings
        if str(item.get("status") or "").upper() in {"REVIEW", "VERIFY"}
    ]

    issues = _items(entries, "issues")
    blockers = _items(entries, "blockers")
    next_actions = _items(entries, "next_actions")
    completed = _items(entries, "completed")

    last_entry = entries[-1] if entries else None
    last_update = None
    if last_entry:
        last_update = {
            "date": last_entry.get("date"),
            "phase": last_entry.get("phase"),
            "completed": last_entry.get("completed") or [],
            "issues": last_entry.get("issues") or [],
            "blockers": last_entry.get("blockers") or [],
            "next_actions": last_entry.get("next_actions") or [],
        }

    phase = project.get("phase") or PROJECT_PHASES[0]
    phase_info = _phase_progress(phase)

    if high_findings:
        health = "engineering_review_required"
    elif blockers:
        health = "blocked"
    elif review_findings:
        health = "verification_required"
    elif not latest:
        health = "drawing_review_required"
    else:
        health = "on_track"

    graph_resolution = float(graph.get("resolution_rate") or 0.0)
    visual_reviewed = (
        int(reconciliation.get("confirmed_count") or 0)
        + int(reconciliation.get("conflict_count") or 0)
    )

    return {
        "project": {
            "id": project.get("id"),
            "name": project.get("name"),
            "location": project.get("location"),
            "client": project.get("client"),
            "status": project.get("status"),
        },
        "health": health,
        "phase": phase_info,
        "kpis": {
            "drawing_sets": len(snapshot.get("drawing_analyses") or []),
            "progress_updates": len(entries),
            "reports_generated": len(reports),
            "completed_items": len(completed),
            "open_issues": len(issues),
            "open_blockers": len(blockers),
            "qa_findings": len(findings),
            "high_findings": len(high_findings),
            "graph_devices": int(graph.get("node_count") or 0),
            "graph_wires": int(graph.get("edge_count") or 0),
            "graph_resolved": int(graph.get("resolved_edge_count") or 0),
            "graph_ambiguous": int(graph.get("ambiguous_edge_count") or 0),
            "graph_resolution_percent": round(graph_resolution * 100),
            "visual_confirmed_connections": int(
                reconciliation.get("confirmed_count") or 0
            ),
            "visual_conflicts": int(reconciliation.get("conflict_count") or 0),
            "visual_reviewed_connections": visual_reviewed,
        },
        "priority": {
            "blockers": blockers[:10],
            "issues": issues[:10],
            "high_findings": high_findings[:10],
            "next_actions": next_actions[:10],
        },
        "latest_update": last_update,
        "latest_drawing": {
            "id": (latest or {}).get("id"),
            "file_name": (latest or {}).get("file_name"),
            "page_count": (latest or {}).get("page_count"),
            "created_at": (latest or {}).get("created_at"),
        } if latest else None,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
