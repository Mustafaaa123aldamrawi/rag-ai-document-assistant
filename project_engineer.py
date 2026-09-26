import json
import re
from datetime import date, datetime, timedelta


PROJECT_PHASES = (
    "Design Review / Pre-Start",
    "First Fix",
    "Second Fix / Device Installation",
    "Configuration / Programming",
    "Testing / Commissioning",
    "Client Training",
    "Snag Closure",
    "Handover",
)


SHEET_TYPE_PATTERNS = (
    ("responsibility_schedule", ("RESPONSIBILITY SCHEDULE",)),
    ("facility_requirements", ("FACILITY REQUIREMENT",)),
    ("cable_legend", ("CABLE LEGEND", "DEVICE ABBREVIATIONS")),
    ("wiring_pinout", ("WIRING PINOUT",)),
    ("scope_key_plan", ("SCOPE KEY PLAN",)),
    ("signal_flow", ("SIGNAL FLOW",)),
    ("containment", ("CONTAINMENT",)),
    ("ceiling_plan", ("CEILING PLAN",)),
    ("sightline", ("SIGHTLINE",)),
    ("elevation", ("ELEVATION",)),
    ("floor_plan", ("FLOOR PLAN",)),
    ("cover", ("COVER SHEET",)),
)


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _dedupe(values):
    output = []
    seen = set()
    for value in values:
        cleaned = _clean(value)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            output.append(cleaned)
            seen.add(key)
    return output


def classify_sheet_type(text):
    upper = _clean(text).upper()
    for sheet_type, patterns in SHEET_TYPE_PATTERNS:
        if any(pattern in upper for pattern in patterns):
            return sheet_type
    return "other"


def _best_sheet_title(text, drawing_number):
    lines = [_clean(line) for line in str(text or "").splitlines() if _clean(line)]
    drawing_number = _clean(drawing_number).upper()

    candidates = []
    for line in lines:
        upper = line.upper()
        if drawing_number and drawing_number in upper:
            continue
        if any(
            token in upper
            for token in (
                "PINSENT MASONS",
                "RIYADH KSA",
                "SHOP DRAWING",
                "DRAWING TITLE",
                "DATE REV",
                "OPPORTUNITY",
                "COPYRIGHT",
                "SCALE:",
                "PROJ ENG",
                "PROJ MGR",
                "PHONE:",
                "WWW.",
            )
        ):
            continue
        if (
            "FLOOR PLAN" in upper
            or "SIGNAL FLOW" in upper
            or "CEILING PLAN" in upper
            or "ELEVATION" in upper
            or "SIGHTLINE" in upper
            or "RESPONSIBILITY" in upper
            or "LEGEND" in upper
            or "PINOUT" in upper
            or "SCOPE KEY PLAN" in upper
            or "COVER SHEET" in upper
        ):
            candidates.append(line)

    if not candidates:
        return None

    candidates.sort(key=lambda item: (len(item) < 12, -len(item)))
    return candidates[0][:240]


def extract_sheet_register(document_pages):
    sheets = []
    seen = set()

    for page in document_pages or []:
        if not isinstance(page, dict):
            continue
        if page.get("is_drawing_analysis") or page.get("is_project_engineer_analysis"):
            continue

        text = str(page.get("text") or "")
        if not text.strip():
            continue

        page_number = page.get("page_number")
        source = page.get("source")

        matches = re.findall(r"\bAV[-\s]?(\d{3})\b", text, flags=re.I)
        normalized = [f"AV-{number}" for number in matches]

        # Prefer the sheet identity near the end/title block. If several AV
        # references exist (key plans and cross references), keep one register
        # entry for the page and choose the most frequently repeated number.
        drawing_number = None
        if normalized:
            counts = {}
            for item in normalized:
                counts[item] = counts.get(item, 0) + 1
            drawing_number = max(
                counts,
                key=lambda item: (counts[item], normalized.index(item)),
            )

        title = _best_sheet_title(text, drawing_number)

        key = (source, page_number)
        if key in seen:
            continue
        seen.add(key)

        sheets.append(
            {
                "page_number": page_number,
                "source": source,
                "drawing_number": drawing_number,
                "title": title,
                "sheet_type": classify_sheet_type(f"{title or ''}\n{text[:2500]}"),
            }
        )

    return sheets


def extract_project_identity(document_pages):
    combined = "\n".join(
        str(page.get("text") or "")
        for page in (document_pages or [])
        if isinstance(page, dict)
    )

    project_name = None
    if re.search(r"PINSENT\s+MASONS", combined, flags=re.I):
        project_name = "Pinsent Masons - Riyadh"

    opportunity = None
    match = re.search(r"\b390I-\d{2}-\d{5}\b", combined, flags=re.I)
    if match:
        opportunity = match.group(0).upper()

    location = None
    if re.search(r"RIYADH\s*,?\s*KSA", combined, flags=re.I):
        location = "Riyadh, KSA"

    return {
        "project_name": project_name,
        "opportunity_number": opportunity,
        "location": location,
    }


def extract_room_areas(document_pages):
    combined = "\n".join(
        str(page.get("text") or "")
        for page in (document_pages or [])
        if isinstance(page, dict)
    )

    rooms = []

    # L7 room labels are common in the supplied real drawing set.
    for match in re.finditer(
        r"\bL\d+-\d{2}\s+([A-Z][A-Z0-9 /&()_-]{2,60})",
        combined,
        flags=re.I,
    ):
        label = _clean(match.group(0))
        label = re.split(
            r"\b(?:TOP VIEW|FLOOR PLAN|AV-|DATE REV|FB\b)",
            label,
            maxsplit=1,
            flags=re.I,
        )[0]
        rooms.append(label)

    # Also preserve generic drawing titles that identify room archetypes.
    for match in re.finditer(
        r"\b(?:INTERNAL|EXTERNAL)?\s*\d+\s*PAX\s+MEETING\s+ROOM(?:\s*\([^\n]{1,80}\))?",
        combined,
        flags=re.I,
    ):
        rooms.append(_clean(match.group(0)))

    if re.search(r"DIVISIBLE\s+MEETING\s+ROOM", combined, flags=re.I):
        rooms.append("Divisible Meeting Room")

    return _dedupe(rooms)[:80]


def extract_coordination_requirements(document_pages):
    requirements = []
    combined = "\n".join(
        str(page.get("text") or "")
        for page in (document_pages or [])
        if isinstance(page, dict)
    )

    patterns = (
        (r"ALL REQUIRED BACKING[^\n]{0,260}", "Wall backing / structural support"),
        (r"ALL AC POWER[^\n]{0,260}", "AV power readiness"),
        (r"ALL REQUIRED CONDUIT[^\n]{0,260}", "Low-voltage containment"),
        (r"ALL HARDPOINTS[^\n]{0,260}", "Ceiling hardpoints / structural support"),
        (r"ALL REQUIRED NETWORK CONFIGURATION[^\n]{0,320}", "Network configuration"),
        (r"ALL ROUGH WIRE PULLS[^\n]{0,260}", "Cable labeling and testing"),
        (r"ANY SITE CHANGE[^\n]{0,260}", "Redline / as-built control"),
        (r"ROOMS?[^\n]{0,180}MUST BE DUST-FREE[^\n]{0,220}", "Site readiness"),
        (r"ALL ELECTRICAL POWER[^\n]{0,340}", "MEP/IT readiness"),
        (r"COORDINATION AND TIMELY IT SUPPORT[^\n]{0,260}", "IT coordination"),
    )

    for pattern, category in patterns:
        match = re.search(pattern, combined, flags=re.I)
        if match:
            requirements.append(
                {
                    "category": category,
                    "requirement": _clean(match.group(0)),
                }
            )

    return requirements


def detect_drawing_risk_flags(document_pages):
    flags = []
    for page in document_pages or []:
        if not isinstance(page, dict):
            continue
        text = str(page.get("text") or "")
        upper = text.upper()
        page_number = page.get("page_number")
        source = page.get("source")

        cues = (
            ("TBD", "TBD item requires closure"),
            ("VIF", "Verify-in-field item requires site confirmation"),
            ("NOT FOR CONSTRUCTION", "Drawing note states not for construction"),
            ("BY OTHERS", "Dependency on other contractor / discipline"),
            ("UNLESS OTHERWISE NOTED", "UNO dependency requires drawing-specific review"),
        )
        for cue, description in cues:
            if cue in upper:
                flags.append(
                    {
                        "page_number": page_number,
                        "source": source,
                        "type": cue,
                        "description": description,
                    }
                )

    # Collapse repeated generic cues so the brief remains useful.
    unique = []
    seen = set()
    for item in flags:
        key = (item["type"], item["page_number"])
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique[:80]


def build_lifecycle_plan(register):
    sheet_types = {
        sheet.get("sheet_type")
        for sheet in (register.get("sheets") or [])
    }

    first_fix = [
        "Review approved shop drawings, responsibilities, legends and latest revision before site work.",
        "Verify room readiness, access, wall/ceiling finishes, power, data, containment and structural supports.",
        "Coordinate floor/wall/ceiling boxes and containment routes against AV layouts and containment drawings.",
        "Pull, label and test AV cabling; maintain service loops and record redlines for site changes.",
    ]
    if "containment" in sheet_types:
        first_fix.append("Use the dedicated AV containment sheets as the first-fix routing reference.")
    if "ceiling_plan" in sheet_types:
        first_fix.append("Coordinate ceiling device locations before ceiling closure.")

    second_fix = [
        "Install AV devices only after first-fix checks and room readiness are complete.",
        "Verify display elevations, sightlines, mounting heights and service access before final fixing.",
        "Terminate and label cables to match drawing/device IDs and signal-flow references.",
    ]

    configuration = [
        "Complete device addressing, network/VLAN requirements and manufacturer configuration.",
        "Load control/DSP/UC programming and document final configuration values.",
    ]

    commissioning = [
        "Test every signal path end-to-end against the signal-flow drawings.",
        "Verify audio, video, USB, control, network and room-combine/divide behavior where applicable.",
        "Record faults, root cause, owner, corrective action and retest result.",
    ]

    handover = [
        "Close snags and verify all redlines are reflected in as-built documentation.",
        "Complete client training and capture attendance/sign-off.",
        "Compile test records, configuration backups, O&M/manuals, warranties, licenses and spare-parts status.",
        "Obtain final client acceptance and hand over to maintenance/support.",
    ]

    return [
        {"phase": PROJECT_PHASES[0], "actions": [
            "Confirm approved drawing revision and project scope.",
            "Build room-by-room scope and drawing register.",
            "Create coordination/RFI list for any missing, conflicting or VIF/TBD information.",
        ]},
        {"phase": PROJECT_PHASES[1], "actions": first_fix},
        {"phase": PROJECT_PHASES[2], "actions": second_fix},
        {"phase": PROJECT_PHASES[3], "actions": configuration},
        {"phase": PROJECT_PHASES[4], "actions": commissioning},
        {"phase": PROJECT_PHASES[5], "actions": [
            "Prepare room-operation training by room/system.",
            "Demonstrate normal operation, recovery and support/escalation procedure.",
        ]},
        {"phase": PROJECT_PHASES[6], "actions": [
            "Maintain one consolidated snag/action register.",
            "Retest every closed item and capture evidence before closure.",
        ]},
        {"phase": PROJECT_PHASES[7], "actions": handover},
    ]


def build_project_drawing_register(document_pages):
    sheets = extract_sheet_register(document_pages)
    identity = extract_project_identity(document_pages)
    rooms = extract_room_areas(document_pages)
    coordination = extract_coordination_requirements(document_pages)
    risk_flags = detect_drawing_risk_flags(document_pages)

    register = {
        "project": identity,
        "sheet_count": len(sheets),
        "sheets": sheets,
        "rooms": rooms,
        "coordination_requirements": coordination,
        "risk_flags": risk_flags,
    }
    register["lifecycle_plan"] = build_lifecycle_plan(register)
    return register


def build_project_engineer_analysis_page(register, source_name):
    if not register:
        return None
    return {
        "page_number": 0,
        "source": source_name,
        "text": json.dumps(register, ensure_ascii=False, indent=2),
        "has_extractable_text": True,
        "content_type": "PROJECT_ENGINEER",
        "is_project_engineer_analysis": True,
    }


def project_engineer_context(register, progress_log=None, max_chars=18000):
    if not isinstance(register, dict):
        return ""

    payload = {
        "project": register.get("project"),
        "sheet_count": register.get("sheet_count"),
        "sheets": register.get("sheets"),
        "rooms": register.get("rooms"),
        "coordination_requirements": register.get("coordination_requirements"),
        "risk_flags": register.get("risk_flags"),
        "lifecycle_plan": register.get("lifecycle_plan"),
        "progress_log": progress_log or [],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    return text[:max_chars]


def is_project_update_message(message):
    value = _clean(message).casefold()
    if not value:
        return False
    cues = (
        "today", "completed", "finished", "installed", "tested", "pending",
        "blocked", "issue", "snag", "first fix", "second fix", "handover",
        "commission", "اليوم", "خلصنا", "ركبنا", "سحبنا", "فحصنا", "تم",
        "معلق", "مشكلة", "مشاكل", "بندنج", "هاند اوفر", "تسليم",
    )
    return any(cue in value for cue in cues)


def normalize_progress_entry(entry):
    if not isinstance(entry, dict):
        return None

    normalized = {
        "date": _clean(entry.get("date")) or date.today().isoformat(),
        "phase": _clean(entry.get("phase")) or None,
        "rooms": _dedupe(entry.get("rooms") or []),
        "completed": _dedupe(entry.get("completed") or []),
        "in_progress": _dedupe(entry.get("in_progress") or []),
        "issues": _dedupe(entry.get("issues") or []),
        "blockers": _dedupe(entry.get("blockers") or []),
        "next_actions": _dedupe(entry.get("next_actions") or []),
        "responsible_parties": _dedupe(entry.get("responsible_parties") or []),
        "source_message": _clean(entry.get("source_message")),
    }
    return normalized


def report_window(period, anchor_date=None):
    anchor = anchor_date or date.today()
    if isinstance(anchor, datetime):
        anchor = anchor.date()
    if period == "daily":
        return anchor, anchor
    if period == "weekly":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    if period == "monthly":
        start = anchor.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1)
        else:
            next_month = start.replace(month=start.month + 1)
        return start, next_month - timedelta(days=1)
    raise ValueError("period must be daily, weekly, or monthly")


def _parse_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def build_progress_report(progress_log, period="daily", anchor_date=None, project=None):
    start, end = report_window(period, anchor_date)
    rows = []
    for raw in progress_log or []:
        entry = normalize_progress_entry(raw)
        if not entry:
            continue
        entry_date = _parse_date(entry["date"])
        if entry_date and start <= entry_date <= end:
            rows.append(entry)

    rows.sort(key=lambda item: item["date"])

    completed = _dedupe(
        item
        for row in rows
        for item in row.get("completed", [])
    )
    in_progress = _dedupe(
        item
        for row in rows
        for item in row.get("in_progress", [])
    )
    issues = _dedupe(
        item
        for row in rows
        for item in row.get("issues", [])
    )
    blockers = _dedupe(
        item
        for row in rows
        for item in row.get("blockers", [])
    )
    next_actions = _dedupe(
        item
        for row in rows
        for item in row.get("next_actions", [])
    )
    rooms = _dedupe(
        room
        for row in rows
        for room in row.get("rooms", [])
    )

    project = project or {}
    return {
        "period": period,
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "project_name": project.get("project_name"),
        "location": project.get("location"),
        "entries_count": len(rows),
        "rooms": rooms,
        "completed": completed,
        "in_progress": in_progress,
        "issues": issues,
        "blockers": blockers,
        "next_actions": next_actions,
        "entries": rows,
    }


def format_progress_report_markdown(report):
    title_map = {
        "daily": "Daily Project Report",
        "weekly": "Weekly Project Report",
        "monthly": "Monthly Project Report",
    }
    title = title_map.get(report.get("period"), "Project Report")
    lines = [f"# {title}"]
    if report.get("project_name"):
        lines.append(f"**Project:** {report['project_name']}")
    if report.get("location"):
        lines.append(f"**Location:** {report['location']}")
    lines.append(
        f"**Period:** {report.get('date_from')} to {report.get('date_to')}"
    )

    sections = (
        ("Rooms / Areas", report.get("rooms")),
        ("Completed Work", report.get("completed")),
        ("Work in Progress", report.get("in_progress")),
        ("Issues / Snags", report.get("issues")),
        ("Blockers / Dependencies", report.get("blockers")),
        ("Next Actions", report.get("next_actions")),
    )
    for heading, items in sections:
        lines.append(f"\n## {heading}")
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("- No recorded items.")

    return "\n".join(lines).strip()



def detect_report_period(message):
    value = _clean(message).casefold()
    if not value:
        return None

    daily = ("daily report", "day report", "تقرير يومي", "تقرير اليوم", "daily")
    weekly = ("weekly report", "week report", "تقرير أسبوعي", "تقرير اسبوعي", "weekly")
    monthly = ("monthly report", "month report", "تقرير شهري", "monthly")

    if any(cue in value for cue in daily):
        return "daily"
    if any(cue in value for cue in weekly):
        return "weekly"
    if any(cue in value for cue in monthly):
        return "monthly"
    return None


def is_project_engineer_question(message):
    value = _clean(message).casefold()
    cues = (
        "first fix", "second fix", "commission", "handover", "handing over",
        "project status", "project progress", "what should i start", "where do i start",
        "next step", "site readiness", "snag", "drawing set", "shop drawing",
        "daily report", "weekly report", "monthly report",
        "شو ابلش", "من وين ابلش", "شو الخطوة الجاية", "اول خطوة", "أول خطوة",
        "فيرست فكس", "سكند فكس", "كومشن", "تسليم", "هاند اوفر", "تقرير يومي",
        "تقرير أسبوعي", "تقرير اسبوعي", "تقرير شهري", "وضع المشروع", "بروجريس",
    )
    return any(cue in value for cue in cues)
