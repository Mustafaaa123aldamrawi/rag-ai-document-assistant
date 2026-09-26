from __future__ import annotations

from typing import Any

from project_engineer import PROJECT_PHASES


PHASE_PLAYBOOK = {
    "Design Review / Pre-Start": {
        "objective": "Confirm the design package is coordinated and buildable before site work starts.",
        "tasks": [
            "Confirm the latest approved AV drawing revision and drawing register.",
            "Cross-check floor plans, ceiling plans, containment, elevations, and signal-flow sheets.",
            "Verify equipment models, quantities, device IDs, and major signal paths.",
            "Confirm power, data, containment, backing, cooling, and structural dependencies by responsible party.",
            "Raise RFIs/technical queries for unresolved TBD/VIF/conflicting items.",
        ],
        "exit_criteria": [
            "Current drawing revision confirmed.",
            "Critical design conflicts closed or formally accepted.",
            "First-fix dependencies issued to MEP/IT/architectural teams.",
            "Procurement and installation scope aligned with approved design.",
        ],
    },
    "First Fix": {
        "objective": "Prepare all infrastructure required before AV devices are installed.",
        "tasks": [
            "Verify containment routes, conduit sizes, pull boxes, floor boxes, and back boxes against drawings.",
            "Verify AV power, data outlets, network provisions, backing, and ceiling hardpoints.",
            "Pull, label, and test AV cabling in accordance with drawing IDs and cable schedule.",
            "Maintain service loops and cable separation/bend-radius requirements.",
            "Redline every site deviation for as-built documentation.",
        ],
        "exit_criteria": [
            "Containment accessible and complete for affected systems.",
            "Required power/data/backing/hardpoints are present and verified.",
            "Cables are labeled, tested, and traceable to the signal-flow drawings.",
            "Open first-fix snags are documented with owners and dates.",
        ],
    },
    "Second Fix / Device Installation": {
        "objective": "Install, terminate, identify, and physically verify all AV equipment.",
        "tasks": [
            "Install devices at the locations and heights shown on coordinated drawings.",
            "Terminate and label all field cabling and equipment-side connections.",
            "Verify device IDs, model numbers, mounting hardware, ventilation, and safety supports.",
            "Build and dress racks with power, network, and cable management.",
            "Record serial numbers, MAC addresses, firmware versions, and installed locations where available.",
        ],
        "exit_criteria": [
            "Installed device quantity matches approved scope or documented redlines.",
            "All terminations are labeled and visually checked.",
            "Rack/device power-up is safe and complete.",
            "Installation snags are recorded before programming starts.",
        ],
    },
    "Configuration / Programming": {
        "objective": "Configure AV, DSP, switching, control, UC, networked media, and room logic.",
        "tasks": [
            "Confirm actual installed model/firmware before loading project-specific configuration.",
            "Configure AV routing, USB paths, DSP/audio paths, control interfaces, and room-combine logic.",
            "Configure vendor-specific devices with approved IP/VLAN/network parameters.",
            "Validate partition logic, presets, UI behavior, source naming, and fail-safe states.",
            "Back up configuration files and record software/firmware versions.",
        ],
        "exit_criteria": [
            "All required devices are reachable and configured.",
            "Control/UI logic matches approved functional requirements.",
            "Audio/video/USB/network paths are operational end-to-end.",
            "Configuration backups are stored with project records.",
        ],
    },
    "Testing / Commissioning": {
        "objective": "Prove every system path and user workflow against the design and acceptance criteria.",
        "tasks": [
            "Test each source-to-destination signal path and document failures.",
            "Commission audio gain structure, AEC, automix, routing, loudspeaker zones, and microphone coverage.",
            "Verify camera framing, display behavior, content scaling, USB/BYOD, and UC operation.",
            "Verify networked AV subscriptions, clocking, VLAN/QoS/IGMP requirements where applicable.",
            "Run room-combine/separate and recovery tests for divisible spaces.",
        ],
        "exit_criteria": [
            "Commissioning checklist complete with evidence.",
            "Critical functional defects closed.",
            "Remaining non-critical snags have owners and target dates.",
            "System is stable enough for client training.",
        ],
    },
    "Client Training": {
        "objective": "Train the client on normal operation, recovery, and support escalation.",
        "tasks": [
            "Demonstrate normal meeting, presentation, BYOD, and room-control workflows.",
            "Demonstrate divisible-room operation where applicable.",
            "Explain approved basic recovery steps without exposing unsafe service functions.",
            "Record attendance, training date, and outstanding client questions.",
        ],
        "exit_criteria": [
            "Training completed with client acknowledgement.",
            "Outstanding questions assigned.",
            "Support/handover contacts confirmed.",
        ],
    },
    "Snag Closure": {
        "objective": "Close remaining defects and prove corrected operation.",
        "tasks": [
            "Maintain a single snag register with owner, priority, due date, and evidence.",
            "Retest every corrected item before marking it closed.",
            "Update redlines/as-builts for physical or configuration changes.",
            "Confirm replacement items, firmware/configuration changes, and final room status.",
        ],
        "exit_criteria": [
            "All critical/high-priority snags closed.",
            "Accepted residual items documented and approved.",
            "As-built changes captured.",
        ],
    },
    "Handover": {
        "objective": "Deliver a complete, supportable system and close the project formally.",
        "tasks": [
            "Issue final as-built drawings and approved configuration backups.",
            "Issue equipment schedules, serial/MAC records, test results, warranties, and manuals as applicable.",
            "Issue commissioning, snag-closure, training, and final project reports.",
            "Obtain client handover/sign-off and transition the system to support/maintenance.",
        ],
        "exit_criteria": [
            "Handover pack complete.",
            "Client sign-off received or documented outstanding acceptance items agreed.",
            "Support/maintenance ownership confirmed.",
            "Project status moved to completed.",
        ],
    },
}


def _latest_drawing(snapshot: dict) -> dict:
    drawings = snapshot.get("drawing_analyses") or []
    return drawings[0] if drawings else {}


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    output = []
    for item in items:
        value = " ".join(str(item or "").split()).strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            output.append(value)
    return output


def _finding_actions(drawing: dict) -> tuple[list[dict], list[str]]:
    qa = drawing.get("qa") or {}
    findings = qa.get("findings") or []
    priority_findings = []
    actions = []

    for finding in findings:
        if not isinstance(finding, dict):
            continue
        severity = str(finding.get("severity") or "review").lower()
        if severity not in {"high", "medium"}:
            continue
        priority_findings.append(
            {
                "severity": severity,
                "status": finding.get("status"),
                "category": finding.get("category"),
                "title": finding.get("title"),
                "recommended_action": finding.get("recommended_action"),
            }
        )
        action = str(finding.get("recommended_action") or "").strip()
        if action:
            actions.append(action)

    return priority_findings[:15], _dedupe(actions)[:15]


def _coordination_actions(drawing: dict) -> list[str]:
    register = drawing.get("register") or {}
    requirements = register.get("coordination_requirements") or []
    actions = []
    for item in requirements:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category") or "").strip()
        requirement = str(item.get("requirement") or "").strip()
        if category and requirement:
            actions.append(f"Verify {category}: {requirement}")
        elif requirement:
            actions.append(f"Verify coordination requirement: {requirement}")
    return _dedupe(actions)[:12]


def build_phase_engineering_plan(snapshot: dict[str, Any]) -> dict[str, Any]:
    project = snapshot.get("project") or {}
    phase = str(project.get("phase") or PROJECT_PHASES[0])
    if phase not in PHASE_PLAYBOOK:
        phase = PROJECT_PHASES[0]

    playbook = PHASE_PLAYBOOK[phase]
    drawing = _latest_drawing(snapshot)
    priority_findings, finding_actions = _finding_actions(drawing)
    coordination_actions = _coordination_actions(drawing)

    progress_entries = snapshot.get("progress_entries") or []
    blockers = []
    issues = []
    completed = []
    next_actions = []

    for entry in progress_entries[-10:]:
        if not isinstance(entry, dict):
            continue
        blockers.extend(entry.get("blockers") or [])
        issues.extend(entry.get("issues") or [])
        completed.extend(entry.get("completed") or [])
        next_actions.extend(entry.get("next_actions") or [])

    combined_next = _dedupe(
        next_actions
        + finding_actions
        + coordination_actions
        + list(playbook["tasks"])
    )

    blocking_items = _dedupe(blockers)
    open_issues = _dedupe(issues)

    readiness = "ready_to_proceed"
    if any((str(item.get("severity") or "").lower() == "high") for item in priority_findings):
        readiness = "engineering_review_required"
    elif blocking_items:
        readiness = "blocked"
    elif not drawing and phase in {
        "First Fix",
        "Second Fix / Device Installation",
        "Configuration / Programming",
        "Testing / Commissioning",
    }:
        readiness = "drawing_review_required"

    current_index = PROJECT_PHASES.index(phase)
    next_phase = (
        PROJECT_PHASES[current_index + 1]
        if current_index + 1 < len(PROJECT_PHASES)
        else None
    )

    return {
        "project_id": project.get("id"),
        "project_name": project.get("name"),
        "phase": phase,
        "next_phase": next_phase,
        "readiness": readiness,
        "objective": playbook["objective"],
        "phase_tasks": list(playbook["tasks"]),
        "exit_criteria": list(playbook["exit_criteria"]),
        "priority_findings": priority_findings,
        "current_blockers": blocking_items[:15],
        "open_issues": open_issues[:15],
        "recent_completed": _dedupe(completed)[-15:],
        "recommended_next_actions": combined_next[:20],
        "drawing_context": {
            "available": bool(drawing),
            "file_name": drawing.get("file_name"),
            "page_count": drawing.get("page_count"),
            "finding_count": (drawing.get("qa") or {}).get("finding_count", 0),
        },
    }
