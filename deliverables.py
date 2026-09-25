from __future__ import annotations

from io import BytesIO
from typing import Any

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


NAVY = "17365D"
BLUE = "2F75B5"
LIGHT_BLUE = "D9EAF7"
LIGHT_GRAY = "F2F2F2"
LIGHT_GREEN = "E2F0D9"
LIGHT_ORANGE = "FCE4D6"
LIGHT_YELLOW = "FFF2CC"
WHITE = "FFFFFF"
DARK_GRAY = "5B6573"


def _rgb(value: str):
    return __import__("docx").shared.RGBColor.from_string(value)


def _shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def _set_cell_margins(cell, top=70, start=90, bottom=70, end=90) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _set_cell_text(
    cell,
    text: Any,
    *,
    bold: bool = False,
    color: str | None = None,
    size: float = 9,
) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run("" if text is None else str(text))
    run.bold = bold
    run.font.name = "Aptos"
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = _rgb(color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    _set_cell_margins(cell)


def _format_table(table) -> None:
    table.style = "Table Grid"
    table.autofit = True
    for row in table.rows:
        for cell in row.cells:
            _set_cell_margins(cell)


def _set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    node = tr_pr.find(qn("w:tblHeader"))
    if node is None:
        node = OxmlElement("w:tblHeader")
        tr_pr.append(node)
    node.set(qn("w:val"), "true")


def _add_section_heading(document: Document, title: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(12)
    paragraph.paragraph_format.space_after = Pt(5)
    run = paragraph.add_run(title)
    run.bold = True
    run.font.name = "Aptos Display"
    run.font.size = Pt(13)
    run.font.color.rgb = _rgb(NAVY)


def _add_header_footer(document: Document, project_name: str, document_type: str) -> None:
    for section in document.sections:
        header = section.header
        p = header.paragraphs[0]
        p.text = ""
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = p.add_run(f"{project_name}  |  {document_type}")
        run.font.name = "Aptos"
        run.font.size = Pt(8)
        run.font.color.rgb = _rgb(DARK_GRAY)

        footer = section.footer
        p = footer.paragraphs[0]
        p.text = ""
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(
            "Draft | Unconfirmed items require field verification before final acceptance"
        )
        run.font.name = "Aptos"
        run.font.size = Pt(7.5)
        run.font.color.rgb = _rgb(DARK_GRAY)


def _project_fields(checklist_data: dict[str, Any]) -> tuple[str, str, str, list[str]]:
    project_info = checklist_data.get("project_info") or {}
    project_name = str(project_info.get("project_name") or "AV Site Survey").strip()
    client = str(project_info.get("client") or "").strip()
    location = str(project_info.get("location") or project_info.get("site") or "").strip()
    raw_rooms = checklist_data.get("rooms_areas")
    if not raw_rooms:
        raw_rooms = project_info.get("rooms") or []
    rooms = [str(item).strip() for item in raw_rooms or [] if str(item).strip()]
    return project_name, client, location, rooms


def _add_document_control_table(
    document: Document,
    *,
    project_name: str,
    client: str,
    location: str,
    rooms: list[str],
    status: str,
    document_type: str,
) -> None:
    table = document.add_table(rows=0, cols=2)
    _format_table(table)
    for label, value in (
        ("Document", document_type),
        ("Project", project_name),
        ("Client", client),
        ("Location", location),
        ("Rooms / Areas", ", ".join(rooms)),
        ("Status", status),
    ):
        if not value:
            continue
        cells = table.add_row().cells
        _set_cell_text(cells[0], label, bold=True, color=WHITE)
        _shade_cell(cells[0], NAVY)
        _set_cell_text(cells[1], value)


def _normalized_checklist_sections(checklist_data: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    source_sections = checklist_data.get("checklist_sections") or []
    if source_sections:
        for section in source_sections:
            if not isinstance(section, dict):
                continue
            name = str(section.get("section") or section.get("section_title") or "").strip()
            items = []
            for item in section.get("items", []) or []:
                if not isinstance(item, dict):
                    continue
                items.append(
                    {
                        "item": item.get("item") or item.get("inspection_item") or "",
                        "status": str(item.get("status") or "VERIFY").upper(),
                        "notes": item.get("notes") or item.get("notes_photo") or "",
                        "photo_ref": item.get("photo_ref") or "",
                    }
                )
            if name and items:
                normalized.append({"section": name, "items": items})
        return normalized

    for section in checklist_data.get("inspection_sections", []) or []:
        if not isinstance(section, dict):
            continue
        name = str(section.get("section_title") or section.get("section") or "Inspection").strip()
        items = []
        for item in section.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            items.append(
                {
                    "item": item.get("inspection_item") or item.get("item") or "",
                    "status": str(item.get("status") or "VERIFY").upper(),
                    "notes": item.get("notes_photo") or item.get("notes") or "",
                    "photo_ref": item.get("photo_ref") or "",
                }
            )
        if name and items:
            normalized.append({"section": name, "items": items})

    return normalized


def _scope_section_summary(checklist_data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for section in _normalized_checklist_sections(checklist_data):
        items = section.get("items", []) or []
        if not items:
            continue

        counts = {"PASS": 0, "OBSERVATION": 0, "VERIFY": 0, "ACTION": 0, "N/A": 0}
        photo_refs = []
        for item in items:
            status = str(item.get("status") or "VERIFY").upper()
            if status in counts:
                counts[status] += 1
            refs = [
                ref.strip()
                for ref in str(item.get("photo_ref") or "").split(",")
                if ref.strip()
            ]
            for ref in refs:
                if ref not in photo_refs:
                    photo_refs.append(ref)

        if counts["ACTION"]:
            section_status = "ACTION"
        elif counts["VERIFY"]:
            section_status = "VERIFY"
        elif counts["OBSERVATION"]:
            section_status = "OBSERVATION"
        elif counts["PASS"] and not any(
            counts[key] for key in ("VERIFY", "OBSERVATION", "ACTION")
        ):
            section_status = "PASS"
        else:
            section_status = "VERIFY"

        key_items = [
            _compact_text(item.get("item"), 130)
            for item in items[:2]
            if str(item.get("item") or "").strip()
        ]

        rows.append(
            {
                "section": section.get("section") or "",
                "items": len(items),
                "status": section_status,
                "photo_refs": ", ".join(photo_refs[:4]),
                "focus": " | ".join(key_items),
            }
        )
    return rows


def _status_summary(checklist_data: dict[str, Any]) -> dict[str, int]:
    counts = {"PASS": 0, "VERIFY": 0, "ACTION": 0, "N/A": 0, "OTHER": 0}
    for section in _normalized_checklist_sections(checklist_data):
        for item in section.get("items", []) or []:
            status = str(item.get("status") or "VERIFY").strip().upper()
            if status not in counts:
                status = "OTHER"
            counts[status] += 1
    return counts


def _normalize_required_photos(checklist_data: dict[str, Any]) -> list[str]:
    result = []
    for item in checklist_data.get("required_photos", []) or []:
        if isinstance(item, dict):
            parts = [
                item.get("photo_subject") or item.get("subject") or item.get("item"),
                item.get("location_direction"),
                item.get("related_item"),
            ]
            text = " | ".join(str(v).strip() for v in parts if str(v or "").strip())
        else:
            text = str(item or "").strip()
        if text:
            result.append(text)
    return result


def _visual_summary(checklist_data: dict[str, Any]) -> dict[str, Any]:
    visual = checklist_data.get("visual_inspection")
    return visual if isinstance(visual, dict) else {}


def _compact_text(value: Any, max_chars: int = 170) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _status_fill(status: str) -> str | None:
    status = str(status or "").upper()
    if status == "PASS":
        return LIGHT_GREEN
    if status == "VERIFY":
        return LIGHT_BLUE
    if status == "OBSERVATION":
        return LIGHT_YELLOW
    if status in {"ACTION", "RISK", "BLOCKER", "HOLD"}:
        return LIGHT_ORANGE
    return None


def _add_title_block(document: Document, title: str, project_name: str, subtitle: str) -> None:
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title)
    run.bold = True
    run.font.name = "Aptos Display"
    run.font.size = Pt(22)
    run.font.color.rgb = _rgb(NAVY)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(project_name)
    run.bold = True
    run.font.name = "Aptos Display"
    run.font.size = Pt(15)
    run.font.color.rgb = _rgb(BLUE)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(subtitle)
    run.italic = True
    run.font.name = "Aptos"
    run.font.size = Pt(9)
    run.font.color.rgb = _rgb(DARK_GRAY)


def _add_visual_findings_section(document: Document, checklist_data: dict[str, Any], number: str) -> None:
    visual = _visual_summary(checklist_data)
    findings = checklist_data.get("visual_findings")
    if findings is None:
        findings = visual.get("visual_findings", []) if visual else []
    verify_items = checklist_data.get("verification_items")
    if verify_items is None:
        verify_items = visual.get("verification_items", []) if visual else []

    if not findings and not verify_items:
        return

    _add_section_heading(document, f"{number}. Visual Findings & Field Verification")

    if findings:
        table = document.add_table(rows=1, cols=6)
        _format_table(table)
        headers = ["ID", "Photo Ref.", "Observation / Finding", "Confidence", "Status", "Required Follow-up"]
        for idx, header in enumerate(headers):
            _set_cell_text(table.rows[0].cells[idx], header, bold=True, color=WHITE)
            _shade_cell(table.rows[0].cells[idx], NAVY)
        _set_repeat_table_header(table.rows[0])

        for finding in findings:
            if not isinstance(finding, dict):
                continue
            status = str(finding.get("status") or "VERIFY").upper()
            row = table.add_row().cells
            values = [
                finding.get("id") or "",
                finding.get("source_photo_ref") or finding.get("source_photo") or "",
                _compact_text(finding.get("finding"), 220),
                finding.get("confidence") or "",
                status,
                _compact_text(finding.get("required_action"), 220),
            ]
            for idx, value in enumerate(values):
                _set_cell_text(row[idx], value, size=8.5)
            fill = _status_fill(status)
            if fill:
                _shade_cell(row[4], fill)

    if verify_items:
        document.add_paragraph()
        p = document.add_paragraph()
        run = p.add_run("Open verification items")
        run.bold = True
        run.font.color.rgb = _rgb(BLUE)

        table = document.add_table(rows=1, cols=5)
        _format_table(table)
        for idx, header in enumerate(["ID", "Photo Ref.", "Item", "Status", "Required Follow-up"]):
            _set_cell_text(table.rows[0].cells[idx], header, bold=True, color=WHITE)
            _shade_cell(table.rows[0].cells[idx], NAVY)
        _set_repeat_table_header(table.rows[0])

        for item in verify_items:
            if not isinstance(item, dict):
                continue
            row = table.add_row().cells
            values = [
                item.get("id") or "",
                item.get("source_photo_ref") or item.get("source_photo") or "",
                _compact_text(item.get("item"), 220),
                item.get("status") or "VERIFY",
                _compact_text(item.get("required_action") or "Verify on site", 220),
            ]
            for idx, value in enumerate(values):
                _set_cell_text(row[idx], value, size=8.5)
            _shade_cell(row[3], LIGHT_BLUE)


def _add_photo_register(document: Document, checklist_data: dict[str, Any], number: str) -> None:
    photo_register = checklist_data.get("photo_register", []) or []
    if not photo_register:
        return

    _add_section_heading(document, f"{number}. Photo Evidence Register")
    table = document.add_table(rows=1, cols=5)
    _format_table(table)
    headers = ["Ref.", "Category", "Subject / Area", "Status", "Notes"]
    for idx, header in enumerate(headers):
        _set_cell_text(table.rows[0].cells[idx], header, bold=True, color=WHITE)
        _shade_cell(table.rows[0].cells[idx], NAVY)
    _set_repeat_table_header(table.rows[0])

    for entry in photo_register:
        if isinstance(entry, dict):
            values = [
                entry.get("photo_ref") or entry.get("photo_number") or "",
                entry.get("category") or "",
                _compact_text(
                    entry.get("photo_subject")
                    or entry.get("subject")
                    or entry.get("subject_equipment")
                    or "",
                    180,
                ),
                entry.get("status") or "PENDING",
                _compact_text(entry.get("photo_notes") or entry.get("notes") or "", 180),
            ]
        else:
            values = ["", "", _compact_text(entry, 180), "PENDING", ""]
        row = table.add_row().cells
        for idx, value in enumerate(values):
            _set_cell_text(row[idx], value, size=8.5)


def build_site_survey_report_docx(checklist_data: dict[str, Any]) -> bytes | None:
    if not isinstance(checklist_data, dict):
        return None

    project_name, client, location, rooms = _project_fields(checklist_data)
    visual = _visual_summary(checklist_data)
    visual_meta = visual.get("inspection_meta") or checklist_data.get("inspection_meta") or {}
    visual_status = str(
        checklist_data.get("visual_status")
        or visual_meta.get("visual_status")
        or visual_meta.get("overall_status")
        or "VERIFY"
    ).strip()
    survey_status = str(
        checklist_data.get("survey_status")
        or visual_status
        or "Draft / Pre-Survey"
    ).strip()

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.6)
    section.right_margin = Inches(0.6)

    document.styles["Normal"].font.name = "Aptos"
    document.styles["Normal"].font.size = Pt(9.5)

    _add_header_footer(document, project_name, "AV SITE SURVEY & INSPECTION REPORT")
    _add_title_block(
        document,
        "AV SITE SURVEY REPORT & INSPECTION",
        project_name,
        "Scope verification + visual site evidence | Draft until field sign-off",
    )
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "Draft / Pre-Survey Report – final acceptance requires field verification and sign-off."
    )
    run.italic = True
    run.font.size = Pt(8.5)
    run.font.color.rgb = _rgb(DARK_GRAY)
    document.add_paragraph()
    _add_document_control_table(
        document,
        project_name=project_name,
        client=client,
        location=location,
        rooms=rooms,
        status=survey_status,
        document_type="AV Site Survey & Inspection Report",
    )

    _add_section_heading(document, "1. Executive Summary")
    counts = _status_summary(checklist_data)
    summary = (
        checklist_data.get("executive_summary")
        or visual.get("executive_summary")
        or (
            f"This report organizes project verification for {project_name}. "
            f"Checklist status: {counts['PASS']} PASS, {counts['VERIFY']} VERIFY, "
            f"{counts['ACTION']} ACTION, {counts['N/A']} N/A."
        )
    )
    document.add_paragraph(str(summary))

    if visual_meta:
        dashboard = document.add_table(rows=2, cols=5)
        _format_table(dashboard)
        headers = ["Survey Status", "Visual Status", "Photos", "Obs / Actions", "Visual Verify"]
        values = [
            survey_status,
            visual_status,
            visual_meta.get("photos_reviewed") or 0,
            f"{visual_meta.get('observations') or 0} / {visual_meta.get('actions') or 0}",
            visual_meta.get("verify_items") or 0,
        ]
        for idx, header in enumerate(headers):
            _set_cell_text(dashboard.rows[0].cells[idx], header, bold=True, color=WHITE)
            _shade_cell(dashboard.rows[0].cells[idx], NAVY)
            _set_cell_text(dashboard.rows[1].cells[idx], values[idx], bold=(idx == 0))

    _add_section_heading(document, "2. Basis & Survey Scope")
    if rooms:
        document.add_paragraph("Rooms / areas: " + ", ".join(rooms) + ".")
    document.add_paragraph(
        "Scope-derived items represent design/project requirements. Visual findings represent only "
        "conditions supported by uploaded site images. VERIFY items are not confirmed defects and "
        "must be checked on site or through the relevant system interface."
    )

    scope_available = checklist_data.get("scope_available")
    if scope_available is None:
        scope_available = bool(
            checklist_data.get("checklist_sections")
            or checklist_data.get("inspection_sections")
            or checklist_data.get("survey_priorities")
        )

    _add_section_heading(document, "3. Design / Scope Verification Summary")
    sections = _normalized_checklist_sections(checklist_data)
    if scope_available and sections:
        scope_rows = _scope_section_summary(checklist_data)
        table = document.add_table(rows=1, cols=5)
        _format_table(table)
        headers = ["Scope Section", "Items", "Status", "Photo Ref.", "Key Verification Focus"]
        for idx, header in enumerate(headers):
            _set_cell_text(table.rows[0].cells[idx], header, bold=True, color=WHITE)
            _shade_cell(table.rows[0].cells[idx], NAVY)
        _set_repeat_table_header(table.rows[0])

        for entry in scope_rows:
            row = table.add_row().cells
            values = [
                entry.get("section") or "",
                entry.get("items") or 0,
                entry.get("status") or "VERIFY",
                entry.get("photo_refs") or "",
                entry.get("focus") or "",
            ]
            for idx, value in enumerate(values):
                _set_cell_text(row[idx], value, size=8.5)
            fill = _status_fill(str(entry.get("status") or ""))
            if fill:
                _shade_cell(row[2], fill)

        document.add_paragraph(
            "Detailed item-by-item verification is provided in the companion AV Site Survey Checklist."
        )
    else:
        document.add_paragraph(
            "No Scope-derived verification checklist was available. This report is based on visual inspection evidence only."
        )

    _add_visual_findings_section(document, checklist_data, "4")

    required_photos = _normalize_required_photos(checklist_data)
    if required_photos:
        _add_section_heading(document, "5. Required / Missing Evidence")
        for item in required_photos:
            document.add_paragraph(f"☐ {item}")

    _add_photo_register(document, checklist_data, "6")

    _add_section_heading(document, "7. Recommendations / Next Actions / Close-out")
    open_items = checklist_data.get("open_items", []) or []
    findings = checklist_data.get("visual_findings") or visual.get("visual_findings", [])
    if open_items:
        for item in open_items:
            document.add_paragraph(f"• {item}")
    action_findings = [
        finding
        for finding in findings
        if isinstance(finding, dict)
        and str(finding.get("status") or "").upper() == "ACTION"
    ]
    if action_findings:
        for finding in action_findings:
            document.add_paragraph(
                f"• {finding.get('id') or ''} {_compact_text(finding.get('required_action') or 'Correct and close with evidence.', 220)}".strip()
            )
    elif findings:
        document.add_paragraph(
            "• Review visual observations against the Scope and actual site state before assigning corrective action."
        )
    if survey_status == "FIELD VERIFICATION REQUIRED":
        document.add_paragraph(
            "• Complete the outstanding Scope verification items in the companion checklist and attach photo/evidence references before final acceptance."
        )
    if not open_items and not findings and survey_status != "FIELD VERIFICATION REQUIRED":
        document.add_paragraph(
            "No open actions have been recorded yet. Confirm all VERIFY items before issuing a final status."
        )

    _add_section_heading(document, "8. Final Assessment")
    conclusion = checklist_data.get("conclusion") or {}

    visual_actions = int(visual_meta.get("actions") or 0)
    critical_blockers = conclusion.get("critical_blockers")
    if not critical_blockers:
        critical_blockers = (
            "Visual action item(s) require immediate review."
            if visual_actions
            else "No critical blocker is confirmed from the uploaded visual evidence."
        )

    additional_work = conclusion.get("additional_work_required")
    if not additional_work and survey_status == "FIELD VERIFICATION REQUIRED":
        additional_work = (
            "Complete the outstanding Scope verification checklist items and "
            "record evidence before final acceptance."
        )

    next_step = conclusion.get("next_step_target_date")
    if not next_step:
        next_step = (
            "Complete field verification, update PASS / OBSERVATION / ACTION statuses, "
            "and issue the final signed report."
        )

    table = document.add_table(rows=0, cols=2)
    _format_table(table)
    assessment_rows = [
        ("Survey Status", survey_status),
        ("Visual Status", visual_status),
        ("Critical Blockers", critical_blockers),
        ("Additional Work Required", additional_work or "To be confirmed during field verification."),
        ("Customer Actions", conclusion.get("customer_actions") or "To be confirmed during field verification."),
        ("Designer / Programmer Actions", conclusion.get("designer_programmer_actions") or "To be confirmed during field verification."),
        ("Next Step", next_step),
    ]
    for label, value in assessment_rows:
        cells = table.add_row().cells
        _set_cell_text(cells[0], label, bold=True)
        _shade_cell(cells[0], LIGHT_GRAY)
        _set_cell_text(cells[1], value)

    _add_section_heading(document, "9. Sign-off")
    sign_table = document.add_table(rows=4, cols=2)
    _format_table(sign_table)
    for row, values in zip(
        sign_table.rows,
        [
            ("Surveyed By", ""),
            ("Project / Engineering Review", ""),
            ("Client Representative", ""),
            ("Date", ""),
        ],
    ):
        _set_cell_text(row.cells[0], values[0], bold=True)
        _shade_cell(row.cells[0], LIGHT_GRAY)
        _set_cell_text(row.cells[1], values[1])

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def build_professional_site_survey_checklist_docx(
    checklist_data: dict[str, Any],
) -> bytes | None:
    if not isinstance(checklist_data, dict):
        return None

    project_name, client, location, rooms = _project_fields(checklist_data)
    visual = _visual_summary(checklist_data)
    visual_meta = visual.get("inspection_meta") or checklist_data.get("inspection_meta") or {}
    visual_status = str(
        checklist_data.get("visual_status")
        or visual_meta.get("visual_status")
        or visual_meta.get("overall_status")
        or "VERIFY"
    )
    survey_status = str(
        checklist_data.get("survey_status")
        or visual_status
        or "Pre-Survey / To Be Verified"
    )

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.6)
    section.right_margin = Inches(0.6)

    document.styles["Normal"].font.name = "Aptos"
    document.styles["Normal"].font.size = Pt(9.5)

    _add_header_footer(document, project_name, "AV SITE SURVEY CHECKLIST")
    _add_title_block(
        document,
        "AV SITE SURVEY CHECKLIST",
        project_name,
        "Field verification checklist | PASS / OBSERVATION / VERIFY / ACTION / N/A",
    )
    document.add_paragraph()
    _add_document_control_table(
        document,
        project_name=project_name,
        client=client,
        location=location,
        rooms=rooms,
        status=survey_status,
        document_type="AV Site Survey Checklist",
    )

    p = document.add_paragraph()
    run = p.add_run(f"Visual status: {visual_status}")
    run.bold = True
    run.font.color.rgb = _rgb(DARK_GRAY)

    p = document.add_paragraph()
    run = p.add_run("Status guide: ")
    run.bold = True
    p.add_run(
        "PASS = verified acceptable; OBSERVATION = visible condition for review; "
        "VERIFY = requires confirmation; ACTION = corrective action / coordination required; "
        "N/A = not applicable."
    )

    survey_priorities = checklist_data.get("survey_priorities", []) or []
    if survey_priorities:
        _add_section_heading(document, "Survey Priorities / Installation Blockers")
        table = document.add_table(rows=1, cols=4)
        _format_table(table)
        for idx, header in enumerate(["Priority Item", "Reason", "Status", "Notes / Evidence"]):
            _set_cell_text(table.rows[0].cells[idx], header, bold=True, color=WHITE)
            _shade_cell(table.rows[0].cells[idx], NAVY)
        _set_repeat_table_header(table.rows[0])
        for item in survey_priorities:
            if not isinstance(item, dict):
                continue
            row = table.add_row().cells
            values = [
                item.get("priority_item") or "",
                item.get("reason") or "",
                "VERIFY",
                "",
            ]
            for idx, value in enumerate(values):
                _set_cell_text(row[idx], value)
            _shade_cell(row[2], LIGHT_BLUE)

    item_number = 1
    sections = _normalized_checklist_sections(checklist_data)
    for section_index, section_data in enumerate(sections, start=1):
        section_name = str(section_data.get("section") or "").strip()
        items = section_data.get("items") or []
        if not section_name or not items:
            continue

        _add_section_heading(document, f"{section_index}. {section_name}")
        table = document.add_table(rows=1, cols=5)
        _format_table(table)
        headers = ["No.", "Inspection / Verification Item", "Status", "Notes / Evidence", "Photo Ref."]
        for idx, header in enumerate(headers):
            _set_cell_text(table.rows[0].cells[idx], header, bold=True, color=WHITE)
            _shade_cell(table.rows[0].cells[idx], NAVY)
        _set_repeat_table_header(table.rows[0])

        for item in items:
            item_status = str(item.get("status") or "VERIFY").upper()
            row = table.add_row().cells
            values = [
                item_number,
                item.get("item") or "",
                item_status,
                item.get("notes") or "",
                item.get("photo_ref") or "",
            ]
            for idx, value in enumerate(values):
                _set_cell_text(row[idx], value, size=8.5)
            fill = _status_fill(item_status)
            if fill:
                _shade_cell(row[2], fill)
            item_number += 1

    _add_visual_findings_section(document, checklist_data, "V")

    required_photos = _normalize_required_photos(checklist_data)
    if required_photos:
        _add_section_heading(document, "Required Site Photos")
        for photo in required_photos:
            document.add_paragraph(f"☐ {photo}")

    _add_photo_register(document, checklist_data, "P")

    _add_section_heading(document, "Deviations / Risks / Actions")
    risk_rows = checklist_data.get("deviations_risks_actions", []) or []
    table = document.add_table(rows=1, cols=7)
    _format_table(table)
    headers = [
        "ID",
        "Photo Ref.",
        "Deviation / Risk / Observation",
        "Impact",
        "Required Action",
        "Owner",
        "Priority",
    ]
    for idx, header in enumerate(headers):
        _set_cell_text(table.rows[0].cells[idx], header, bold=True, color=WHITE)
        _shade_cell(table.rows[0].cells[idx], NAVY)
    _set_repeat_table_header(table.rows[0])

    if risk_rows:
        rows_to_add = risk_rows
    else:
        rows_to_add = [
            {
                "id": "",
                "photo_ref": "",
                "deviation_risk_missing_item": "No deviation/action has been confirmed from the current visual evidence.",
                "impact": "",
                "required_action": "Continue Scope verification and record any confirmed deviation.",
                "owner": "",
                "priority": "",
            }
        ]

    for entry in rows_to_add:
        if not isinstance(entry, dict):
            continue
        row = table.add_row().cells
        values = [
            entry.get("id") or "",
            entry.get("photo_ref") or "",
            entry.get("deviation_risk_missing_item") or entry.get("finding") or "",
            entry.get("impact") or "",
            entry.get("required_action") or "",
            entry.get("owner") or "",
            entry.get("priority") or "",
        ]
        for idx, value in enumerate(values):
            _set_cell_text(row[idx], value, size=8.2)
        fill = _status_fill(str(entry.get("priority") or ""))
        if fill:
            _shade_cell(row[6], fill)

    _add_section_heading(document, "Survey Sign-off / Outcome")
    outcome = document.add_table(rows=5, cols=2)
    _format_table(outcome)
    for row, values in zip(
        outcome.rows,
        [
            ("Overall Status", survey_status),
            ("Surveyed By", ""),
            ("Project / Engineering Review", ""),
            ("Client Representative", ""),
            ("Date", ""),
        ],
    ):
        _set_cell_text(row.cells[0], values[0], bold=True)
        _shade_cell(row.cells[0], LIGHT_GRAY)
        _set_cell_text(row.cells[1], values[1])

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()



def _add_final_report_photo_evidence(
    document: Document,
    checklist_data: dict[str, Any],
) -> None:
    photo_register = checklist_data.get("photo_register", []) or []
    if not photo_register:
        return

    _add_section_heading(document, "7. Photo Evidence")

    intro = document.add_paragraph(
        "The photographs below are included as visual evidence only. "
        "They confirm only what is directly visible in each image and do not, by themselves, "
        "confirm concealed cabling, internal configuration, commissioning status, or final compliance."
    )
    intro.paragraph_format.space_after = Pt(8)

    rendered = 0
    for entry in photo_register:
        if not isinstance(entry, dict):
            continue

        image_bytes = entry.get("image_bytes")
        if not image_bytes:
            continue

        photo_ref = str(
            entry.get("photo_ref")
            or entry.get("photo_number")
            or f"P{rendered + 1:02d}"
        ).strip()
        subject = _compact_text(
            entry.get("photo_subject")
            or entry.get("subject")
            or entry.get("subject_equipment")
            or "Site photo",
            220,
        )
        category = str(entry.get("category") or "").strip()
        notes = _compact_text(
            entry.get("photo_notes")
            or entry.get("notes")
            or "",
            320,
        )

        if rendered:
            document.add_paragraph()

        caption = document.add_paragraph()
        caption.paragraph_format.space_after = Pt(4)
        run = caption.add_run(
            f"{photo_ref} — {subject}"
            + (f" [{category}]" if category else "")
        )
        run.bold = True
        run.font.name = "Aptos"
        run.font.size = Pt(10)
        run.font.color.rgb = _rgb(NAVY)

        try:
            picture_stream = BytesIO(image_bytes)
            document.add_picture(
                picture_stream,
                width=Inches(6.25),
            )
            picture_paragraph = document.paragraphs[-1]
            picture_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception:
            fallback = document.add_paragraph(
                f"{photo_ref}: embedded image could not be rendered in this document."
            )
            fallback.runs[0].italic = True

        if notes:
            p = document.add_paragraph()
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(8)
            run = p.add_run("Visible evidence: ")
            run.bold = True
            p.add_run(notes)

        rendered += 1

    if not rendered:
        document.add_paragraph(
            "Photo references are available in the evidence register, but no embedded image bytes "
            "were available for this generated report."
        )


def build_final_professional_site_report_docx(
    checklist_data: dict[str, Any],
) -> bytes | None:
    """
    Build a client-facing one-click final report package from the current
    Scope-derived survey data and retained inspection photo evidence.

    The report remains evidence-disciplined: VERIFY stays unconfirmed and
    visual observations are not converted into defects without field closure.
    """
    if not isinstance(checklist_data, dict):
        return None

    project_name, client, location, rooms = _project_fields(checklist_data)
    visual = _visual_summary(checklist_data)
    visual_meta = visual.get("inspection_meta") or checklist_data.get("inspection_meta") or {}

    visual_status = str(
        checklist_data.get("visual_status")
        or visual_meta.get("visual_status")
        or visual_meta.get("overall_status")
        or "VERIFY"
    ).strip()
    survey_status = str(
        checklist_data.get("survey_status")
        or visual_status
        or "FIELD VERIFICATION REQUIRED"
    ).strip()

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.62)
    section.right_margin = Inches(0.62)

    document.styles["Normal"].font.name = "Aptos"
    document.styles["Normal"].font.size = Pt(9.5)

    _add_header_footer(document, project_name, "FINAL AV SITE SURVEY & INSPECTION REPORT")
    _add_title_block(
        document,
        "FINAL AV SITE SURVEY & INSPECTION REPORT",
        project_name,
        "Scope verification + field observations + embedded photographic evidence",
    )

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "Report status is evidence-based. Final acceptance requires closure of all outstanding VERIFY/ACTION items and sign-off."
    )
    run.italic = True
    run.font.size = Pt(8.5)
    run.font.color.rgb = _rgb(DARK_GRAY)

    document.add_paragraph()

    _add_document_control_table(
        document,
        project_name=project_name,
        client=client,
        location=location,
        rooms=rooms,
        status=survey_status,
        document_type="Final AV Site Survey & Inspection Report",
    )

    _add_section_heading(document, "1. Executive Summary")
    executive_summary = (
        checklist_data.get("executive_summary")
        or visual.get("executive_summary")
        or "Site inspection evidence and Scope verification were consolidated into this report."
    )
    document.add_paragraph(str(executive_summary))

    dashboard = document.add_table(rows=2, cols=5)
    _format_table(dashboard)
    headers = ["Survey Status", "Visual Status", "Photos", "Observations / Actions", "Visual Verify"]
    values = [
        survey_status,
        visual_status,
        visual_meta.get("photos_reviewed") or 0,
        f"{visual_meta.get('observations') or 0} / {visual_meta.get('actions') or 0}",
        visual_meta.get("verify_items") or 0,
    ]
    for idx, header in enumerate(headers):
        _set_cell_text(dashboard.rows[0].cells[idx], header, bold=True, color=WHITE)
        _shade_cell(dashboard.rows[0].cells[idx], NAVY)
        _set_cell_text(dashboard.rows[1].cells[idx], values[idx], bold=(idx < 2))

    _add_section_heading(document, "2. Report Basis & Evidence Rules")
    document.add_paragraph(
        "This report combines Scope-of-Work requirements with uploaded site-photo evidence. "
        "A Scope item marked VERIFY has not yet been confirmed. A photo reference means the image "
        "contains directly relevant visible evidence; it does not prove concealed wiring, programming, "
        "commissioning, or compliance unless those conditions are directly observable."
    )

    _add_section_heading(document, "3. Scope Verification Register")
    scope_sections = _normalized_checklist_sections(checklist_data)
    if scope_sections:
        table = document.add_table(rows=1, cols=5)
        _format_table(table)
        headers = ["No.", "Scope / Verification Item", "Status", "Evidence / Notes", "Photo Ref."]
        for idx, header in enumerate(headers):
            _set_cell_text(table.rows[0].cells[idx], header, bold=True, color=WHITE)
            _shade_cell(table.rows[0].cells[idx], NAVY)
        _set_repeat_table_header(table.rows[0])

        item_no = 1
        for section_data in scope_sections:
            section_name = str(section_data.get("section") or "").strip()
            for item in section_data.get("items", []) or []:
                status = str(item.get("status") or "VERIFY").upper()
                row = table.add_row().cells
                item_text = str(item.get("item") or "").strip()
                values = [
                    item_no,
                    f"{section_name}: {item_text}" if section_name else item_text,
                    status,
                    item.get("notes") or "",
                    item.get("photo_ref") or "",
                ]
                for idx, value in enumerate(values):
                    _set_cell_text(row[idx], value, size=8.2)
                fill = _status_fill(status)
                if fill:
                    _shade_cell(row[2], fill)
                item_no += 1
    else:
        document.add_paragraph(
            "No Scope-derived verification register was available for this report."
        )

    _add_section_heading(document, "4. Visual Findings & Required Actions")
    findings = checklist_data.get("visual_findings") or visual.get("visual_findings", [])
    if findings:
        table = document.add_table(rows=1, cols=6)
        _format_table(table)
        headers = ["ID", "Photo", "Observation / Finding", "Confidence", "Status", "Required Follow-up"]
        for idx, header in enumerate(headers):
            _set_cell_text(table.rows[0].cells[idx], header, bold=True, color=WHITE)
            _shade_cell(table.rows[0].cells[idx], NAVY)
        _set_repeat_table_header(table.rows[0])

        for finding in findings:
            if not isinstance(finding, dict):
                continue
            status = str(finding.get("status") or "VERIFY").upper()
            row = table.add_row().cells
            values = [
                finding.get("id") or "",
                finding.get("source_photo_ref") or "",
                _compact_text(finding.get("finding"), 240),
                finding.get("confidence") or "",
                status,
                _compact_text(finding.get("required_action"), 240),
            ]
            for idx, value in enumerate(values):
                _set_cell_text(row[idx], value, size=8.2)
            fill = _status_fill(status)
            if fill:
                _shade_cell(row[4], fill)
    else:
        document.add_paragraph(
            "No visual observation requiring client-facing follow-up was identified from the current photo set."
        )

    _add_section_heading(document, "5. Deviations / Risks / Action Register")
    risk_rows = checklist_data.get("deviations_risks_actions", []) or []
    table = document.add_table(rows=1, cols=7)
    _format_table(table)
    headers = ["ID", "Photo", "Deviation / Risk / Observation", "Impact", "Required Action", "Owner", "Priority"]
    for idx, header in enumerate(headers):
        _set_cell_text(table.rows[0].cells[idx], header, bold=True, color=WHITE)
        _shade_cell(table.rows[0].cells[idx], NAVY)
    _set_repeat_table_header(table.rows[0])

    if risk_rows:
        for entry in risk_rows:
            if not isinstance(entry, dict):
                continue
            row = table.add_row().cells
            values = [
                entry.get("id") or "",
                entry.get("photo_ref") or "",
                _compact_text(entry.get("deviation_risk_missing_item") or entry.get("finding"), 220),
                _compact_text(entry.get("impact"), 180),
                _compact_text(entry.get("required_action"), 220),
                entry.get("owner") or "",
                entry.get("priority") or "",
            ]
            for idx, value in enumerate(values):
                _set_cell_text(row[idx], value, size=8.0)
    else:
        row = table.add_row().cells
        values = [
            "",
            "",
            "No deviation/action has been confirmed from the current visual evidence.",
            "",
            "Continue Scope verification and record confirmed deviations only.",
            "",
            "",
        ]
        for idx, value in enumerate(values):
            _set_cell_text(row[idx], value, size=8.2)

    _add_section_heading(document, "6. Outstanding Verification & Next Steps")
    verify_items = checklist_data.get("verification_items") or visual.get("verification_items", [])
    if verify_items:
        for item in verify_items:
            if not isinstance(item, dict):
                continue
            document.add_paragraph(
                f"• {item.get('source_photo_ref') or ''} "
                f"{_compact_text(item.get('item'), 240)}".strip()
            )
    else:
        document.add_paragraph(
            "No additional client-facing visual verification item remains outside the Scope checklist. "
            "Outstanding project verification is controlled through the Scope Verification Register above."
        )

    document.add_paragraph(
        "Next step: complete all outstanding Scope verification items, update statuses to PASS / OBSERVATION / ACTION / N/A as applicable, "
        "attach closure evidence, and obtain final project/client sign-off."
    )

    _add_final_report_photo_evidence(document, checklist_data)

    _add_section_heading(document, "8. Final Assessment")
    actions = int(visual_meta.get("actions") or 0)
    assessment = document.add_table(rows=0, cols=2)
    _format_table(assessment)
    rows = [
        ("Survey Status", survey_status),
        ("Visual Status", visual_status),
        (
            "Critical Blockers",
            "Visual action item(s) require immediate review."
            if actions
            else "No critical blocker is confirmed from the uploaded visual evidence.",
        ),
        (
            "Acceptance Position",
            "Not ready for final acceptance until outstanding VERIFY/ACTION items are closed."
            if survey_status not in {"READY FOR FINAL REVIEW", "PASS"}
            else "Ready for final review and sign-off.",
        ),
        (
            "Required Close-out",
            "Complete remaining field verification, attach closure evidence, and update the checklist before acceptance.",
        ),
    ]
    for label, value in rows:
        cells = assessment.add_row().cells
        _set_cell_text(cells[0], label, bold=True)
        _shade_cell(cells[0], LIGHT_GRAY)
        _set_cell_text(cells[1], value)

    _add_section_heading(document, "9. Sign-off")
    sign_table = document.add_table(rows=5, cols=2)
    _format_table(sign_table)
    for row, values in zip(
        sign_table.rows,
        [
            ("Surveyed By", ""),
            ("Project / Engineering Review", ""),
            ("Client Representative", ""),
            ("Date", ""),
            ("Final Acceptance", "☐ Accepted   ☐ Accepted with actions   ☐ Not accepted"),
        ],
    ):
        _set_cell_text(row.cells[0], values[0], bold=True)
        _shade_cell(row.cells[0], LIGHT_GRAY)
        _set_cell_text(row.cells[1], values[1])

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
