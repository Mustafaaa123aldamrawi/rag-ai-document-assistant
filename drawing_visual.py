from __future__ import annotations

import base64
import io
import json
import os
import re
from typing import Any

import fitz
import requests
from PIL import Image


VISION_MODELS = (
    "Qwen/Qwen3.8-Flash-Next:featherless-ai",
    "Qwen/Qwen2.5-VL-3B-Instruct",
    "Qwen/Qwen2-VL-7B-Instruct",
)


def select_visual_qa_pages(
    document_pages: list[dict],
    qa: dict | None = None,
    *,
    max_pages: int = 8,
) -> list[int]:
    """Prioritize pages that are most valuable for visual engineering review."""
    scores: dict[int, int] = {}

    for page in document_pages or []:
        page_number = int(page.get("page_number") or 0)
        if page_number <= 0:
            continue
        text = str(page.get("text") or "").upper()
        score = 0

        if "SIGNAL FLOW" in text:
            score += 100
        if "DIVISIBLE MEETING ROOM" in text:
            score += 45
        if "CEILING PLAN" in text:
            score += 30
        if "CONTAINMENT" in text:
            score += 25
        if "ELEVATION" in text or "SIGHTLINE" in text:
            score += 20
        if "FLOOR PLAN AV" in text:
            score += 18
        if "TBD" in text or "VIF" in text or "VERIFY IN FIELD" in text:
            score += 12

        if score:
            scores[page_number] = scores.get(page_number, 0) + score

    for finding in (qa or {}).get("findings") or []:
        severity = str(finding.get("severity") or "").lower()
        bonus = 50 if severity == "high" else 25 if severity == "medium" else 10
        for evidence in finding.get("evidence") or []:
            if not isinstance(evidence, dict):
                continue
            page_number = evidence.get("page_number")
            if isinstance(page_number, int) and page_number > 0:
                scores[page_number] = scores.get(page_number, 0) + bonus

    if not scores:
        for page in document_pages or []:
            page_number = int(page.get("page_number") or 0)
            if page_number > 0:
                scores[page_number] = 1

    ranked = sorted(scores, key=lambda page: (-scores[page], page))
    return ranked[: max(1, int(max_pages))]


def render_pdf_pages(
    payload: bytes,
    page_numbers: list[int],
    *,
    zoom: float = 2.2,
) -> list[dict]:
    document = fitz.open(stream=payload, filetype="pdf")
    output = []
    matrix = fitz.Matrix(zoom, zoom)

    try:
        for page_number in page_numbers:
            index = int(page_number) - 1
            if index < 0 or index >= len(document):
                continue
            page = document.load_page(index)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
            output.append(
                {
                    "page_number": page_number,
                    "image": image,
                    "width": image.width,
                    "height": image.height,
                }
            )
    finally:
        document.close()

    return output


def split_drawing_image_into_regions(
    image: Image.Image,
    *,
    rows: int = 2,
    cols: int = 2,
    overlap: float = 0.08,
) -> list[dict]:
    width, height = image.size
    regions = []
    region_width = width / cols
    region_height = height / rows
    overlap_x = int(region_width * overlap)
    overlap_y = int(region_height * overlap)

    region_number = 1
    for row in range(rows):
        for col in range(cols):
            left = max(0, int(col * region_width) - overlap_x)
            top = max(0, int(row * region_height) - overlap_y)
            right = min(width, int((col + 1) * region_width) + overlap_x)
            bottom = min(height, int((row + 1) * region_height) + overlap_y)
            regions.append(
                {
                    "region_number": region_number,
                    "box": [left, top, right, bottom],
                    "image": image.crop((left, top, right, bottom)),
                }
            )
            region_number += 1
    return regions


def image_to_data_url(image: Image.Image, *, quality: int = 88) -> str:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def build_drawing_region_messages(
    *,
    file_name: str,
    page_number: int,
    region_number: int,
    image_data_url: str,
) -> list[dict]:
    schema = {
        "page_number": page_number,
        "region_number": region_number,
        "drawing_number": None,
        "room_labels": [],
        "device_blocks": [
            {
                "device_id": None,
                "manufacturer": None,
                "model": None,
                "device_type": None,
            }
        ],
        "connections": [
            {
                "wire_id": None,
                "source_device": None,
                "source_port": None,
                "destination_device": None,
                "destination_port": None,
                "signal_type": None,
                "connector_type": None,
                "confidence": "low",
                "evidence": "",
            }
        ],
        "visible_requirements": [],
        "possible_issues": [
            {
                "category": "",
                "severity": "review",
                "issue": "",
                "evidence": "",
            }
        ],
        "uncertainties": [],
    }

    return [
        {
            "role": "system",
            "content": (
                "You are a senior professional AV design review engineer. "
                "Read only what is visibly present in the supplied drawing crop. "
                "Do not invent hidden wires, ports, model numbers, or endpoints. "
                "A connection may only be emitted when the crop visually supports it. "
                "Use uncertainties instead of guessing."
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Review drawing {file_name}, PDF page {page_number}, "
                        f"region {region_number}. Return STRICT JSON only matching this schema:\n"
                        f"{json.dumps(schema, ensure_ascii=False)}\n\n"
                        "Engineering rules:\n"
                        "- Preserve exact device IDs, wire IDs, port labels, manufacturer and model text when readable.\n"
                        "- Distinguish INPUT from OUTPUT exactly as drawn.\n"
                        "- Flag visually supported output-to-output or input-to-input paths.\n"
                        "- Flag a connector/media mismatch only when both visible endpoints support that conclusion.\n"
                        "- Do not infer the opposite endpoint when it is outside this crop.\n"
                        "- Do not treat OCR uncertainty as an engineering defect.\n"
                        "- If a wire continues outside the crop, record that in uncertainties.\n"
                        "- severity must be high, medium, low, or review."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_url},
                },
            ],
        },
    ]


def parse_drawing_region_analysis(raw: str) -> dict:
    text = str(raw or "").strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        text = text.strip(chr(96)).strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]

    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r",\s*([}\]])", r"\1", text)
    data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError("Drawing visual analysis must be a JSON object.")

    for key in (
        "room_labels",
        "device_blocks",
        "connections",
        "visible_requirements",
        "possible_issues",
        "uncertainties",
    ):
        if not isinstance(data.get(key), list):
            data[key] = []

    return data


def call_drawing_vision(
    messages: list[dict],
    *,
    token: str | None = None,
    timeout: int = 120,
) -> str:
    hf_token = token or os.getenv("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("HF_TOKEN is required for visual drawing analysis.")

    url = "https://router.huggingface.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json",
    }

    errors = []
    for model in VISION_MODELS:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            "top_p": 0.8,
            "max_tokens": 2600,
            "reasoning_effort": "low",
        }
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except Exception as exc:
            errors.append(f"{model}: {exc}")
            continue

        if not response.ok:
            errors.append(f"{model}: HTTP {response.status_code} {response.text[:180]}")
            continue

        data = response.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )
        if isinstance(content, str) and content.strip():
            return content.strip()

        errors.append(f"{model}: no usable content")

    raise RuntimeError("No vision model succeeded. " + " | ".join(errors[-3:]))


def _norm_token(value: Any) -> str | None:
    text = re.sub(r"\s+", " ", str(value or "")).strip().upper()
    return text or None


def _visual_connection_records(visual_review: dict) -> list[dict]:
    records = []
    for region in (visual_review or {}).get("regions") or []:
        page_number = region.get("page_number")
        region_number = region.get("region_number")
        drawing_number = _norm_token(region.get("drawing_number"))
        for connection in region.get("connections") or []:
            if not isinstance(connection, dict):
                continue
            wire_id = _norm_token(connection.get("wire_id"))
            source_device = _norm_token(connection.get("source_device"))
            destination_device = _norm_token(connection.get("destination_device"))
            source_port = _norm_token(connection.get("source_port"))
            destination_port = _norm_token(connection.get("destination_port"))
            signal_type = _norm_token(connection.get("signal_type"))
            connector_type = _norm_token(connection.get("connector_type"))
            if not any(
                (
                    wire_id,
                    source_device,
                    destination_device,
                    source_port,
                    destination_port,
                )
            ):
                continue
            records.append(
                {
                    "page_number": page_number,
                    "region_number": region_number,
                    "drawing_number": drawing_number,
                    "wire_id": wire_id,
                    "source_device": source_device,
                    "source_port": source_port,
                    "destination_device": destination_device,
                    "destination_port": destination_port,
                    "signal_type": signal_type,
                    "connector_type": connector_type,
                    "confidence": _norm_token(connection.get("confidence")),
                    "evidence": str(connection.get("evidence") or "").strip(),
                }
            )
    return records


def _same_or_unknown(left: str | None, right: str | None) -> bool:
    return not left or not right or left == right


def reconcile_visual_with_connection_graph(
    qa: dict,
    visual_review: dict,
) -> dict:
    """Cross-check text-derived graph edges against visual observations.

    This function never overwrites the text graph. It adds a second evidence
    layer that can confirm, contradict, or leave a connection unresolved.
    """
    graph_edges = (qa or {}).get("connection_graph", {}).get("edges") or []
    visual_connections = _visual_connection_records(visual_review)

    by_wire: dict[str, list[dict]] = {}
    for item in visual_connections:
        wire_id = item.get("wire_id")
        if wire_id:
            by_wire.setdefault(wire_id, []).append(item)

    confirmed = []
    conflicts = []
    unresolved = []

    for edge in graph_edges:
        if edge.get("status") != "resolved":
            continue
        wire_id = _norm_token(edge.get("wire_id"))
        source = edge.get("source") or {}
        destination = edge.get("destination") or {}
        text_source = _norm_token(source.get("device_id"))
        text_destination = _norm_token(destination.get("device_id"))
        text_source_port = _norm_token(source.get("port"))
        text_destination_port = _norm_token(destination.get("port"))

        candidates = by_wire.get(wire_id or "", [])
        if not candidates:
            unresolved.append(
                {
                    "wire_id": wire_id,
                    "status": "NO_VISUAL_MATCH",
                    "text_source_device": text_source,
                    "text_destination_device": text_destination,
                    "pages": edge.get("pages") or [],
                }
            )
            continue

        best_match = None
        best_score = -1
        for candidate in candidates:
            score = 0
            if candidate.get("source_device") == text_source and text_source:
                score += 3
            if candidate.get("destination_device") == text_destination and text_destination:
                score += 3
            if candidate.get("source_port") and text_source_port and candidate.get("source_port") in text_source_port:
                score += 1
            if candidate.get("destination_port") and text_destination_port and candidate.get("destination_port") in text_destination_port:
                score += 1
            if score > best_score:
                best_match = candidate
                best_score = score

        candidate = best_match or candidates[0]
        source_ok = _same_or_unknown(candidate.get("source_device"), text_source)
        destination_ok = _same_or_unknown(
            candidate.get("destination_device"), text_destination
        )

        if source_ok and destination_ok:
            confirmed.append(
                {
                    "wire_id": wire_id,
                    "status": "VISUALLY_CONFIRMED",
                    "text": {
                        "source_device": text_source,
                        "source_port": source.get("port"),
                        "destination_device": text_destination,
                        "destination_port": destination.get("port"),
                        "confidence": edge.get("confidence"),
                    },
                    "visual": candidate,
                }
            )
        else:
            conflicts.append(
                {
                    "wire_id": wire_id,
                    "status": "CONFLICT_REVIEW",
                    "severity": "high",
                    "title": f"{wire_id} visual endpoints conflict with extracted connection graph",
                    "why_it_matters": (
                        "The text-derived signal-flow graph and visual drawing review "
                        "do not agree on the same endpoint device IDs."
                    ),
                    "recommended_action": (
                        "Open the referenced page/region and verify the wire label and "
                        "both device blocks before installation or programming."
                    ),
                    "text": {
                        "source_device": text_source,
                        "source_port": source.get("port"),
                        "destination_device": text_destination,
                        "destination_port": destination.get("port"),
                    },
                    "visual": candidate,
                }
            )

    graph_wire_ids = {
        _norm_token(edge.get("wire_id"))
        for edge in graph_edges
        if _norm_token(edge.get("wire_id"))
    }
    visual_only = [
        item
        for item in visual_connections
        if item.get("wire_id") and item.get("wire_id") not in graph_wire_ids
    ]

    reviewed = len(confirmed) + len(conflicts)
    return {
        "visual_connection_count": len(visual_connections),
        "confirmed_count": len(confirmed),
        "conflict_count": len(conflicts),
        "no_visual_match_count": len(unresolved),
        "visual_only_count": len(visual_only),
        "confirmation_rate": round(
            len(confirmed) / reviewed, 3
        ) if reviewed else 0.0,
        "confirmed": confirmed,
        "conflicts": conflicts,
        "unresolved": unresolved,
        "visual_only": visual_only,
        "quality_note": (
            "Visual confirmation strengthens evidence but does not replace field "
            "verification, manufacturer documentation, or commissioning tests."
        ),
    }


def analyze_visual_drawing_pages(
    *,
    file_name: str,
    payload: bytes,
    document_pages: list[dict],
    qa: dict,
    max_pages: int = 6,
    regions_per_page: int = 4,
    token: str | None = None,
) -> dict:
    selected_pages = select_visual_qa_pages(
        document_pages,
        qa,
        max_pages=max_pages,
    )
    rendered = render_pdf_pages(payload, selected_pages)

    analyses = []
    for page in rendered:
        if regions_per_page <= 1:
            regions = [
                {
                    "region_number": 1,
                    "box": [0, 0, page["width"], page["height"]],
                    "image": page["image"],
                }
            ]
        else:
            regions = split_drawing_image_into_regions(page["image"])

        for region in regions[:regions_per_page]:
            messages = build_drawing_region_messages(
                file_name=file_name,
                page_number=page["page_number"],
                region_number=region["region_number"],
                image_data_url=image_to_data_url(region["image"]),
            )
            raw = call_drawing_vision(messages, token=token)
            parsed = parse_drawing_region_analysis(raw)
            parsed["page_number"] = page["page_number"]
            parsed["region_number"] = region["region_number"]
            parsed["box"] = region["box"]
            analyses.append(parsed)

    return {
        "selected_pages": selected_pages,
        "analysis_count": len(analyses),
        "regions": analyses,
    }
