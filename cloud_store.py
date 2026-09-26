from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


metadata = MetaData()

projects = Table(
    "projects",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("owner_id", String(255), nullable=False, index=True),
    Column("name", String(255), nullable=False),
    Column("location", String(255)),
    Column("client", String(255)),
    Column("opportunity_number", String(128)),
    Column("phase", String(128), nullable=False),
    Column("status", String(32), nullable=False, default="active"),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("created_at", String(64), nullable=False),
    Column("updated_at", String(64), nullable=False),
)

progress_entries = Table(
    "progress_entries",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("project_id", String(64), nullable=False, index=True),
    Column("entry_date", String(16), nullable=False, index=True),
    Column("phase", String(128)),
    Column("rooms_json", Text, nullable=False, default="[]"),
    Column("completed_json", Text, nullable=False, default="[]"),
    Column("in_progress_json", Text, nullable=False, default="[]"),
    Column("issues_json", Text, nullable=False, default="[]"),
    Column("blockers_json", Text, nullable=False, default="[]"),
    Column("next_actions_json", Text, nullable=False, default="[]"),
    Column("responsible_parties_json", Text, nullable=False, default="[]"),
    Column("notes", Text),
    Column("created_at", String(64), nullable=False),
    Column("updated_at", String(64), nullable=False),
)

drawing_analyses = Table(
    "drawing_analyses",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("project_id", String(64), nullable=False, index=True),
    Column("file_name", String(512), nullable=False),
    Column("file_hash", String(128)),
    Column("page_count", Integer, nullable=False, default=0),
    Column("register_json", Text, nullable=False, default="{}"),
    Column("qa_json", Text, nullable=False, default="{}"),
    Column("created_at", String(64), nullable=False),
)

generated_reports = Table(
    "generated_reports",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("project_id", String(64), nullable=False, index=True),
    Column("period", String(32), nullable=False),
    Column("anchor_date", String(16), nullable=False),
    Column("payload_json", Text, nullable=False, default="{}"),
    Column("created_at", String(64), nullable=False),
)


class SqlAlchemyProjectStore:
    """Portable project store for managed PostgreSQL and SQLAlchemy-compatible DBs."""

    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("database_url is required")
        self.database_url = database_url
        self.engine: Engine = create_engine(
            database_url,
            pool_pre_ping=True,
            future=True,
        )
        metadata.create_all(self.engine)

    @staticmethod
    def _project(row: Any) -> dict:
        data = dict(row._mapping if hasattr(row, "_mapping") else row)
        return {
            "id": data["id"],
            "owner_id": data["owner_id"],
            "name": data["name"],
            "location": data.get("location"),
            "client": data.get("client"),
            "opportunity_number": data.get("opportunity_number"),
            "phase": data["phase"],
            "status": data["status"],
            "metadata": _json_loads(data.get("metadata_json"), {}),
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
        }

    @staticmethod
    def _progress(row: Any) -> dict:
        data = dict(row._mapping if hasattr(row, "_mapping") else row)
        return {
            "id": data["id"],
            "project_id": data["project_id"],
            "date": data["entry_date"],
            "phase": data.get("phase"),
            "rooms": _json_loads(data.get("rooms_json"), []),
            "completed": _json_loads(data.get("completed_json"), []),
            "in_progress": _json_loads(data.get("in_progress_json"), []),
            "issues": _json_loads(data.get("issues_json"), []),
            "blockers": _json_loads(data.get("blockers_json"), []),
            "next_actions": _json_loads(data.get("next_actions_json"), []),
            "responsible_parties": _json_loads(
                data.get("responsible_parties_json"), []
            ),
            "notes": data.get("notes"),
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
        }

    def create_project(
        self,
        *,
        name: str,
        phase: str,
        owner_id: str = "local-dev",
        location: str | None = None,
        client: str | None = None,
        opportunity_number: str | None = None,
        status: str = "active",
        metadata: dict | None = None,
    ) -> dict:
        project_id = str(uuid.uuid4())
        now = _utc_now()
        values = {
            "id": project_id,
            "owner_id": owner_id,
            "name": name.strip(),
            "location": location,
            "client": client,
            "opportunity_number": opportunity_number,
            "phase": phase,
            "status": status,
            "metadata_json": _json_dumps(metadata or {}),
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as conn:
            conn.execute(insert(projects).values(**values))
            row = conn.execute(
                select(projects).where(projects.c.id == project_id)
            ).one()
        return self._project(row)

    def list_projects(
        self,
        status: str | None = None,
        owner_id: str | None = None,
    ) -> list[dict]:
        stmt = select(projects)
        if owner_id is not None:
            stmt = stmt.where(projects.c.owner_id == owner_id)
        if status:
            stmt = stmt.where(projects.c.status == status)
        stmt = stmt.order_by(projects.c.updated_at.desc())
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).all()
        return [self._project(row) for row in rows]

    def get_project(
        self,
        project_id: str,
        owner_id: str | None = None,
    ) -> dict | None:
        stmt = select(projects).where(projects.c.id == project_id)
        if owner_id is not None:
            stmt = stmt.where(projects.c.owner_id == owner_id)
        with self.engine.begin() as conn:
            row = conn.execute(stmt).first()
        return self._project(row) if row else None

    def update_project(
        self,
        project_id: str,
        *,
        name: str | None = None,
        location: str | None = None,
        client: str | None = None,
        opportunity_number: str | None = None,
        phase: str | None = None,
        status: str | None = None,
        metadata: dict | None = None,
        owner_id: str | None = None,
    ) -> dict | None:
        current = self.get_project(project_id, owner_id=owner_id)
        if not current:
            return None
        values = {
            "name": name if name is not None else current["name"],
            "location": location if location is not None else current["location"],
            "client": client if client is not None else current["client"],
            "opportunity_number": (
                opportunity_number
                if opportunity_number is not None
                else current["opportunity_number"]
            ),
            "phase": phase if phase is not None else current["phase"],
            "status": status if status is not None else current["status"],
            "metadata_json": _json_dumps(
                metadata if metadata is not None else current["metadata"]
            ),
            "updated_at": _utc_now(),
        }
        with self.engine.begin() as conn:
            conn.execute(
                update(projects)
                .where(projects.c.id == project_id)
                .values(**values)
            )
            row = conn.execute(
                select(projects).where(projects.c.id == project_id)
            ).first()
        return self._project(row) if row else None

    def delete_project(
        self,
        project_id: str,
        owner_id: str | None = None,
    ) -> bool:
        stmt = delete(projects).where(projects.c.id == project_id)
        if owner_id is not None:
            stmt = stmt.where(projects.c.owner_id == owner_id)
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
            if result.rowcount:
                conn.execute(
                    delete(progress_entries).where(
                        progress_entries.c.project_id == project_id
                    )
                )
                conn.execute(
                    delete(drawing_analyses).where(
                        drawing_analyses.c.project_id == project_id
                    )
                )
                conn.execute(
                    delete(generated_reports).where(
                        generated_reports.c.project_id == project_id
                    )
                )
        return bool(result.rowcount)

    def add_progress_entry(
        self,
        project_id: str,
        *,
        entry_date: str,
        phase: str | None = None,
        rooms: list[str] | None = None,
        completed: list[str] | None = None,
        in_progress: list[str] | None = None,
        issues: list[str] | None = None,
        blockers: list[str] | None = None,
        next_actions: list[str] | None = None,
        responsible_parties: list[str] | None = None,
        notes: str | None = None,
    ) -> dict:
        if not self.get_project(project_id):
            raise KeyError(project_id)
        entry_id = str(uuid.uuid4())
        now = _utc_now()
        values = {
            "id": entry_id,
            "project_id": project_id,
            "entry_date": entry_date,
            "phase": phase,
            "rooms_json": _json_dumps(rooms or []),
            "completed_json": _json_dumps(completed or []),
            "in_progress_json": _json_dumps(in_progress or []),
            "issues_json": _json_dumps(issues or []),
            "blockers_json": _json_dumps(blockers or []),
            "next_actions_json": _json_dumps(next_actions or []),
            "responsible_parties_json": _json_dumps(
                responsible_parties or []
            ),
            "notes": notes,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as conn:
            conn.execute(insert(progress_entries).values(**values))
            conn.execute(
                update(projects)
                .where(projects.c.id == project_id)
                .values(updated_at=now)
            )
            row = conn.execute(
                select(progress_entries).where(
                    progress_entries.c.id == entry_id
                )
            ).one()
        return self._progress(row)

    def list_progress_entries(
        self,
        project_id: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        stmt = select(progress_entries).where(
            progress_entries.c.project_id == project_id
        )
        if start_date:
            stmt = stmt.where(progress_entries.c.entry_date >= start_date)
        if end_date:
            stmt = stmt.where(progress_entries.c.entry_date <= end_date)
        stmt = stmt.order_by(
            progress_entries.c.entry_date.asc(),
            progress_entries.c.created_at.asc(),
        )
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).all()
        return [self._progress(row) for row in rows]

    def save_drawing_analysis(
        self,
        project_id: str,
        *,
        file_name: str,
        page_count: int,
        register: dict,
        qa: dict,
        file_hash: str | None = None,
    ) -> dict:
        if not self.get_project(project_id):
            raise KeyError(project_id)
        analysis_id = str(uuid.uuid4())
        now = _utc_now()
        values = {
            "id": analysis_id,
            "project_id": project_id,
            "file_name": file_name,
            "file_hash": file_hash,
            "page_count": int(page_count),
            "register_json": _json_dumps(register),
            "qa_json": _json_dumps(qa),
            "created_at": now,
        }
        with self.engine.begin() as conn:
            conn.execute(insert(drawing_analyses).values(**values))
            conn.execute(
                update(projects)
                .where(projects.c.id == project_id)
                .values(updated_at=now)
            )
        return {
            "id": analysis_id,
            "project_id": project_id,
            "file_name": file_name,
            "file_hash": file_hash,
            "page_count": int(page_count),
            "register": register,
            "qa": qa,
            "created_at": now,
        }

    def list_drawing_analyses(self, project_id: str) -> list[dict]:
        stmt = (
            select(drawing_analyses)
            .where(drawing_analyses.c.project_id == project_id)
            .order_by(drawing_analyses.c.created_at.desc())
        )
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).all()
        output = []
        for row in rows:
            data = dict(row._mapping)
            output.append(
                {
                    "id": data["id"],
                    "project_id": data["project_id"],
                    "file_name": data["file_name"],
                    "file_hash": data.get("file_hash"),
                    "page_count": int(data.get("page_count") or 0),
                    "register": _json_loads(data.get("register_json"), {}),
                    "qa": _json_loads(data.get("qa_json"), {}),
                    "created_at": data["created_at"],
                }
            )
        return output

    def save_report(
        self,
        project_id: str,
        *,
        period: str,
        anchor_date: str,
        payload: dict,
    ) -> dict:
        if not self.get_project(project_id):
            raise KeyError(project_id)
        report_id = str(uuid.uuid4())
        now = _utc_now()
        values = {
            "id": report_id,
            "project_id": project_id,
            "period": period,
            "anchor_date": anchor_date,
            "payload_json": _json_dumps(payload),
            "created_at": now,
        }
        with self.engine.begin() as conn:
            conn.execute(insert(generated_reports).values(**values))
        return {
            "id": report_id,
            "project_id": project_id,
            "period": period,
            "anchor_date": anchor_date,
            "payload": payload,
            "created_at": now,
        }

    def get_report(
        self,
        project_id: str,
        report_id: str,
    ) -> dict | None:
        stmt = select(generated_reports).where(
            generated_reports.c.project_id == project_id,
            generated_reports.c.id == report_id,
        )
        with self.engine.begin() as conn:
            row = conn.execute(stmt).first()
        if not row:
            return None
        data = dict(row._mapping)
        return {
            "id": data["id"],
            "project_id": data["project_id"],
            "period": data["period"],
            "anchor_date": data["anchor_date"],
            "payload": _json_loads(data.get("payload_json"), {}),
            "created_at": data["created_at"],
        }

    def list_reports(self, project_id: str) -> list[dict]:
        stmt = (
            select(generated_reports)
            .where(generated_reports.c.project_id == project_id)
            .order_by(generated_reports.c.created_at.desc())
        )
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).all()
        output = []
        for row in rows:
            data = dict(row._mapping)
            output.append(
                {
                    "id": data["id"],
                    "project_id": data["project_id"],
                    "period": data["period"],
                    "anchor_date": data["anchor_date"],
                    "payload": _json_loads(data.get("payload_json"), {}),
                    "created_at": data["created_at"],
                }
            )
        return output

    def project_snapshot(
        self,
        project_id: str,
        owner_id: str | None = None,
    ) -> dict | None:
        project = self.get_project(project_id, owner_id=owner_id)
        if not project:
            return None
        return {
            "project": project,
            "progress_entries": self.list_progress_entries(project_id),
            "drawing_analyses": self.list_drawing_analyses(project_id),
            "reports": self.list_reports(project_id),
        }


def _normalize_database_url(database_url: str) -> str:
    value = str(database_url or "").strip()
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


def create_project_store():
    database_url = os.getenv("AVIA_DATABASE_URL", "").strip()
    if database_url:
        return SqlAlchemyProjectStore(
            _normalize_database_url(database_url)
        )

    from project_store import ProjectStore

    return ProjectStore()
