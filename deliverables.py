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
WHITE = "FFFFFF"


def _shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def _set_cell_text(cell, text: Any, *, bold: bool = False, color: str | None = None) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run("" if text is None else str(text))
    run.bold = bold
    run.font.size = Pt(9)
    if color:
        run.font.color.rgb = __import__("docx").shared.RGBColor.from_string(color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _add_section_heading(document: Document, title: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(10)
    paragraph.paragraph_format.space_after = Pt(5)
    run = paragraph.add_run(title)
    run.bold = True
    run.font.size = Pt(13)
    run.font.color.rgb = __import__("docx").shared.RGBColor.from_string(NAVY)


def _status_summary(checklist_data: dict[str, Any]) -> dict[str, int]:
    counts = {"PASS": 0, "VERIFY": 0, "ACTION": 0, "N/A": 0, "OTHER": 0}
    for section in checklist_data.get("checklist_sections", []) or []:
        if not isinstance(section, dict):
            continue
        for item in section.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "VERIFY").strip().upper()
            if status not in counts:
                status = "OTHER"
            counts[status] += 1
    return counts


def build_site_survey_report_docx(checklist_data: dict[str, Any]) -> bytes | None:
    if not isinstance(checklist_data, dict):
        return None

    project_info = checklist_data.get("project_info") or {}
    project_name = str(project_info.get("project_name") or "AV Site Survey").strip()
    client = str(project_info.get("client") or "").strip()
    location = str(project_info.get("location") or "").strip()
    rooms = [
        str(item).strip()
        for item in checklist_data.get("rooms_areas", []) or []
        if str(item).strip()
    ]

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)

    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(9.5)

    cover = document.add_paragraph()
    cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cover.add_run("AV SITE SURVEY REPORT")
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = __import__("docx").shared.RGBColor.from_string(NAVY)

    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(project_name)
    run.bold = True
    run.font.size = Pt(15)
    run.font.color.rgb = __import__("docx").shared.RGBColor.from_string(BLUE)

    status_note = document.add_paragraph()
    status_note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = status_note.add_run(
        "Draft / Pre-Survey Report – VERIFY items require confirmation during the site survey."
    )
    run.italic = True
    run.font.size = Pt(9)

    document.add_paragraph()

    info_table = document.add_table(rows=0, cols=2)
    info_table.style = "Table Grid"
    info_rows = [
        ("Project", project_name),
        ("Client", client),
        ("Location", location),
        ("Rooms / Areas", ", ".join(rooms)),
        ("Document Status", "Draft / Pre-Survey"),
    ]
    for label, value in info_rows:
        if not value:
            continue
        cells = info_table.add_row().cells
        _set_cell_text(cells[0], label, bold=True, color=WHITE)
        _shade_cell(cells[0], NAVY)
        _set_cell_text(cells[1], value)

    _add_section_heading(document, "1. Executive Summary")
    counts = _status_summary(checklist_data)
    summary_text = (
        f"This report has been prepared from the available project scope and survey checklist "
        f"for {project_name}. It is intended to organize site verification and close-out actions "
        f"before final handover or implementation. Current checklist status: "
        f"{counts['PASS']} PASS, {counts['VERIFY']} VERIFY, {counts['ACTION']} ACTION, "
        f"{counts['N/A']} N/A."
    )
    document.add_paragraph(summary_text)

    _add_section_heading(document, "2. Survey Scope")
    if rooms:
        document.add_paragraph(
            "The survey covers the following rooms / areas: " + ", ".join(rooms) + "."
        )
    else:
        document.add_paragraph(
            "Rooms / areas are to be confirmed against the approved project documentation."
        )
    document.add_paragraph(
        "All VERIFY items below require physical confirmation on site. The report must not be "
        "treated as confirmation of existing site conditions until those items are completed."
    )

    _add_section_heading(document, "3. Findings and Verification Status")
    findings = document.add_table(rows=1, cols=5)
    findings.style = "Table Grid"
    headers = ["Section", "Survey Item", "Status", "Notes / Evidence", "Action Required"]
    for index, header in enumerate(headers):
        _set_cell_text(findings.rows[0].cells[index], header, bold=True, color=WHITE)
        _shade_cell(findings.rows[0].cells[index], NAVY)

    for section_data in checklist_data.get("checklist_sections", []) or []:
        if not isinstance(section_data, dict):
            continue
        section_name = str(section_data.get("section") or "").strip()
        for item in section_data.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "VERIFY").strip().upper()
            notes = str(item.get("notes") or "").strip()
            action = ""
            if status == "VERIFY":
                action = "Verify on site"
            elif status == "ACTION":
                action = "Corrective action / coordination required"
            row = findings.add_row().cells
            values = [
                section_name,
                item.get("item") or "",
                status,
                notes,
                action,
            ]
            for idx, value in enumerate(values):
                _set_cell_text(row[idx], value)
            if status == "VERIFY":
                _shade_cell(row[2], LIGHT_BLUE)
            elif status == "ACTION":
                _shade_cell(row[2], "FCE4D6")
            elif status == "PASS":
                _shade_cell(row[2], "E2F0D9")

    _add_section_heading(document, "4. Required Site Photos / Evidence")
    required_photos = checklist_data.get("required_photos", []) or []
    if required_photos:
        for item in required_photos:
            document.add_paragraph(f"☐ {item}")
    else:
        document.add_paragraph(
            "Photo evidence requirements are to be confirmed during the survey."
        )

    photo_register = checklist_data.get("photo_register", []) or []
    if photo_register:
        table = document.add_table(rows=1, cols=4)
        table.style = "Table Grid"
        for idx, header in enumerate(["Photo", "Subject / Area", "Status", "Notes"]):
            _set_cell_text(table.rows[0].cells[idx], header, bold=True, color=WHITE)
            _shade_cell(table.rows[0].cells[idx], NAVY)

        for entry in photo_register:
            row = table.add_row().cells
            if isinstance(entry, dict):
                values = [
                    entry.get("photo_number") or "",
                    entry.get("photo_subject") or entry.get("subject") or "",
                    entry.get("status") or "PENDING",
                    entry.get("photo_notes") or entry.get("notes") or "",
                ]
            else:
                values = ["", str(entry), "PENDING", ""]
            for idx, value in enumerate(values):
                _set_cell_text(row[idx], value)

    _add_section_heading(document, "5. Open Items / Follow-up")
    open_items = checklist_data.get("open_items", []) or []
    if open_items:
        for item in open_items:
            document.add_paragraph(f"• {item}")
    else:
        document.add_paragraph(
            "No open items have been recorded yet. Update this section after site verification."
        )

    _add_section_heading(document, "6. Recommendations / Next Actions")
    document.add_paragraph(
        "• Complete all VERIFY items and attach supporting photo or measurement evidence where applicable."
    )
    document.add_paragraph(
        "• Convert unresolved items to ACTION with a named owner, target date, and closure evidence."
    )
    document.add_paragraph(
        "• Confirm any deviation from the design documentation before installation, programming, or handover."
    )
    document.add_paragraph(
        "• Issue the final report only after the observed site condition has been reconciled with the approved scope."
    )

    _add_section_heading(document, "7. Sign-off")
    sign_table = document.add_table(rows=4, cols=2)
    sign_table.style = "Table Grid"
    sign_rows = [
        ("Surveyed By", ""),
        ("Project / Engineering Review", ""),
        ("Client Representative", ""),
        ("Date", ""),
    ]
    for row, values in zip(sign_table.rows, sign_rows):
        _set_cell_text(row.cells[0], values[0], bold=True)
        _shade_cell(row.cells[0], LIGHT_GRAY)
        _set_cell_text(row.cells[1], values[1])

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
