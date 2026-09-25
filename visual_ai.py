from __future__ import annotations

import json
from typing import Any


VISUAL_CATEGORIES = {
    "SITE_PHOTO",
    "ERROR_SCREENSHOT",
    "AV_EQUIPMENT",
    "DRAWING_SNIPPET",
    "OTHER",
}


def build_visual_analysis_messages(
    *,
    file_name: str,
    image_data_url: str,
) -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": (
                "You are an AV/UC visual inspection assistant. Analyze only what is "
                "actually visible in the image. Never infer hidden wiring, device state, "
                "model numbers, fault causes, compliance, or installation quality unless "
                "the image provides direct evidence. Distinguish observation from inference."
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""
Analyze the uploaded image: {file_name}

Return STRICT JSON only with this schema:
{{
  "category": "SITE_PHOTO | ERROR_SCREENSHOT | AV_EQUIPMENT | DRAWING_SNIPPET | OTHER",
  "summary": "short factual visual summary",
  "visible_text": ["exact readable text only"],
  "devices": [
    {{
      "manufacturer": null,
      "model": null,
      "device_type": null,
      "visible_evidence": "what in the image supports this identification"
    }}
  ],
  "observations": ["directly visible factual observations"],
  "possible_issues": [
    {{
      "issue": "only if visually supported",
      "confidence": "high | medium | low",
      "basis": "visible evidence"
    }}
  ],
  "uncertainties": ["anything unclear, unreadable, obscured, or requiring site verification"]
}}

Rules:
- Do not guess model numbers from appearance alone.
- Do not claim a device is faulty merely because an LED is red unless a visible label/message supports that conclusion.
- Do not claim cables are connected behind equipment unless the connection is visible.
- For screenshots, transcribe exact error messages when readable.
- For site photos, note visible installation condition without assigning root cause unless directly evident.
- For drawing snippets, preserve exact room/device labels when readable.
- If text is unreadable, put that in uncertainties instead of inventing it.
- Use null when manufacturer/model/device type cannot be established visually.
""".strip(),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_url},
                },
            ],
        },
    ]


def parse_visual_analysis(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()

    try:
        data = json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Visual analysis did not return valid JSON.")
        data = json.loads(text[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("Visual analysis JSON must be an object.")

    category = str(data.get("category") or "OTHER").upper()
    if category not in VISUAL_CATEGORIES:
        category = "OTHER"
    data["category"] = category

    for key in ("visible_text", "devices", "observations", "possible_issues", "uncertainties"):
        if not isinstance(data.get(key), list):
            data[key] = []

    data["summary"] = str(data.get("summary") or "").strip()
    return data


def build_visual_evidence_text(
    analysis: dict[str, Any],
    *,
    file_name: str,
) -> str:
    lines = [
        f"VISUAL SOURCE: {file_name}",
        f"VISUAL CATEGORY: {analysis.get('category', 'OTHER')}",
        "IMPORTANT: The following evidence is AI-extracted from the visible image only. "
        "Critical details must be verified when the image is unclear.",
    ]

    summary = str(analysis.get("summary") or "").strip()
    if summary:
        lines.append(f"SUMMARY: {summary}")

    visible_text = [str(x).strip() for x in analysis.get("visible_text", []) if str(x).strip()]
    if visible_text:
        lines.append("VISIBLE TEXT:")
        lines.extend(f"- {item}" for item in visible_text)

    devices = analysis.get("devices", [])
    if devices:
        lines.append("VISIBLE DEVICES:")
        for item in devices:
            if not isinstance(item, dict):
                continue
            manufacturer = item.get("manufacturer") or "unknown manufacturer"
            model = item.get("model") or "unknown model"
            device_type = item.get("device_type") or "unknown device type"
            evidence = item.get("visible_evidence") or "visual appearance"
            lines.append(
                f"- {manufacturer} | {model} | {device_type} | evidence: {evidence}"
            )

    observations = [str(x).strip() for x in analysis.get("observations", []) if str(x).strip()]
    if observations:
        lines.append("DIRECT VISUAL OBSERVATIONS:")
        lines.extend(f"- {item}" for item in observations)

    issues = analysis.get("possible_issues", [])
    if issues:
        lines.append("POSSIBLE VISUAL ISSUES:")
        for item in issues:
            if not isinstance(item, dict):
                continue
            issue = str(item.get("issue") or "").strip()
            if not issue:
                continue
            confidence = str(item.get("confidence") or "low").strip()
            basis = str(item.get("basis") or "").strip()
            lines.append(f"- {issue} | confidence: {confidence} | basis: {basis}")

    uncertainties = [str(x).strip() for x in analysis.get("uncertainties", []) if str(x).strip()]
    if uncertainties:
        lines.append("UNCERTAINTIES / VERIFY:")
        lines.extend(f"- {item}" for item in uncertainties)

    return "\n".join(lines).strip()



def build_visual_diagnostic_plan(
    analysis: dict[str, Any],
    *,
    question: str = "",
) -> dict[str, Any]:
    """Create a deterministic AV field-inspection plan from visual evidence."""
    category = str(analysis.get("category") or "OTHER").upper()
    observations = [
        str(item).strip()
        for item in analysis.get("observations", [])
        if str(item).strip()
    ]
    uncertainties = [
        str(item).strip()
        for item in analysis.get("uncertainties", [])
        if str(item).strip()
    ]

    normalized_issues = []
    for item in analysis.get("possible_issues", []):
        if not isinstance(item, dict):
            continue
        issue = str(item.get("issue") or "").strip()
        if not issue:
            continue
        confidence = str(item.get("confidence") or "low").strip().lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"
        basis = str(item.get("basis") or "").strip()
        normalized_issues.append(
            {
                "issue": issue,
                "confidence": confidence,
                "basis": basis,
            }
        )

    confidence_rank = {"high": 0, "medium": 1, "low": 2}
    normalized_issues.sort(
        key=lambda item: confidence_rank.get(item["confidence"], 2)
    )

    supported_faults = [
        item
        for item in normalized_issues
        if item["confidence"] in {"high", "medium"}
    ]

    if supported_faults:
        visible_fault_status = "POSSIBLE_VISIBLE_FAULT"
        fault_summary = (
            "One or more possible visual issues are supported by the image evidence."
        )
    else:
        visible_fault_status = "NO_OBVIOUS_VISIBLE_FAULT"
        fault_summary = (
            "No obvious visual fault is directly supported by the image evidence."
        )

    category_checks = {
        "SITE_PHOTO": [
            "Confirm the displayed source/state is the intended operational state.",
            "Check image geometry, scaling, alignment, and cropping across the full display surface.",
            "Inspect visible seams, brightness, and color uniformity from a normal viewing position.",
            "Verify the signal source and output resolution/refresh rate against the display system requirements.",
            "Inspect mounting, ventilation, and any visible obstruction or physical damage only where accessible.",
        ],
        "ERROR_SCREENSHOT": [
            "Record the exact visible error message and timestamp before changing the system state.",
            "Confirm which source, endpoint, application, or signal path produced the error.",
            "Check the immediately related network, USB, HDMI, or control connection indicated by the error context.",
            "Reproduce the issue once after capturing the current state, if doing so is safe and non-disruptive.",
            "Compare the result with logs or device status before replacing hardware.",
        ],
        "AV_EQUIPMENT": [
            "Verify power, link/status indicators, and any readable front-panel messages.",
            "Confirm the visible cabling and connector seating without inferring hidden connections.",
            "Check the device role and signal path before changing configuration.",
            "Compare the observed state with the expected commissioning or design state.",
            "Record model/serial information only from readable labels or management interfaces.",
        ],
        "DRAWING_SNIPPET": [
            "Verify readable room, device, and cable labels against the latest issued drawing revision.",
            "Check quantities and locations only where the drawing explicitly shows them.",
            "Flag unreadable, conflicting, or missing labels as items requiring design confirmation.",
            "Do not infer hidden connections or equipment not shown in the drawing.",
        ],
        "OTHER": [
            "Confirm the intended system state before treating any visible condition as a fault.",
            "Check the most directly related signal, power, network, or control path.",
            "Record any visible error text, status indication, or physical anomaly before making changes.",
        ],
    }

    next_checks = list(category_checks.get(category, category_checks["OTHER"]))

    # Keep the action list concise and field-oriented.
    next_checks = next_checks[:5]

    return {
        "category": category,
        "visible_fault_status": visible_fault_status,
        "fault_summary": fault_summary,
        "observations": observations[:6],
        "possible_issues": normalized_issues[:5],
        "uncertainties": uncertainties[:5],
        "next_checks": next_checks,
        "question": str(question or "").strip(),
    }


def build_visual_diagnostic_context(
    analysis: dict[str, Any],
    *,
    question: str = "",
) -> str:
    plan = build_visual_diagnostic_plan(
        analysis,
        question=question,
    )

    lines = [
        "VISUAL DIAGNOSTIC PLAN",
        f"CATEGORY: {plan['category']}",
        f"VISIBLE FAULT STATUS: {plan['visible_fault_status']}",
        f"FAULT SUMMARY: {plan['fault_summary']}",
    ]

    if plan["observations"]:
        lines.append("PRIORITY OBSERVATIONS:")
        lines.extend(
            f"- {item}"
            for item in plan["observations"]
        )

    if plan["possible_issues"]:
        lines.append("SUPPORTED POSSIBLE ISSUES:")
        for item in plan["possible_issues"]:
            lines.append(
                f"- {item['issue']} | confidence: {item['confidence']} | "
                f"basis: {item['basis'] or 'visible evidence'}"
            )
    else:
        lines.append(
            "SUPPORTED POSSIBLE ISSUES: none identified with medium/high visual confidence."
        )

    if plan["uncertainties"]:
        lines.append("UNKNOWNS / VERIFY:")
        lines.extend(
            f"- {item}"
            for item in plan["uncertainties"]
        )

    lines.append("RECOMMENDED FIELD CHECKS:")
    lines.extend(
        f"- {item}"
        for item in plan["next_checks"]
    )

    lines.append(
        "IMPORTANT: Recommended field checks are diagnostic actions, not claims that a fault exists."
    )

    return "\n".join(lines).strip()



def visual_answer_is_complete(answer: str, question: str = "") -> bool:
    """Return True when a visual diagnostic answer covers the requested workflow."""
    text = str(answer or "").strip().lower()
    if not text:
        return False

    question_lower = str(question or "").lower()

    asks_what_visible = any(
        cue in question_lower
        for cue in ("what can you see", "what do you see", "what is visible")
    )
    asks_issue = any(
        cue in question_lower
        for cue in ("what looks wrong", "what is wrong", "issue", "problem")
    )
    asks_next = any(
        cue in question_lower
        for cue in ("what should i check", "check next", "next check", "what to check")
    )

    if not any((asks_what_visible, asks_issue, asks_next)):
        return True

    has_visible_section = any(
        cue in text
        for cue in ("what i can see", "what is visible", "visible observations")
    )
    has_issue_section = any(
        cue in text
        for cue in (
            "what looks wrong",
            "visible fault",
            "possible issue",
            "no obvious",
            "no clear",
        )
    )
    has_next_section = any(
        cue in text
        for cue in ("what to check next", "check next", "next checks")
    )

    return (
        (not asks_what_visible or has_visible_section)
        and (not asks_issue or has_issue_section)
        and (not asks_next or has_next_section)
    )


def build_visual_field_answer(
    analysis: dict[str, Any],
    *,
    citation_label: str = "",
) -> str:
    """Build a complete, concise field answer without relying on a second LLM pass."""
    plan = build_visual_diagnostic_plan(analysis)
    cite = f" {citation_label}".rstrip() if citation_label else ""

    lines = ["**What I can see:**", ""]

    observations = plan.get("observations") or []
    if observations:
        for item in observations[:4]:
            lines.append(f"- {item}{cite}")
    else:
        summary = str(analysis.get("summary") or "").strip()
        if summary:
            lines.append(f"- {summary}{cite}")
        else:
            lines.append(f"- The image contains visible AV/site information, but no reliable detailed observation was extracted.{cite}")

    lines.extend(["", "**What looks wrong:**", ""])

    issues = plan.get("possible_issues") or []
    supported_issues = [
        item
        for item in issues
        if item.get("confidence") in {"high", "medium"}
    ]

    if supported_issues:
        for item in supported_issues[:3]:
            basis = str(item.get("basis") or "").strip()
            confidence = str(item.get("confidence") or "low").capitalize()
            issue_text = str(item.get("issue") or "").strip()
            suffix = f" — {confidence} confidence"
            if basis:
                suffix += f"; visible basis: {basis}"
            lines.append(f"- {issue_text}{suffix}.{cite}")
    else:
        lines.append(
            f"- No obvious visual fault is directly supported by this image alone.{cite}"
        )

    uncertainties = plan.get("uncertainties") or []
    if uncertainties:
        lines.append(
            f"- Some details remain uncertain from the photo and should be verified on site rather than treated as faults.{cite}"
        )

    lines.extend(["", "**What to check next:**", ""])

    for item in (plan.get("next_checks") or [])[:5]:
        lines.append(f"- {item}{cite}")

    return "\n".join(lines).strip()
