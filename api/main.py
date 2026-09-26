from __future__ import annotations

import hashlib
from datetime import date
from io import BytesIO

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pypdf import PdfReader

from api.auth_context import AuthUser, auth_capabilities, get_current_user
from drawing_qa import audit_drawing_set
from drawing_visual import analyze_visual_drawing_pages, reconcile_visual_with_connection_graph
from project_engineer import (
    PROJECT_PHASES,
    build_progress_report,
    build_project_drawing_register,
)
from project_store import ProjectStore
from project_plan import build_phase_engineering_plan
from project_dashboard import build_project_dashboard
from professional_reports import build_professional_project_report


APP_VERSION = "0.2.0"
store = ProjectStore()

app = FastAPI(
    title="AV Intelligence Assistant API",
    version=APP_VERSION,
    description=(
        "Production API for AV project intelligence, drawing analysis, "
        "persistent project tracking, reporting, commissioning, and future vendor programming."
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
    responsible_parties: list[str] = Field(default_factory=list)
    notes: str | None = None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    client: str | None = Field(default=None, max_length=200)
    opportunity_number: str | None = Field(default=None, max_length=100)
    phase: str = PROJECT_PHASES[0]
    metadata: dict = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    client: str | None = Field(default=None, max_length=200)
    opportunity_number: str | None = Field(default=None, max_length=100)
    phase: str | None = None
    status: str | None = Field(default=None, pattern="^(active|on_hold|completed|archived)$")
    metadata: dict | None = None


class ReportRequest(BaseModel):
    period: str = Field(pattern="^(daily|weekly|monthly)$")
    anchor_date: date | None = None
    project: dict = Field(default_factory=dict)
    entries: list[ProgressEntry] = Field(default_factory=list)


def _validate_phase(phase: str | None) -> None:
    if phase is not None and phase not in PROJECT_PHASES:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Unsupported project phase.",
                "allowed_phases": list(PROJECT_PHASES),
            },
        )


def _require_project(project_id: str, owner_id: str) -> dict:
    project = store.get_project(project_id, owner_id=owner_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


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


async def _read_pdf(file: UploadFile) -> tuple[bytes, list[dict]]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A PDF file is required.")

    content_type = (file.content_type or "").lower()
    if "pdf" not in content_type and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF drawing sets are supported.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")

    return payload, _pdf_to_pages(file.filename, payload)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "av-intelligence-assistant-api",
        "version": APP_VERSION,
        "persistence": "sqlite",
        "auth": auth_capabilities(),
    }


@app.get("/v1/capabilities")
def capabilities() -> dict:
    return {
        "drawing_intelligence": {
            "full_pdf_register": True,
            "room_detection": True,
            "coordination_requirements": True,
            "risk_flags": True,
            "connection_graph": "beta",
            "design_error_detection": "beta",
            "visual_deep_review": "beta",
        },
        "project_lifecycle": {
            "phases": list(PROJECT_PHASES),
            "daily_reports": True,
            "weekly_reports": True,
            "monthly_reports": True,
            "final_handover_report": True,
            "professional_reports_v2": True,
            "persistent_project_memory": True,
            "phase_engineering_plan": True,
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


@app.post("/v1/projects", status_code=201)
def create_project(
    request: ProjectCreate,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    _validate_phase(request.phase)
    return store.create_project(
        name=request.name,
        owner_id=user.id,
        location=request.location,
        client=request.client,
        opportunity_number=request.opportunity_number,
        phase=request.phase,
        metadata=request.metadata,
    )


@app.get("/v1/projects")
def list_projects(
    status: str | None = Query(default=None),
    user: AuthUser = Depends(get_current_user),
) -> dict:
    return {
        "projects": store.list_projects(status=status, owner_id=user.id)
    }


@app.get("/v1/projects/{project_id}")
def get_project(
    project_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    snapshot = store.project_snapshot(project_id, owner_id=user.id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Project not found.")
    return snapshot


@app.get("/v1/projects/{project_id}/plan")
def get_project_engineering_plan(project_id: str,
    user: AuthUser = Depends(get_current_user),) -> dict:
    snapshot = store.project_snapshot(project_id, owner_id=user.id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Project not found.")
    return build_phase_engineering_plan(snapshot)


@app.get("/v1/projects/{project_id}/dashboard")
def get_project_dashboard(
    project_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    snapshot = store.project_snapshot(project_id, owner_id=user.id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Project not found.")
    return build_project_dashboard(snapshot)


@app.patch("/v1/projects/{project_id}")
def update_project(
    project_id: str,
    request: ProjectUpdate,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    _require_project(project_id, user.id)
    _validate_phase(request.phase)
    project = store.update_project(
        project_id,
        name=request.name,
        location=request.location,
        client=request.client,
        opportunity_number=request.opportunity_number,
        phase=request.phase,
        status=request.status,
        metadata=request.metadata,
        owner_id=user.id,
    )
    return project


@app.delete("/v1/projects/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    user: AuthUser = Depends(get_current_user),
) -> None:
    if not store.delete_project(project_id, owner_id=user.id):
        raise HTTPException(status_code=404, detail="Project not found.")


@app.post("/v1/projects/{project_id}/progress", status_code=201)
def add_project_progress(project_id: str, request: ProgressEntry,
    user: AuthUser = Depends(get_current_user),) -> dict:
    _require_project(project_id, user.id)
    _validate_phase(request.phase)
    return store.add_progress_entry(
        project_id,
        entry_date=request.date,
        phase=request.phase,
        rooms=request.rooms,
        completed=request.completed,
        in_progress=request.in_progress,
        issues=request.issues,
        blockers=request.blockers,
        next_actions=request.next_actions,
        responsible_parties=request.responsible_parties,
        notes=request.notes,
    )


@app.get("/v1/projects/{project_id}/progress")
def project_progress(
    project_id: str,
    start_date: str | None = None,
    end_date: str | None = None,

    user: AuthUser = Depends(get_current_user),) -> dict:
    _require_project(project_id, user.id)
    return {
        "entries": store.list_progress_entries(
            project_id,
            start_date=start_date,
            end_date=end_date,
        )
    }


@app.post("/v1/drawings/register")
async def analyze_drawing_register(
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
) -> dict:
    _, pages = await _read_pdf(file)
    register = build_project_drawing_register(pages)
    return {
        "file_name": file.filename,
        "page_count": len(pages),
        "register": register,
    }


@app.post("/v1/drawings/qa")
async def analyze_drawing_qa(
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
) -> dict:
    _, pages = await _read_pdf(file)
    return {
        "file_name": file.filename,
        "page_count": len(pages),
        "register": build_project_drawing_register(pages),
        "qa": audit_drawing_set(pages),
    }


@app.post("/v1/projects/{project_id}/drawings/qa", status_code=201)
async def analyze_and_save_project_drawing(
    project_id: str,
    file: UploadFile = File(...),

    user: AuthUser = Depends(get_current_user),) -> dict:
    _require_project(project_id, user.id)
    payload, pages = await _read_pdf(file)
    register = build_project_drawing_register(pages)
    qa = audit_drawing_set(pages)
    saved = store.save_drawing_analysis(
        project_id,
        file_name=file.filename or "drawing.pdf",
        file_hash=hashlib.sha256(payload).hexdigest(),
        page_count=len(pages),
        register=register,
        qa=qa,
    )
    return saved


@app.post("/v1/projects/{project_id}/drawings/qa-visual", status_code=201)
async def analyze_and_save_project_drawing_visual(
    project_id: str,
    file: UploadFile = File(...),
    max_pages: int = Query(default=6, ge=1, le=12),
    regions_per_page: int = Query(default=4, ge=1, le=4),

    user: AuthUser = Depends(get_current_user),) -> dict:
    _require_project(project_id, user.id)
    payload, pages = await _read_pdf(file)
    register = build_project_drawing_register(pages)
    qa = audit_drawing_set(pages)

    try:
        visual_review = analyze_visual_drawing_pages(
            file_name=file.filename or "drawing.pdf",
            payload=payload,
            document_pages=pages,
            qa=qa,
            max_pages=max_pages,
            regions_per_page=regions_per_page,
        )
    except RuntimeError as exc:
        message = str(exc)
        status_code = 503 if "HF_TOKEN" in message else 502
        raise HTTPException(status_code=status_code, detail=message) from exc

    qa["visual_review"] = visual_review
    reconciliation = reconcile_visual_with_connection_graph(qa, visual_review)
    qa["visual_reconciliation"] = reconciliation
    if reconciliation.get("conflicts"):
        qa.setdefault("findings", []).extend(
            {
                "severity": item.get("severity", "high"),
                "status": "REVIEW",
                "category": "visual_graph_conflict",
                "title": item.get("title"),
                "why_it_matters": item.get("why_it_matters"),
                "recommended_action": item.get("recommended_action"),
                "evidence": [
                    item.get("text") or {},
                    item.get("visual") or {},
                ],
            }
            for item in reconciliation["conflicts"]
        )
        qa["finding_count"] = len(qa.get("findings") or [])
    saved = store.save_drawing_analysis(
        project_id,
        file_name=file.filename or "drawing.pdf",
        file_hash=hashlib.sha256(payload).hexdigest(),
        page_count=len(pages),
        register=register,
        qa=qa,
    )
    return saved


@app.get("/v1/projects/{project_id}/drawings")
def list_project_drawings(project_id: str,
    user: AuthUser = Depends(get_current_user),) -> dict:
    _require_project(project_id, user.id)
    return {"drawing_analyses": store.list_drawing_analyses(project_id)}


@app.post("/v1/reports/progress")
def build_report(request: ReportRequest) -> dict:
    entries = [entry.model_dump() for entry in request.entries]
    return build_progress_report(
        entries,
        period=request.period,
        anchor_date=request.anchor_date or date.today(),
        project=request.project,
    )


@app.post("/v1/projects/{project_id}/reports/{period}", status_code=201)
def build_and_save_project_report(
    project_id: str,
    period: str,
    anchor_date: date | None = None,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    if period not in {"daily", "weekly", "monthly", "final"}:
        raise HTTPException(
            status_code=422,
            detail="period must be daily, weekly, monthly, or final",
        )

    snapshot = store.project_snapshot(project_id, owner_id=user.id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Project not found.")

    report_date = anchor_date or date.today()
    report = build_professional_project_report(
        snapshot,
        period=period,
        anchor_date=report_date,
    )
    return store.save_report(
        project_id,
        period=period,
        anchor_date=report_date.isoformat(),
        payload=report,
    )


@app.get("/v1/projects/{project_id}/reports")
def list_project_reports(project_id: str,
    user: AuthUser = Depends(get_current_user),) -> dict:
    _require_project(project_id, user.id)
    return {"reports": store.list_reports(project_id)}
