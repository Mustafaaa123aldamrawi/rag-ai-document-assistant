from __future__ import annotations

from copy import deepcopy
from typing import Any


SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "VERIFY": 3}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_confidence(value: Any) -> str:
    confidence = _clean_text(value).lower()
    if confidence not in {"high", "medium", "low"}:
        return "low"
    return confidence


def _normalized_key(value: Any) -> str:
    text = _clean_text(value).lower()
    return " ".join(
        token.strip(".,:;()[]{}")
        for token in text.split()
        if token.strip(".,:;()[]{}")
    )


def _uncertainty_is_actionable(value: Any) -> bool:
    text = _normalized_key(value)
    if not text:
        return False

    low_value_phrases = (
        "manufacturer is not readable",
        "manufacturer and model are not readable",
        "manufacturer/model",
        "model number is unreadable",
        "exact model",
        "exact manufacturer",
        "text is unreadable",
        "text is too blurry",
        "exact labels",
        "cannot be determined from the image",
        "cannot be confirmed from the image",
        "manufacturers and models cannot be determined",
        "manufacturer and model cannot be determined",
        "make/model",
        "make and model",
        "model number is not visible",
        "exact crestron model",
        "background flat-panel",
        "background flat panel",
        "function of the space",
        "space (meeting room",
        "space is not labeled",
        "purpose (decorative",
        "purpose is not visually confirmed",
        "power state of the background",
    )
    return not any(phrase in text for phrase in low_value_phrases)


def _is_critical_high_confidence_finding(finding: dict[str, Any]) -> bool:
    if _clean_text(finding.get("confidence")).upper() != "HIGH":
        return False

    text = " ".join(
        (
            _clean_text(finding.get("finding")),
            _clean_text(finding.get("basis")),
        )
    ).lower()

    critical_cues = (
        "safety",
        "unsafe",
        "exposed live",
        "electrical hazard",
        "fire",
        "water ingress",
        "smoke",
        "burn",
        "overheating",
        "blocked egress",
        "structural",
        "falling",
        "hanging loose overhead",
    )
    return any(cue in text for cue in critical_cues)


def _finding_status(issue_text: str, confidence: str, basis: str) -> str:
    probe = {
        "confidence": str(confidence or "").upper(),
        "finding": issue_text,
        "basis": basis,
    }
    if _is_critical_high_confidence_finding(probe):
        return "ACTION"
    if str(confidence or "").lower() in {"high", "medium"}:
        return "OBSERVATION"
    return "VERIFY"


def _scope_verification_status(survey_data: dict[str, Any]) -> str:
    if not isinstance(survey_data, dict):
        return ""

    statuses = []
    for section in survey_data.get("inspection_sections", []) or []:
        if not isinstance(section, dict):
            continue
        for item in section.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            status = _clean_text(item.get("status") or "VERIFY").upper()
            statuses.append(status)

    if any(status == "ACTION" for status in statuses):
        return "ACTION REQUIRED"
    if any(status == "VERIFY" for status in statuses):
        return "FIELD VERIFICATION REQUIRED"
    if any(status == "OBSERVATION" for status in statuses):
        return "REVIEW REQUIRED"
    if statuses and all(status in {"PASS", "N/A"} for status in statuses):
        return "READY FOR FINAL REVIEW"
    return ""


def derive_survey_status(
    survey_data: dict[str, Any] | None,
    inspection_summary: dict[str, Any],
) -> str:
    visual_meta = (
        inspection_summary.get("inspection_meta", {})
        if isinstance(inspection_summary, dict)
        else {}
    )
    visual_status = _clean_text(visual_meta.get("overall_status")) or "VERIFY"

    if not isinstance(survey_data, dict):
        return visual_status

    scope_status = _scope_verification_status(survey_data)

    visual_actions = int(visual_meta.get("actions") or 0)
    visual_observations = int(visual_meta.get("observations") or 0)
    visual_verify = int(visual_meta.get("verify_items") or 0)

    if visual_actions:
        return "ACTION REQUIRED"
    if scope_status == "ACTION REQUIRED":
        return "ACTION REQUIRED"
    if scope_status == "FIELD VERIFICATION REQUIRED":
        return "FIELD VERIFICATION REQUIRED"
    if visual_observations or scope_status == "REVIEW REQUIRED":
        return "REVIEW REQUIRED"
    if visual_verify:
        return "FIELD VERIFICATION REQUIRED"
    return scope_status or visual_status


def build_site_inspection_summary(
    visual_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Aggregate multiple visual-analysis results into one conservative
    AV/UC site-inspection package.

    visual_items items:
      {
        "file_name": "...",
        "analysis": {...},
      }
    """
    items = [
        item for item in (visual_items or [])
        if isinstance(item, dict)
        and isinstance(item.get("analysis"), dict)
    ]

    photo_register: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    verify_items: list[dict[str, Any]] = []

    issue_counter = 1
    verify_counter = 1
    seen_finding_keys: set[str] = set()
    seen_verify_keys: set[str] = set()

    for photo_index, item in enumerate(items, start=1):
        file_name = _clean_text(item.get("file_name")) or f"Photo {photo_index:02d}"
        analysis = item["analysis"]
        category = _clean_text(analysis.get("category")).upper() or "OTHER"
        summary = _clean_text(analysis.get("summary"))

        observations = [
            _clean_text(value)
            for value in analysis.get("observations", []) or []
            if _clean_text(value)
        ]
        uncertainties = [
            _clean_text(value)
            for value in analysis.get("uncertainties", []) or []
            if _clean_text(value)
        ]
        visible_text = [
            _clean_text(value)
            for value in analysis.get("visible_text", []) or []
            if _clean_text(value)
        ]

        photo_ref = f"P{photo_index:02d}"

        photo_register.append(
            {
                "photo_number": f"Photo {photo_index:02d}",
                "photo_ref": photo_ref,
                "file_name": file_name,
                "category": category,
                "subject_equipment": summary or (observations[0] if observations else ""),
                "location_direction": "",
                "finding_related_item": "",
                "status": "REVIEWED",
                "notes": "; ".join(observations[:2]),
                "visible_text": visible_text[:5],
            }
        )

        for issue in analysis.get("possible_issues", []) or []:
            if not isinstance(issue, dict):
                continue

            issue_text = _clean_text(issue.get("issue"))
            if not issue_text:
                continue

            confidence = _normalize_confidence(issue.get("confidence"))
            basis = _clean_text(issue.get("basis"))
            priority = {
                "high": "HIGH",
                "medium": "MEDIUM",
                "low": "LOW",
            }[confidence]
            finding_status = _finding_status(
                issue_text,
                confidence,
                basis,
            )

            finding_key = _normalized_key(issue_text)
            if finding_key in seen_finding_keys:
                continue
            seen_finding_keys.add(finding_key)

            findings.append(
                {
                    "id": f"F-{issue_counter:02d}",
                    "source_photo": file_name,
                    "source_photo_ref": photo_ref,
                    "category": category,
                    "finding": issue_text,
                    "basis": basis,
                    "confidence": confidence.upper(),
                    "priority": priority,
                    "status": finding_status,
                    "required_action": (
                        "Take immediate corrective / safety action and document closure."
                        if finding_status == "ACTION"
                        else (
                            "Verify the visible condition against the Scope and actual site state before treating it as a defect."
                            if finding_status == "OBSERVATION"
                            else "Verify on site before assigning a fault, root cause, or responsibility."
                        )
                    ),
                    "owner": "",
                    "closure_evidence": "",
                }
            )
            issue_counter += 1

        photo_verify_count = 0
        for uncertainty in uncertainties:
            if photo_verify_count >= 2:
                break
            if not _uncertainty_is_actionable(uncertainty):
                continue

            verify_key = _normalized_key(uncertainty)
            if verify_key in seen_verify_keys:
                continue
            seen_verify_keys.add(verify_key)

            verify_items.append(
                {
                    "id": f"V-{verify_counter:02d}",
                    "source_photo": file_name,
                    "source_photo_ref": photo_ref,
                    "item": uncertainty,
                    "status": "VERIFY",
                    "required_action": "Verify on site or through the relevant device/system interface.",
                    "owner": "",
                    "notes": "",
                }
            )
            verify_counter += 1
            photo_verify_count += 1

    findings.sort(
        key=lambda row: (
            SEVERITY_ORDER.get(_clean_text(row.get("priority")).upper(), 99),
            _clean_text(row.get("source_photo")).lower(),
            _clean_text(row.get("finding")).lower(),
        )
    )

    high_count = sum(
        1 for row in findings
        if _clean_text(row.get("priority")).upper() == "HIGH"
    )
    medium_count = sum(
        1 for row in findings
        if _clean_text(row.get("priority")).upper() == "MEDIUM"
    )

    action_count = sum(
        1 for row in findings
        if _clean_text(row.get("status")).upper() == "ACTION"
    )
    observation_count = sum(
        1 for row in findings
        if _clean_text(row.get("status")).upper() == "OBSERVATION"
    )

    if action_count:
        overall_status = "ACTION REQUIRED"
    elif observation_count:
        overall_status = "REVIEW REQUIRED"
    elif findings or verify_items:
        overall_status = "VERIFY"
    else:
        overall_status = "NO OBVIOUS VISUAL FAULT"

    if findings:
        summary_text = (
            f"{len(items)} photo(s) were reviewed. "
            f"{len(findings)} possible visual issue(s) were identified and require "
            "field verification before root cause or responsibility is assigned."
        )
    elif items:
        summary_text = (
            f"{len(items)} photo(s) were reviewed. No obvious visual fault was directly "
            "supported by the available images. Site verification is still required for "
            "items that cannot be confirmed visually."
        )
    else:
        summary_text = "No site photos were available for visual inspection."

    return {
        "inspection_meta": {
            "title": "AV/UC Site Inspection",
            "inspection_type": "Multi-Image Visual Inspection",
            "overall_status": overall_status,
            "visual_status": overall_status,
            "photos_reviewed": len(items),
            "possible_issues": len(findings),
            "observations": observation_count,
            "actions": action_count,
            "verify_items": len(verify_items),
        },
        "executive_summary": summary_text,
        "photo_register": photo_register,
        "visual_findings": findings,
        "verification_items": verify_items,
    }


def build_inspection_only_survey_data(
    inspection_summary: dict[str, Any],
) -> dict[str, Any]:
    """Build a report/checklist-compatible structure when no Scope of Work exists."""
    summary = inspection_summary if isinstance(inspection_summary, dict) else {}
    meta = summary.get("inspection_meta") or {}

    checklist_items = []

    for finding in summary.get("visual_findings", []) or []:
        if not isinstance(finding, dict):
            continue
        checklist_items.append(
            {
                "item": _clean_text(finding.get("finding")),
                "status": _clean_text(finding.get("status")) or "VERIFY",
                "notes": (
                    f"Source: {_clean_text(finding.get('source_photo_ref') or finding.get('source_photo'))}. "
                    f"Basis: {_clean_text(finding.get('basis'))}"
                ).strip(),
                "photo_ref": _clean_text(finding.get("source_photo_ref") or finding.get("source_photo")),
            }
        )

    for verify_item in summary.get("verification_items", []) or []:
        if not isinstance(verify_item, dict):
            continue
        checklist_items.append(
            {
                "item": _clean_text(verify_item.get("item")),
                "status": "VERIFY",
                "notes": f"Source: {_clean_text(verify_item.get('source_photo_ref') or verify_item.get('source_photo'))}",
                "photo_ref": _clean_text(verify_item.get("source_photo_ref") or verify_item.get("source_photo")),
            }
        )

    if not checklist_items and meta.get("photos_reviewed"):
        checklist_items.append(
            {
                "item": "Confirm site condition against the intended AV/UC operational state.",
                "status": "VERIFY",
                "notes": "No obvious visual fault was identified from the uploaded photos.",
                "photo_ref": "",
            }
        )

    return {
        "scope_available": False,
        "survey_status": _clean_text(meta.get("overall_status")) or "VERIFY",
        "visual_status": _clean_text(meta.get("visual_status") or meta.get("overall_status")) or "VERIFY",
        "document_meta": {
            "title": "AV/UC Site Inspection Checklist",
            "subtitle": "Multi-Image Visual Inspection",
            "purpose": (
                "Organize field verification using evidence extracted from uploaded site "
                "photos without assuming unobserved site conditions."
            ),
        },
        "project_info": {
            "project_name": "AV/UC Site Inspection",
            "client": "",
            "site": "",
            "location": "",
            "rooms": [],
            "drawing_references": [],
        },
        "rooms_areas": [],
        "checklist_sections": [
            {
                "section": "Visual Findings / Verification",
                "items": checklist_items,
            }
        ],
        "required_photos": [],
        "open_items": [
            _clean_text(item.get("item"))
            for item in summary.get("verification_items", []) or []
            if isinstance(item, dict) and _clean_text(item.get("item"))
        ],
        "photo_register": summary.get("photo_register") or [],
        "visual_inspection": summary,
        "inspection_meta": meta,
        "executive_summary": summary.get("executive_summary") or "",
        "visual_findings": summary.get("visual_findings") or [],
        "verification_items": summary.get("verification_items") or [],
        "deviations_risks_actions": [],
    }


PHOTO_SCOPE_TERM_GROUPS = {
    "display": ("display", "flat panel", "screen", "monitor"),
    "camera": ("camera",),
    "scheduler": ("crestron", "scheduler", "scheduling", "touch panel", "tc10"),
    "rack": ("rack", "headend", "pdu", "power distribution"),
    "dsp": ("dsp", "biamp", "tesira"),
    "amplifier": ("amplifier", "amp", "netpa"),
    "codec": ("codec", "poly", "g62", "vtc"),
    "switcher": ("switcher", "sw-01"),
    "extender": ("extender", "receiver", "transmitter", "rx-01", "wrx-01"),
    "microphone": ("microphone", "mic", "array microphone"),
    "speaker": ("speaker", "loudspeaker"),
    "ceiling": ("ceiling", "above-ceiling", "above ceiling", "plenum"),
    "partition": ("partition", "divisible", "combined room", "room-combining"),
    "cable": ("cable", "pathway", "containment", "conduit", "hdmi", "usb"),
    "dante": ("dante",),
    "room": ("meeting room", "conference room", "room-1", "room-2"),
}


def _photo_scope_tokens(text: Any) -> set[str]:
    normalized = _normalized_key(text)
    matched = set()
    for canonical, variants in PHOTO_SCOPE_TERM_GROUPS.items():
        if any(variant in normalized for variant in variants):
            matched.add(canonical)
    return matched


def _photo_search_text(photo: dict[str, Any]) -> str:
    return " ".join(
        _clean_text(photo.get(key))
        for key in (
            "subject_equipment",
            "notes",
            "visible_text",
            "category",
        )
        if _clean_text(photo.get(key))
    )


def _link_photo_refs_to_scope(merged: dict[str, Any]) -> None:
    photos = [
        photo for photo in merged.get("photo_register", []) or []
        if isinstance(photo, dict)
    ]
    if not photos:
        return

    photo_tokens = []
    for photo in photos:
        text = _photo_search_text(photo)
        photo_tokens.append(
            (
                _clean_text(photo.get("photo_ref")),
                _photo_scope_tokens(text),
                _normalized_key(text),
            )
        )

    for section in merged.get("inspection_sections", []) or []:
        if not isinstance(section, dict):
            continue
        section_text = _clean_text(
            section.get("section_title") or section.get("section")
        )
        for item in section.get("items", []) or []:
            if not isinstance(item, dict):
                continue

            item_text = " ".join(
                (
                    section_text,
                    _clean_text(item.get("inspection_item") or item.get("item")),
                )
            )
            item_tokens = _photo_scope_tokens(item_text)
            normalized_item = _normalized_key(item_text)

            scored = []
            for photo_ref, tokens, photo_text in photo_tokens:
                if not photo_ref:
                    continue
                overlap = len(item_tokens & tokens)
                exact_bonus = 0

                # Strong evidence terms should beat broad room/ceiling matches.
                for phrase in (
                    "crestron",
                    "tc10",
                    "rack",
                    "biamp",
                    "dsp",
                    "codec",
                    "poly",
                    "display",
                    "camera",
                    "ceiling",
                    "cable",
                    "partition",
                ):
                    if phrase in normalized_item and phrase in photo_text:
                        exact_bonus += 2

                score = overlap + exact_bonus
                if score >= 2:
                    scored.append((score, photo_ref))

            scored.sort(key=lambda pair: (-pair[0], pair[1]))
            refs = []
            for _, ref in scored:
                if ref not in refs:
                    refs.append(ref)
                if len(refs) >= 2:
                    break

            if refs:
                item["photo_ref"] = ", ".join(refs)


def merge_site_inspection_into_survey_data(
    survey_data: dict[str, Any] | None,
    inspection_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Merge visual evidence into existing Scope-derived survey data while
    preserving the original design/scope structure.
    """
    if not isinstance(survey_data, dict):
        return build_inspection_only_survey_data(inspection_summary)

    merged = deepcopy(survey_data)
    summary = inspection_summary if isinstance(inspection_summary, dict) else {}

    merged["scope_available"] = True
    merged["survey_status"] = derive_survey_status(merged, summary)
    merged["visual_status"] = _clean_text(
        (summary.get("inspection_meta") or {}).get("visual_status")
        or (summary.get("inspection_meta") or {}).get("overall_status")
    ) or "VERIFY"
    merged["visual_inspection"] = summary
    merged["inspection_meta"] = summary.get("inspection_meta") or {}
    merged["executive_summary"] = summary.get("executive_summary") or ""
    merged["visual_findings"] = summary.get("visual_findings") or []
    merged["verification_items"] = summary.get("verification_items") or []

    existing_photo_register = list(merged.get("photo_register") or [])
    visual_photo_register = list(summary.get("photo_register") or [])

    # Replace blank pre-survey photo rows only when real visual evidence exists.
    if visual_photo_register:
        non_blank_existing = []
        for row in existing_photo_register:
            if not isinstance(row, dict):
                continue
            meaningful = any(
                _clean_text(row.get(key))
                for key in (
                    "subject_equipment",
                    "photo_subject",
                    "location_direction",
                    "finding_related_item",
                    "notes",
                )
            )
            if meaningful:
                non_blank_existing.append(row)

        merged["photo_register"] = non_blank_existing + visual_photo_register

    _link_photo_refs_to_scope(merged)

    # Visual findings remain in dedicated visual_findings / verification_items
    # collections. They are intentionally NOT injected into the Scope-derived
    # checklist sections, preventing duplicate rows in client-facing documents.

    return merged
