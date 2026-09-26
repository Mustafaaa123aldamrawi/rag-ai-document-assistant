from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 2
DEFAULT_DB_PATH = os.getenv("AVIA_DATABASE_PATH", "data/av_intelligence.db")
_DB_LOCK = threading.RLock()


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


class ProjectStore:
    """SQLite-backed persistent store for AV project lifecycle data.

    The store intentionally uses only Python's stdlib so it can run locally,
    in CI, and in a lightweight API container. The database path is configurable
    through AVIA_DATABASE_PATH and can later be replaced by a managed database
    without changing the API contract.
    """

    def __init__(self, db_path: str | os.PathLike[str] | None = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with _DB_LOCK:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL DEFAULT 'local-dev',
                    name TEXT NOT NULL,
                    location TEXT,
                    client TEXT,
                    opportunity_number TEXT,
                    phase TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS progress_entries (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    entry_date TEXT NOT NULL,
                    phase TEXT,
                    rooms_json TEXT NOT NULL DEFAULT '[]',
                    completed_json TEXT NOT NULL DEFAULT '[]',
                    in_progress_json TEXT NOT NULL DEFAULT '[]',
                    issues_json TEXT NOT NULL DEFAULT '[]',
                    blockers_json TEXT NOT NULL DEFAULT '[]',
                    next_actions_json TEXT NOT NULL DEFAULT '[]',
                    responsible_parties_json TEXT NOT NULL DEFAULT '[]',
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS drawing_analyses (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_hash TEXT,
                    page_count INTEGER NOT NULL DEFAULT 0,
                    register_json TEXT NOT NULL DEFAULT '{}',
                    qa_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS generated_reports (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    period TEXT NOT NULL,
                    anchor_date TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_progress_project_date
                    ON progress_entries(project_id, entry_date);
                CREATE INDEX IF NOT EXISTS idx_drawings_project_created
                    ON drawing_analyses(project_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_reports_project_created
                    ON generated_reports(project_id, created_at);
                """
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(projects)").fetchall()
            }
            if "owner_id" not in columns:
                conn.execute(
                    "ALTER TABLE projects ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'local-dev'"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_projects_owner_updated ON projects(owner_id, updated_at)"
                )

            conn.execute(
                """
                INSERT INTO schema_meta(key, value)
                VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (str(SCHEMA_VERSION),),
            )

    @staticmethod
    def _project_from_row(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "owner_id": row["owner_id"],
            "name": row["name"],
            "location": row["location"],
            "client": row["client"],
            "opportunity_number": row["opportunity_number"],
            "phase": row["phase"],
            "status": row["status"],
            "metadata": _json_loads(row["metadata_json"], {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _progress_from_row(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "date": row["entry_date"],
            "phase": row["phase"],
            "rooms": _json_loads(row["rooms_json"], []),
            "completed": _json_loads(row["completed_json"], []),
            "in_progress": _json_loads(row["in_progress_json"], []),
            "issues": _json_loads(row["issues_json"], []),
            "blockers": _json_loads(row["blockers_json"], []),
            "next_actions": _json_loads(row["next_actions_json"], []),
            "responsible_parties": _json_loads(
                row["responsible_parties_json"], []
            ),
            "notes": row["notes"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
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
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO projects(
                    id, owner_id, name, location, client, opportunity_number, phase,
                    status, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    owner_id,
                    name.strip(),
                    location,
                    client,
                    opportunity_number,
                    phase,
                    status,
                    _json_dumps(metadata or {}),
                    now,
                    now,
                ),
            )
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        return self._project_from_row(row)

    def list_projects(
        self,
        status: str | None = None,
        owner_id: str | None = None,
    ) -> list[dict]:
        query = "SELECT * FROM projects WHERE 1=1"
        params: list[Any] = []
        if owner_id is not None:
            query += " AND owner_id=?"
            params.append(owner_id)
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._project_from_row(row) for row in rows]

    def get_project(
        self,
        project_id: str,
        owner_id: str | None = None,
    ) -> dict | None:
        with self._connect() as conn:
            if owner_id is None:
                row = conn.execute(
                    "SELECT * FROM projects WHERE id = ?",
                    (project_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM projects WHERE id = ? AND owner_id = ?",
                    (project_id, owner_id),
                ).fetchone()
        return self._project_from_row(row) if row else None

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
            "metadata": metadata if metadata is not None else current["metadata"],
            "updated_at": _utc_now(),
        }

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE projects
                SET name=?, location=?, client=?, opportunity_number=?,
                    phase=?, status=?, metadata_json=?, updated_at=?
                WHERE id=?
                """,
                (
                    values["name"],
                    values["location"],
                    values["client"],
                    values["opportunity_number"],
                    values["phase"],
                    values["status"],
                    _json_dumps(values["metadata"]),
                    values["updated_at"],
                    project_id,
                ),
            )
            row = conn.execute(
                "SELECT * FROM projects WHERE id=?", (project_id,)
            ).fetchone()
        return self._project_from_row(row)

    def delete_project(self, project_id: str, owner_id: str | None = None) -> bool:
        with self._connect() as conn:
            if owner_id is None:
                cur = conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
            else:
                cur = conn.execute(
                    "DELETE FROM projects WHERE id=? AND owner_id=?",
                    (project_id, owner_id),
                )
        return cur.rowcount > 0

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
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO progress_entries(
                    id, project_id, entry_date, phase, rooms_json,
                    completed_json, in_progress_json, issues_json, blockers_json,
                    next_actions_json, responsible_parties_json, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    project_id,
                    entry_date,
                    phase,
                    _json_dumps(rooms or []),
                    _json_dumps(completed or []),
                    _json_dumps(in_progress or []),
                    _json_dumps(issues or []),
                    _json_dumps(blockers or []),
                    _json_dumps(next_actions or []),
                    _json_dumps(responsible_parties or []),
                    notes,
                    now,
                    now,
                ),
            )
            conn.execute(
                "UPDATE projects SET updated_at=? WHERE id=?",
                (now, project_id),
            )
            row = conn.execute(
                "SELECT * FROM progress_entries WHERE id=?", (entry_id,)
            ).fetchone()
        return self._progress_from_row(row)

    def list_progress_entries(
        self,
        project_id: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        query = "SELECT * FROM progress_entries WHERE project_id=?"
        params: list[Any] = [project_id]
        if start_date:
            query += " AND entry_date>=?"
            params.append(start_date)
        if end_date:
            query += " AND entry_date<=?"
            params.append(end_date)
        query += " ORDER BY entry_date ASC, created_at ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._progress_from_row(row) for row in rows]

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
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO drawing_analyses(
                    id, project_id, file_name, file_hash, page_count,
                    register_json, qa_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    project_id,
                    file_name,
                    file_hash,
                    int(page_count),
                    _json_dumps(register),
                    _json_dumps(qa),
                    now,
                ),
            )
            conn.execute(
                "UPDATE projects SET updated_at=? WHERE id=?",
                (now, project_id),
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
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM drawing_analyses
                WHERE project_id=?
                ORDER BY created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "file_name": row["file_name"],
                "file_hash": row["file_hash"],
                "page_count": row["page_count"],
                "register": _json_loads(row["register_json"], {}),
                "qa": _json_loads(row["qa_json"], {}),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

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
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO generated_reports(
                    id, project_id, period, anchor_date, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    project_id,
                    period,
                    anchor_date,
                    _json_dumps(payload),
                    now,
                ),
            )
        return {
            "id": report_id,
            "project_id": project_id,
            "period": period,
            "anchor_date": anchor_date,
            "payload": payload,
            "created_at": now,
        }

    def get_report(self, project_id: str, report_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM generated_reports
                WHERE project_id=? AND id=?
                """,
                (project_id, report_id),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "period": row["period"],
            "anchor_date": row["anchor_date"],
            "payload": _json_loads(row["payload_json"], {}),
            "created_at": row["created_at"],
        }

    def list_reports(self, project_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM generated_reports
                WHERE project_id=?
                ORDER BY created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "period": row["period"],
                "anchor_date": row["anchor_date"],
                "payload": _json_loads(row["payload_json"], {}),
                "created_at": row["created_at"],
            }
            for row in rows
        ]


    def delete_projects_for_owner(self, owner_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM projects WHERE owner_id=?",
                (owner_id,),
            ).fetchone()
            count = int(row["count"] if row else 0)
            conn.execute(
                "DELETE FROM projects WHERE owner_id=?",
                (owner_id,),
            )
        return count

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
