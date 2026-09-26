from __future__ import annotations

from datetime import date
from io import BytesIO

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pypdf import PdfReader

from project_engineer import (
    build_progress_report,
    build_project_drawing_register,
)


APP_VERSION = "0.1.0"

app = FastAPI(
    title="AV Intelligence Assistant API",
    version=APP_VERSION,
    description=(
        "Production API for AV project intelligence, drawing analysis, "
        "project tracking, reporting, commissioning, and future vendor programming."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProgressEntry(BaseModel):
    date: str
    phase: str | None = None
    rooms: list[str] = Field(default_factory=list)
    completed: list[str] = Field(default_factory=list)
    in_progress: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class ReportRequest(BaseModel):
    period: str = Field(pattern="^(daily|weekly|monthly)$")
    anchor_date: date | None = None
    project: dict = Field(default_factory=dict)
    entries: list[ProgressEntry] = Field(default_factory=list)


def _pdf_to_pages(file_name: str, payload: bytes) -> list[dict]:
    try:
        reader = PdfReader(BytesIO(payload))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid PDF: {exc}") from exc

    pages: list[dict] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(
            {
                "page_number": index,
                "source": file_name,
                "text": text,
            }
        )
    return pages


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "av-intelligence-assistant-api",
        "version": APP_VERSION,
    }


@app.get("/v1/capabilities")
def capabilities() -> dict:
    return {
        "drawing_intelligence": {
            "full_pdf_register": True,
            "room_detection": True,
            "coordination_requirements": True,
            "risk_flags": True,
            "connection_graph": "planned",
            "design_error_detection": "planned",
        },
        "project_lifecycle": {
            "phases": [
                "Design Review / Pre-Start",
                "First Fix",
                "Second Fix / Device Installation",
                "Configuration / Programming",
                "Testing / Commissioning",
                "Client Training",
                "Snag Closure",
                "Handover",
            ],
            "daily_reports": True,
            "weekly_reports": True,
            "monthly_reports": True,
            "persistent_project_memory": "planned",
        },
        "vendor_programming": {
            "Extron": "planned",
            "Crestron": "planned",
            "Q-SYS": "planned",
            "Lightware": "planned",
            "Biamp": "planned",
            "Barco": "planned",
            "Samsung": "planned",
        },
    }


@app.post("/v1/drawings/register")
async def analyze_drawing_register(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A PDF file is required.")

    content_type = (file.content_type or "").lower()
    if "pdf" not in content_type and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF drawing sets are supported.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")

    pages = _pdf_to_pages(file.filename, payload)
    register = build_project_drawing_register(pages)
    return {
        "file_name": file.filename,
        "page_count": len(pages),
        "register": register,
    }


@app.post("/v1/reports/progress")
def build_report(request: ReportRequest) -> dict:
    entries = [entry.model_dump() for entry in request.entries]
    return build_progress_report(
        entries,
        period=request.period,
        anchor_date=request.anchor_date or date.today(),
        project=request.project,
    )
