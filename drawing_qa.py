from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


VENDOR_PATTERNS = (
    "EXTRON",
    "CRESTRON",
    "Q-SYS",
    "QSC",
    "LIGHTWARE",
    "BIAMP",
    "BARCO",
    "SAMSUNG",
    "SONY",
    "POLY",
    "HP-POLY",
    "SHURE",
    "AUDINATE",
    "NETGEAR",
    "CISCO",
    "LG",
)

DEVICE_ID_RE = re.compile(
    r"\b(?:CAM|MON|MIC|SPK|TP|TB|TX|RX|VTC|DSP|NSW|OCS|WPR|AVR|PDU|UCE|PRJ|SCN|DEC|ENC)-?\d{1,3}\b",
    flags=re.I,
)
WIRE_ID_RE = re.compile(r"\b[ACDPV]\d{4}\b", flags=re.I)
DRAWING_RE = re.compile(r"\bAV-\d{3}\b", flags=re.I)

CONNECTOR_TOKENS = (
    "HDMI",
    "USB",
    "USB-A",
    "USB-B",
    "USB-C",
    "RJ45",
    "DANTE",
    "AES67",
    "PHX",
    "RS232",
    "RS-232",
    "GPIO",
    "CRESNET",
    "CNET",
    "DISPLAYPORT",
    "DP",
    "SDI",
    "XLR",
    "3.5S",
    "3.5RS",
    "TOS",
    "LC",
    "SC",
    "ST",
)

PROGRAMMING_HINTS = {
    "EXTRON": ("Control processor / switching / endpoint configuration", "Global Configurator / Global Scripter / device web UI"),
    "CRESTRON": ("Control, room-combine logic, touch UI, sensors, device integration", "SIMPL / SIMPL# / Crestron Construct / Toolbox as applicable"),
    "Q-SYS": ("DSP, control, UCI, room logic, audio/video routing", "Q-SYS Designer"),
    "QSC": ("DSP, control, UCI, room logic, audio/video routing", "Q-SYS Designer"),
    "LIGHTWARE": ("USB/AV switching, routing, USB-C/HDMI configuration and control", "Lightware Device Controller / REST or command API as applicable"),
    "BIAMP": ("DSP signal path, AEC, automix, gain structure, logic", "Tesira Software"),
    "BARCO": ("Video wall / presentation / processing configuration", "Barco device-specific software and API"),
    "SAMSUNG": ("Display / signage / video wall addressing and control", "Samsung MDC / MagicINFO / device API as applicable"),
    "SONY": ("Display configuration and control", "Display web UI / IP control as applicable"),
    "POLY": ("UC room device setup, peripherals, platform registration", "Poly Lens / device web UI"),
    "HP-POLY": ("UC room device setup, peripherals, platform registration", "Poly Lens / device web UI"),
    "SHURE": ("Dante, microphone coverage, DSP/channel routing, device presets", "Shure Designer"),
    "AUDINATE": ("Dante subscriptions, clocking, latency, multicast where required", "Dante Controller"),
    "NETGEAR": ("AV network VLAN/QoS/IGMP configuration", "NETGEAR AV UI / Engage"),
    "CISCO": ("Room device / UC configuration and network integration", "Cisco Control Hub / device web UI"),
    "LG": ("Display / video wall configuration and control", "LG SuperSign / device API as applicable"),
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _page_lines(page: dict) -> list[str]:
    return [_clean(x) for x in str(page.get("text") or "").splitlines() if _clean(x)]


def _context(lines: list[str], index: int, radius: int = 4) -> str:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    return " | ".join(lines[start:end])


def _nearby_connector_tags(text: str) -> list[str]:
    upper = text.upper().replace("_", " ")
    found = []
    for token in CONNECTOR_TOKENS:
        if token in upper and token not in found:
            found.append(token)
    return found


def extract_equipment_mentions(document_pages: list[dict]) -> list[dict]:
    mentions: list[dict] = []
    seen = set()

    for page in document_pages or []:
        lines = _page_lines(page)
        for i, line in enumerate(lines):
            upper = line.upper()
            vendor = next((v for v in VENDOR_PATTERNS if v in upper), None)
            if not vendor:
                continue

            nearby = _context(lines, i, radius=3)
            device_ids = DEVICE_ID_RE.findall(nearby)
            model = None

            # Prefer a short model-like line near the vendor name.
            candidates = lines[max(0, i - 2): min(len(lines), i + 4)]
            for candidate in candidates:
                cu = candidate.upper()
                if candidate == line:
                    continue
                if len(candidate) > 80:
                    continue
                if DEVICE_ID_RE.fullmatch(candidate):
                    continue
                if any(tok in cu for tok in ("DATE REV", "DRAWING", "PROJECT", "SCALE", "POWER", "LAN", "HDMI", "USB", "RJ45")):
                    continue
                if re.search(r"[A-Z]{1,8}[- ]?\d[A-Z0-9\-]{1,25}", cu):
                    model = candidate
                    break

            key = (page.get("page_number"), vendor, model, tuple(device_ids))
            if key in seen:
                continue
            seen.add(key)
            mentions.append(
                {
                    "page_number": page.get("page_number"),
                    "source": page.get("source"),
                    "vendor": vendor,
                    "model": model,
                    "device_ids": [d.upper() for d in device_ids],
                    "evidence": nearby[:700],
                }
            )

    return mentions


def extract_connection_index(document_pages: list[dict]) -> dict:
    wires: dict[str, list[dict]] = defaultdict(list)

    for page in document_pages or []:
        lines = _page_lines(page)
        for i, line in enumerate(lines):
            for wire in WIRE_ID_RE.findall(line):
                context = _context(lines, i, radius=5)
                devices = [d.upper() for d in DEVICE_ID_RE.findall(context)]
                wires[wire.upper()].append(
                    {
                        "page_number": page.get("page_number"),
                        "source": page.get("source"),
                        "devices": sorted(set(devices)),
                        "connector_tags": _nearby_connector_tags(context),
                        "evidence": context[:900],
                    }
                )

    return {
        "wire_count": len(wires),
        "wires": dict(sorted(wires.items())),
    }


def _device_model_conflicts(equipment_mentions: list[dict]) -> list[dict]:
    by_id: dict[str, list[dict]] = defaultdict(list)
    for mention in equipment_mentions:
        for device_id in mention.get("device_ids") or []:
            by_id[device_id].append(mention)

    findings = []
    for device_id, mentions in by_id.items():
        identities = {
            (
                _clean(m.get("vendor")).upper(),
                _clean(m.get("model")).upper(),
            )
            for m in mentions
            if _clean(m.get("vendor")) or _clean(m.get("model"))
        }
        if len(identities) <= 1:
            continue

        findings.append(
            {
                "severity": "high",
                "status": "REVIEW",
                "category": "device_identity_conflict",
                "title": f"Conflicting identity for {device_id}",
                "why_it_matters": "The same device ID appears associated with more than one vendor/model identity.",
                "recommended_action": "Verify the device schedule and signal-flow blocks, then correct the drawing so one device ID maps to one physical device.",
                "evidence": [
                    {
                        "page_number": m.get("page_number"),
                        "vendor": m.get("vendor"),
                        "model": m.get("model"),
                    }
                    for m in mentions[:8]
                ],
            }
        )
    return findings


def _wire_findings(connection_index: dict) -> list[dict]:
    findings = []
    for wire_id, occurrences in (connection_index.get("wires") or {}).items():
        if len(occurrences) == 1:
            findings.append(
                {
                    "severity": "medium",
                    "status": "VERIFY",
                    "category": "single_ended_connection",
                    "title": f"{wire_id} appears only once in extracted signal-flow text",
                    "why_it_matters": "A one-sided wire reference can indicate an orphaned signal, a missing continuation, or incomplete text extraction.",
                    "recommended_action": "Open the referenced signal-flow page visually and confirm both source and destination before installation.",
                    "evidence": occurrences,
                }
            )
            continue

        connector_sets = [set(o.get("connector_tags") or []) for o in occurrences if o.get("connector_tags")]
        if len(connector_sets) >= 2:
            common = set.intersection(*connector_sets) if connector_sets else set()
            union = set.union(*connector_sets) if connector_sets else set()
            major_media = {"HDMI", "USB", "RJ45", "DANTE", "RS232", "RS-232", "DISPLAYPORT", "DP", "SDI"}
            media_seen = union.intersection(major_media)
            if len(media_seen) > 1 and not common.intersection(media_seen):
                findings.append(
                    {
                        "severity": "medium",
                        "status": "REVIEW",
                        "category": "connector_media_mismatch",
                        "title": f"{wire_id} has inconsistent connector/media tags",
                        "why_it_matters": "The same wire reference is associated with different media/connector families in the extracted drawing text.",
                        "recommended_action": "Verify both endpoints visually and confirm whether an active converter/extender is intentionally present.",
                        "evidence": occurrences,
                    }
                )
    return findings


def _drawing_completeness_findings(document_pages: list[dict]) -> list[dict]:
    combined = "\n".join(str(p.get("text") or "") for p in document_pages or [])
    upper = combined.upper()
    findings = []

    required_pairs = (
        ("FLOOR PLAN", "SIGNAL FLOW", "Floor-plan information exists but no signal-flow sheet was detected."),
        ("DIVISIBLE MEETING ROOM", "PARTITION", "A divisible room is present but no partition reference was detected in extracted text."),
    )
    for anchor, required, message in required_pairs:
        if anchor in upper and required not in upper:
            findings.append(
                {
                    "severity": "high" if "DIVISIBLE" in anchor else "medium",
                    "status": "REVIEW",
                    "category": "drawing_set_completeness",
                    "title": message,
                    "why_it_matters": "Installation and commissioning depend on coordinated information across multiple drawing disciplines.",
                    "recommended_action": "Request or verify the missing coordinated drawing/detail before proceeding with affected work.",
                    "evidence": [],
                }
            )

    if "TBD" in upper:
        findings.append(
            {
                "severity": "medium",
                "status": "VERIFY",
                "category": "unresolved_design_information",
                "title": "TBD items are present in the drawing set",
                "why_it_matters": "Unresolved design information can create installation or procurement risk.",
                "recommended_action": "Create an RFI/technical query and close the TBD before the dependent installation activity.",
                "evidence": [],
            }
        )
    if "VIF" in upper or "VERIFY IN FIELD" in upper:
        findings.append(
            {
                "severity": "medium",
                "status": "VERIFY",
                "category": "field_verification_required",
                "title": "Field-verification requirements are present",
                "why_it_matters": "These items cannot be accepted from drawings alone.",
                "recommended_action": "Add them to the site-survey / first-fix checklist and record actual field values with evidence.",
                "evidence": [],
            }
        )
    return findings


def build_programming_requirements(equipment_mentions: list[dict]) -> list[dict]:
    vendors = sorted({str(m.get("vendor") or "").upper() for m in equipment_mentions if m.get("vendor")})
    output = []
    for vendor in vendors:
        hint = PROGRAMMING_HINTS.get(vendor)
        if not hint:
            continue
        models = sorted(
            {
                _clean(m.get("model"))
                for m in equipment_mentions
                if str(m.get("vendor") or "").upper() == vendor and _clean(m.get("model"))
            }
        )
        output.append(
            {
                "vendor": vendor,
                "models_detected": models[:20],
                "programming_scope": hint[0],
                "engineering_tool": hint[1],
                "status": "REQUIRES PROJECT-SPECIFIC VALIDATION",
            }
        )
    return output


def audit_drawing_set(document_pages: list[dict]) -> dict:
    equipment = extract_equipment_mentions(document_pages)
    connections = extract_connection_index(document_pages)

    findings = []
    findings.extend(_device_model_conflicts(equipment))
    findings.extend(_wire_findings(connections))
    findings.extend(_drawing_completeness_findings(document_pages))

    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda item: severity_order.get(item.get("severity"), 9))

    return {
        "equipment_mentions": equipment,
        "connection_index": connections,
        "findings": findings,
        "finding_count": len(findings),
        "programming_requirements": build_programming_requirements(equipment),
        "disclaimer": (
            "Findings are engineering review candidates, not automatic as-built truth. "
            "Items marked REVIEW/VERIFY require visual drawing confirmation and, where applicable, field verification."
        ),
    }
