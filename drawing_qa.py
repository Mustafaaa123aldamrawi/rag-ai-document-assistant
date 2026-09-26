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
    r"\b(?:CAM|MON|MIC|SPK|TP|TB|TX|RX|VTC|DSP|NSW|OCS|WPR|AVR|PDU|UCE|PRJ|SCN|DEC|ENC|SW|CI|CU|DA|PA)-?\d{1,3}\b",
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

PORT_DIRECTION_PATTERNS = (
    ("out", re.compile(r"\b(?:OUT|OUTPUT|TX)\b", flags=re.I)),
    ("in", re.compile(r"\b(?:IN|INPUT|RX)\b", flags=re.I)),
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


def _media_family(tags: list[str]) -> str | None:
    upper = {tag.upper() for tag in tags}
    if "HDMI" in upper:
        return "video"
    if upper.intersection({"USB", "USB-A", "USB-B", "USB-C"}):
        return "usb"
    if upper.intersection({"RJ45", "DANTE", "AES67"}):
        return "network"
    if upper.intersection({"RS232", "RS-232", "GPIO", "CRESNET", "CNET"}):
        return "control"
    if upper.intersection({"XLR", "3.5S", "3.5RS", "TOS"}):
        return "audio"
    if upper.intersection({"DISPLAYPORT", "DP", "SDI"}):
        return "video"
    if upper.intersection({"LC", "SC", "ST"}):
        return "fiber"
    return None


def _infer_direction(text: str) -> str | None:
    upper = _clean(text).upper()
    hits = []
    for direction, pattern in PORT_DIRECTION_PATTERNS:
        if pattern.search(upper):
            hits.append(direction)
    if len(set(hits)) == 1:
        return hits[0]
    return None


def _nearest_device(lines: list[str], index: int, radius: int = 7) -> str | None:
    candidates: list[tuple[int, str]] = []
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    for j in range(start, end):
        for device in DEVICE_ID_RE.findall(lines[j]):
            candidates.append((abs(index - j), device.upper()))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _port_label(lines: list[str], index: int, radius: int = 2) -> str | None:
    candidates = []
    for j in range(max(0, index - radius), min(len(lines), index + radius + 1)):
        line = _clean(lines[j])
        upper = line.upper()
        if len(line) > 90:
            continue
        if WIRE_ID_RE.fullmatch(line):
            continue
        if any(token in upper for token in CONNECTOR_TOKENS) and (
            re.search(r"\b(?:IN|OUT|INPUT|OUTPUT|TX|RX|LAN|PORT|USB|HDMI)\b", upper)
            or any(token in upper for token in ("RJ45", "PHX", "DANTE", "CRESNET"))
        ):
            candidates.append((abs(index - j), line))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1][:120]


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


def extract_connection_endpoints(document_pages: list[dict]) -> list[dict]:
    """Extract conservative structured endpoint observations from drawing text.

    Endpoint observations are evidence records, not guaranteed physical truth.
    Visual confirmation remains required when text extraction is ambiguous.
    """
    endpoints: list[dict] = []
    seen = set()

    for page in document_pages or []:
        lines = _page_lines(page)
        for i, line in enumerate(lines):
            wires = WIRE_ID_RE.findall(line)
            if not wires:
                continue

            local_context = _context(lines, i, radius=4)
            device_id = _nearest_device(lines, i)
            port = _port_label(lines, i)
            connector_tags = _nearby_connector_tags(
                " | ".join(lines[max(0, i - 2): min(len(lines), i + 3)])
            )
            direction = _infer_direction(port or local_context)
            media = _media_family(connector_tags)

            for wire in wires:
                endpoint = {
                    "wire_id": wire.upper(),
                    "page_number": page.get("page_number"),
                    "source": page.get("source"),
                    "device_id": device_id,
                    "port": port,
                    "direction": direction,
                    "connector_tags": connector_tags,
                    "media_family": media,
                    "evidence": local_context[:900],
                }
                key = (
                    endpoint["wire_id"],
                    endpoint["page_number"],
                    endpoint["device_id"],
                    endpoint["port"],
                    endpoint["direction"],
                )
                if key in seen:
                    continue
                seen.add(key)
                endpoints.append(endpoint)

    return endpoints


def build_connection_graph(document_pages: list[dict]) -> dict:
    endpoints = extract_connection_endpoints(document_pages)
    by_wire: dict[str, list[dict]] = defaultdict(list)
    nodes: set[str] = set()

    for endpoint in endpoints:
        by_wire[endpoint["wire_id"]].append(endpoint)
        if endpoint.get("device_id"):
            nodes.add(endpoint["device_id"])

    edges = []
    resolved = 0
    ambiguous = 0

    for wire_id, observations in sorted(by_wire.items()):
        output_eps = [ep for ep in observations if ep.get("direction") == "out"]
        input_eps = [ep for ep in observations if ep.get("direction") == "in"]

        source = output_eps[0] if len(output_eps) == 1 else None
        destination = input_eps[0] if len(input_eps) == 1 else None

        status = "resolved" if source and destination else "ambiguous"
        if status == "resolved":
            resolved += 1
        else:
            ambiguous += 1

        edges.append(
            {
                "wire_id": wire_id,
                "status": status,
                "source": source,
                "destination": destination,
                "observations": observations,
                "observation_count": len(observations),
            }
        )

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "resolved_edge_count": resolved,
        "ambiguous_edge_count": ambiguous,
        "nodes": sorted(nodes),
        "edges": edges,
    }


def extract_connection_index(document_pages: list[dict]) -> dict:
    graph = build_connection_graph(document_pages)
    wires: dict[str, list[dict]] = defaultdict(list)

    for edge in graph["edges"]:
        for endpoint in edge["observations"]:
            wires[edge["wire_id"]].append(
                {
                    "page_number": endpoint.get("page_number"),
                    "source": endpoint.get("source"),
                    "devices": [endpoint["device_id"]] if endpoint.get("device_id") else [],
                    "connector_tags": endpoint.get("connector_tags") or [],
                    "port": endpoint.get("port"),
                    "direction": endpoint.get("direction"),
                    "media_family": endpoint.get("media_family"),
                    "evidence": endpoint.get("evidence"),
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


def _graph_findings(connection_graph: dict) -> list[dict]:
    findings = []

    for edge in connection_graph.get("edges") or []:
        wire_id = edge["wire_id"]
        observations = edge.get("observations") or []
        directions = [ep.get("direction") for ep in observations if ep.get("direction")]

        if len(observations) == 1:
            findings.append(
                {
                    "severity": "medium",
                    "status": "VERIFY",
                    "category": "single_ended_connection",
                    "title": f"{wire_id} appears only once in extracted signal-flow text",
                    "why_it_matters": "A one-sided wire reference can indicate an orphaned signal, a missing continuation, or incomplete text extraction.",
                    "recommended_action": "Open the referenced signal-flow page visually and confirm both source and destination before installation.",
                    "evidence": observations,
                }
            )
            continue

        if directions and all(direction == "out" for direction in directions):
            findings.append(
                {
                    "severity": "high",
                    "status": "REVIEW",
                    "category": "direction_conflict",
                    "title": f"{wire_id} appears connected output-to-output",
                    "why_it_matters": "A signal path normally requires a source output feeding a compatible destination input.",
                    "recommended_action": "Verify the two endpoint port labels visually. If both are outputs, correct the design before installation.",
                    "evidence": observations,
                }
            )
        elif directions and all(direction == "in" for direction in directions):
            findings.append(
                {
                    "severity": "high",
                    "status": "REVIEW",
                    "category": "direction_conflict",
                    "title": f"{wire_id} appears connected input-to-input",
                    "why_it_matters": "A signal path normally requires a source output feeding a compatible destination input.",
                    "recommended_action": "Verify the two endpoint port labels visually. If both are inputs, correct the design before installation.",
                    "evidence": observations,
                }
            )

        media = {ep.get("media_family") for ep in observations if ep.get("media_family")}
        if len(media) > 1:
            findings.append(
                {
                    "severity": "medium",
                    "status": "REVIEW",
                    "category": "connector_media_mismatch",
                    "title": f"{wire_id} crosses multiple media families: {', '.join(sorted(media))}",
                    "why_it_matters": "Different media families on the same wire reference can indicate a wrong port/cable callout or an undocumented converter/extender.",
                    "recommended_action": "Confirm the intended active conversion path and ensure the converter/extender is shown and scheduled.",
                    "evidence": observations,
                }
            )

        device_ids = {ep.get("device_id") for ep in observations if ep.get("device_id")}
        if len(device_ids) == 1 and len(observations) >= 2:
            findings.append(
                {
                    "severity": "medium",
                    "status": "VERIFY",
                    "category": "same_device_loop",
                    "title": f"{wire_id} resolves repeatedly near the same device",
                    "why_it_matters": "This can be a legitimate internal loop, but often indicates text extraction failed to capture the opposite endpoint.",
                    "recommended_action": "Confirm both physical endpoints on the signal-flow drawing before installation.",
                    "evidence": observations,
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
    connection_graph = build_connection_graph(document_pages)
    connections = extract_connection_index(document_pages)

    findings = []
    findings.extend(_device_model_conflicts(equipment))
    findings.extend(_graph_findings(connection_graph))
    findings.extend(_drawing_completeness_findings(document_pages))

    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda item: severity_order.get(item.get("severity"), 9))

    return {
        "equipment_mentions": equipment,
        "connection_index": connections,
        "connection_graph": connection_graph,
        "findings": findings,
        "finding_count": len(findings),
        "programming_requirements": build_programming_requirements(equipment),
        "disclaimer": (
            "Findings are engineering review candidates, not automatic as-built truth. "
            "Structured connection edges derived from extracted PDF text are marked resolved only when one output and one input are unambiguous. "
            "Items marked REVIEW/VERIFY still require visual drawing confirmation and, where applicable, field verification."
        ),
    }
