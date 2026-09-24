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
