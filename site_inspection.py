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


def _content_terms(value: Any) -> set[str]:
    stopwords = {
        "about", "after", "against", "cannot", "could", "from", "have",
        "image", "into", "only", "photo", "requires", "site", "that",
        "their", "there", "these", "this", "through", "visible", "whether",
        "with", "without", "would", "verify", "verified", "verification",
    }
    return {
        token
        for token in _normalized_key(value).split()
        if len(token) >= 4 and token not in stopwords
    }


def _uncertainty_duplicates_finding(
    uncertainty: Any,
    photo_findings: list[dict[str, Any]],
) -> bool:
    uncertainty_text = _normalized_key(uncertainty)
    uncertainty_terms = _content_terms(uncertainty)
    if not uncertainty_terms:
        return False

    cable_terms = ("cable", "wire", "conductor")
    support_terms = (
        "hang",
        "hanging",
        "loose",
        "unsecured",
        "unsupported",
        "support",
        "suspension",
    )

    for finding in photo_findings:
        finding_text = _normalized_key(
            " ".join(
                (
                    _clean_text(finding.get("finding")),
                    _clean_text(finding.get("basis")),
                )
            )
        )
        finding_terms = _content_terms(finding_text)

        if len(uncertainty_terms & finding_terms) >= 2:
            return True

        # Concept-level duplicate: a cable/wire support uncertainty is the same
        # client-facing item as an existing loose/hanging cable observation,
        # even when one phrase says "hang" and the other says "unsupported".
        uncertainty_is_cable_support = (
            _contains_any(uncertainty_text, cable_terms)
            and _contains_any(uncertainty_text, support_terms)
        )
        finding_is_cable_support = (
            _contains_any(finding_text, cable_terms)
            and _contains_any(finding_text, support_terms)
        )
        if uncertainty_is_cable_support and finding_is_cable_support:
            return True

    return False


def _uncertainty_is_client_relevant(
    value: Any,
    photo_findings: list[dict[str, Any]],
) -> bool:
    """Keep only decision-relevant uncertainty in client-facing outputs."""
    text = _normalized_key(value)
    if not text:
        return False

    # If the uncertainty is already represented by a visible observation/finding,
    # keep the observation and its follow-up instead of duplicating it as VERIFY.
    if _uncertainty_duplicates_finding(value, photo_findings):
        return False

    generic_absence_phrases = (
        "not visible",
        "not legible",
        "not readable",
        "cannot be assessed",
        "cannot be verified",
        "cannot be confirmed",
        "cannot be determined",
        "cannot be identified",
        "not labeled",
        "not labelled",
        "unknown",
        "out of frame",
        "may be out of frame",
        "behind the wall",
        "behind wall",
        "behind the panel",
        "behind panel",
        "behind the devices",
        "behind devices",
        "rear cabling",
        "hidden wiring",
        "connections behind",
        "manufacturer",
        "model number",
        "make/model",
        "brand/model",
        "exact model",
        "exact manufacturer",
        "exact labels",
        "function of the space",
        "purpose is not",
        "power state",
        "device identity",
    )
    if any(phrase in text for phrase in generic_absence_phrases):
        return False

    # Keep only uncertainties that could materially change the disposition of a
    # visible condition or a safety/installation decision.
    material_cues = (
        "safety",
        "hazard",
        "live conductor",
        "energized",
        "structural",
        "water ingress",
        "overheating",
        "blocked",
        "clearance",
        "support",
        "secure",
        "load",
        "mount",
        "termination",
        "terminated",
        "damage",
    )
    return any(cue in text for cue in material_cues)



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

        photo_findings = [
            finding
            for finding in findings
            if finding.get("source_photo_ref") == photo_ref
        ]

        photo_verify_count = 0
        for uncertainty in uncertainties:
            if photo_verify_count >= 1:
                break
            if not _uncertainty_is_client_relevant(
                uncertainty,
                photo_findings,
            ):
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
            f"{len(findings)} visual observation(s) require field review before "
            "any defect, root cause, or responsibility is assigned."
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


def _photo_search_text(photo: dict[str, Any]) -> str:
    return _normalized_key(
        " ".join(
            _clean_text(photo.get(key))
            for key in (
                "subject_equipment",
                "notes",
                "visible_text",
                "category",
            )
            if _clean_text(photo.get(key))
        )
    )


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _photo_evidence_score(
    section_text: str,
    item_text: str,
    photo_text: str,
) -> int:
    """Conservative evidence matching: no broad manufacturer-only matches."""
    section = _normalized_key(section_text)
    item = _normalized_key(item_text)
    photo = _normalized_key(photo_text)
    probe = f"{section} {item}"

    # Exact/specific equipment must be directly visible in the photo analysis.
    if "poly studio g62" in probe or "g62" in probe:
        return 100 if "g62" in photo else 0

    if "poly tc10" in probe or "tc10" in probe:
        return 100 if "tc10" in photo else 0

    if "crestron room scheduling" in probe or "room scheduling touch panel" in probe:
        return 100 if (
            "crestron" in photo
            and _contains_any(photo, ("scheduler", "scheduling", "touch panel"))
        ) else 0

    if _contains_any(probe, ("audio dsp", "biamp", "tesira")):
        return 95 if _contains_any(photo, ("biamp", "tesira", "dsp-01", "audio dsp")) else 0

    if "dante amplifier" in probe:
        return 95 if "dante" in photo and _contains_any(photo, ("amplifier", "amp")) else 0

    if "amplifier" in probe:
        return 90 if _contains_any(photo, ("amplifier", "netpa", "pa-01")) else 0

    if "power distribution unit" in probe or " pdu " in f" {probe} ":
        return 90 if _contains_any(photo, ("power distribution", "pdu")) else 0

    if _contains_any(probe, ("slide out equipment rack", "rack capacity", "a/v rack", "av rack")):
        return 90 if "rack" in photo else 0

    if "high definition camera" in probe or "camera" in probe:
        return 90 if "camera" in photo else 0

    if _contains_any(probe, ("flat panel display", "flat-panel display", "displays")):
        if not _contains_any(photo, ("display", "flat-panel", "flat panel", "screen")):
            return 0
        # For dual-display claims, require the photo analysis to explicitly
        # indicate two/dual displays rather than merely one background screen.
        if _contains_any(probe, ("2 x", "dual", "two ")):
            return 95 if _contains_any(photo, ("two ", "2 ", "dual")) else 0
        return 80

    if _contains_any(probe, ("ceiling loudspeaker", "ceiling speaker", "loudspeakers")):
        return 90 if _contains_any(photo, ("ceiling speaker", "ceiling loudspeaker", "loudspeaker")) else 0

    if _contains_any(probe, ("array microphone", "ceiling mounted array microphone")):
        return 90 if _contains_any(photo, ("array microphone", "microphone", "mic")) else 0

    if "partition sensor" in probe:
        return 90 if _contains_any(photo, ("partition sensor", "partition")) else 0

    if _contains_any(probe, ("codec", "existing codec")):
        return 85 if _contains_any(photo, ("codec", "vtc-01")) else 0

    if "hdmi switcher" in probe or "switcher" in probe:
        return 85 if _contains_any(photo, ("switcher", "sw-01", "sw2 hd")) else 0

    if "scaler" in probe:
        return 85 if _contains_any(photo, ("scaler", "dsc")) else 0

    if "wireless presentation" in probe:
        return 85 if _contains_any(photo, ("wireless presentation", "wrx-01")) else 0

    if _contains_any(probe, ("video extender", "extender")):
        return 85 if _contains_any(photo, ("extender", "receiver", "transmitter", "rx-01", "wrx-01", "dtp")) else 0

    # Site-condition evidence: link only when the photo explicitly covers the
    # relevant physical condition.
    if _contains_any(probe, ("ceiling construction", "above-ceiling", "above ceiling")):
        return 80 if _contains_any(photo, ("ceiling", "plenum", "ductwork", "ceiling grid")) else 0

    if _contains_any(probe, ("cable pathways", "cable routes", "containment", "conduit")):
        return 80 if _contains_any(photo, ("cable", "pathway", "conduit", "plenum")) else 0

    if "dust-free" in probe or "finishes completely installed" in probe:
        return 75 if _contains_any(photo, ("debris", "ceiling grid", "construction material", "floor", "wall finish")) else 0

    return 0


def _link_photo_refs_to_scope(merged: dict[str, Any]) -> None:
    photos = [
        photo for photo in merged.get("photo_register", []) or []
        if isinstance(photo, dict)
    ]
    if not photos:
        return

    prepared_photos = [
        (
            _clean_text(photo.get("photo_ref")),
            _photo_search_text(photo),
        )
        for photo in photos
        if _clean_text(photo.get("photo_ref"))
    ]

    for section in merged.get("inspection_sections", []) or []:
        if not isinstance(section, dict):
            continue

        section_text = _clean_text(
            section.get("section_title") or section.get("section")
        )

        for item in section.get("items", []) or []:
            if not isinstance(item, dict):
                continue

            item_text = _clean_text(
                item.get("inspection_item") or item.get("item")
            )

            scored = []
            for photo_ref, photo_text in prepared_photos:
                score = _photo_evidence_score(
                    section_text,
                    item_text,
                    photo_text,
                )
                if score > 0:
                    scored.append((score, photo_ref))

            scored.sort(key=lambda pair: (-pair[0], pair[1]))
            if scored:
                # One strong evidence reference is preferable to multiple weak
                # references that could imply unsupported confirmation.
                item["photo_ref"] = scored[0][1]
            else:
                item["photo_ref"] = ""


def _build_deviation_action_rows(
    visual_findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for finding in visual_findings or []:
        if not isinstance(finding, dict):
            continue

        status = _clean_text(finding.get("status")).upper()
        if status not in {"OBSERVATION", "ACTION"}:
            continue

        priority = _clean_text(finding.get("priority")).upper() or "MEDIUM"
        if status == "ACTION":
            impact = "Potential safety / installation impact; immediate review required."
        else:
            impact = "Potential installation or site-readiness impact; confirm before classification."

        rows.append(
            {
                "id": _clean_text(finding.get("id")),
                "deviation_risk_missing_item": _clean_text(finding.get("finding")),
                "impact": impact,
                "required_action": _clean_text(finding.get("required_action")),
                "owner": "",
                "priority": priority,
                "photo_ref": _clean_text(finding.get("source_photo_ref")),
            }
        )
    return rows



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
    merged["deviations_risks_actions"] = _build_deviation_action_rows(
        merged["visual_findings"]
    )

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
