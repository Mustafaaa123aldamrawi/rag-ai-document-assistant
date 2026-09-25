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

        photo_register.append(
            {
                "photo_number": f"Photo {photo_index:02d}",
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
                "low": "VERIFY",
            }[confidence]

            finding_key = _normalized_key(issue_text)
            if finding_key in seen_finding_keys:
                continue
            seen_finding_keys.add(finding_key)

            findings.append(
                {
                    "id": f"F-{issue_counter:02d}",
                    "source_photo": file_name,
                    "category": category,
                    "finding": issue_text,
                    "basis": basis,
                    "confidence": confidence.upper(),
                    "priority": priority,
                    "status": "OPEN",
                    "required_action": (
                        "Verify the visible condition on site and trace the directly related "
                        "signal, power, network, control, or physical installation path before "
                        "assigning a root cause."
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

    critical_high_count = sum(
        1 for row in findings
        if _is_critical_high_confidence_finding(row)
    )

    if critical_high_count:
        overall_status = "HOLD / INVESTIGATE"
    elif high_count or medium_count:
        overall_status = "ACTION REQUIRED"
    elif findings:
        overall_status = "VERIFY"
    elif verify_items:
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
            "photos_reviewed": len(items),
            "possible_issues": len(findings),
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
                "status": "ACTION",
                "notes": (
                    f"Source: {_clean_text(finding.get('source_photo'))}. "
                    f"Basis: {_clean_text(finding.get('basis'))}"
                ).strip(),
                "photo_ref": _clean_text(finding.get("source_photo")),
            }
        )

    for verify_item in summary.get("verification_items", []) or []:
        if not isinstance(verify_item, dict):
            continue
        checklist_items.append(
            {
                "item": _clean_text(verify_item.get("item")),
                "status": "VERIFY",
                "notes": f"Source: {_clean_text(verify_item.get('source_photo'))}",
                "photo_ref": _clean_text(verify_item.get("source_photo")),
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

    # Visual findings remain in dedicated visual_findings / verification_items
    # collections. They are intentionally NOT injected into the Scope-derived
    # checklist sections, preventing duplicate rows in client-facing documents.

    return merged
