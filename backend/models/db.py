"""SQLite 数据层（标准库 sqlite3，无 ORM 依赖）。

每次操作使用独立连接（本地文件库开销极低），规避线程问题。
"""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from config import settings

_local = threading.local()
_write_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    path        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    goal        TEXT,
    created_at  TEXT NOT NULL,
    last_analyzed_at TEXT
);

CREATE TABLE IF NOT EXISTS reports (
    id            TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL REFERENCES projects(id),
    status        TEXT NOT NULL DEFAULT 'running',   -- running | completed | failed
    goal          TEXT,
    summary       TEXT,
    project_map_json  TEXT,
    findings_json     TEXT,
    suggestions_json  TEXT,
    tool_trace_json   TEXT,
    error         TEXT,
    started_at    TEXT NOT NULL,
    finished_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_reports_project ON reports(project_id, started_at DESC);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_conn():
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with _write_lock, get_conn() as conn:
        conn.executescript(_SCHEMA)
        # 轻量迁移：早期版本无 goal_source 列
        cols = {r[1] for r in conn.execute("PRAGMA table_info(reports)")}
        if "goal_source" not in cols:
            conn.execute("ALTER TABLE reports ADD COLUMN goal_source TEXT")
        conn.commit()


# ---------------------------------------------------------------- projects

def upsert_project(path: str, name: str, goal: str | None = None) -> dict:
    with _write_lock, get_conn() as conn:
        conn.execute(
            """INSERT INTO projects (id, path, name, goal, created_at) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(path) DO UPDATE SET
                   name = excluded.name,
                   goal = COALESCE(excluded.goal, projects.goal)""",
            (_new_id(), path, name, goal, utc_now()),
        )
        row = conn.execute("SELECT * FROM projects WHERE path = ?", (path,)).fetchone()
        conn.commit()
        return dict(row)


def get_project(project_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None


def get_project_by_path(path: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM projects WHERE path = ?", (path,)).fetchone()
        return dict(row) if row else None


def set_project_goal(project_id: str, goal: str) -> None:
    with _write_lock, get_conn() as conn:
        conn.execute("UPDATE projects SET goal = ? WHERE id = ?", (goal, project_id))
        conn.commit()


def touch_project_analyzed(project_id: str) -> None:
    with _write_lock, get_conn() as conn:
        conn.execute("UPDATE projects SET last_analyzed_at = ? WHERE id = ?", (utc_now(), project_id))
        conn.commit()


def list_projects(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT p.*, r.id AS last_report_id, r.status AS last_report_status,
                      r.finished_at AS last_report_finished_at
               FROM projects p
               LEFT JOIN reports r ON r.project_id = p.id
                 AND r.started_at = (SELECT MAX(r2.started_at) FROM reports r2 WHERE r2.project_id = p.id)
               ORDER BY COALESCE(p.last_analyzed_at, p.created_at) DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------- reports

def set_report_goal_and_status(report_id: str, goal: str | None, status: str) -> None:
    with _write_lock, get_conn() as conn:
        conn.execute(
            "UPDATE reports SET goal = COALESCE(?, goal), status = ? WHERE id = ?",
            (goal, status, report_id),
        )
        # 同步项目目标（README 提取出的 goal 固化到项目）
        if goal:
            conn.execute(
                """UPDATE projects SET goal = ? WHERE id =
                   (SELECT project_id FROM reports WHERE id = ?)""",
                (goal, report_id),
            )
        conn.commit()


def create_report(project_id: str, goal: str | None) -> dict:
    report_id = _new_id()
    with _write_lock, get_conn() as conn:
        conn.execute(
            """INSERT INTO reports (id, project_id, status, goal, started_at)
               VALUES (?, ?, 'running', ?, ?)""",
            (report_id, project_id, goal, utc_now()),
        )
        conn.commit()
        return {"id": report_id, "project_id": project_id, "status": "running"}


def get_report(report_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ("project_map", "findings", "suggestions", "tool_trace"):
            raw = d.pop(f"{key}_json", None)
            d[key] = json.loads(raw) if raw else None
        return d


def list_reports(project_id: str, limit: int = 10) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, status, goal, summary, started_at, finished_at FROM reports "
            "WHERE project_id = ? ORDER BY started_at DESC LIMIT ?",
            (project_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def fail_report(report_id: str, error: str) -> None:
    with _write_lock, get_conn() as conn:
        conn.execute(
            "UPDATE reports SET status = 'failed', error = ?, finished_at = ? WHERE id = ?",
            (error[:2000], utc_now(), report_id),
        )
        conn.commit()


def complete_report(
    report_id: str,
    summary: str,
    project_map: dict | None,
    findings: list,
    suggestions: list,
    tool_trace: list,
    goal_source: str | None = None,
) -> None:
    with _write_lock, get_conn() as conn:
        conn.execute(
            """UPDATE reports SET status = 'completed', summary = ?,
                   project_map_json = ?, findings_json = ?, suggestions_json = ?,
                   tool_trace_json = ?, goal_source = ?, finished_at = ? WHERE id = ?""",
            (
                summary,
                json.dumps(project_map, ensure_ascii=False),
                json.dumps(findings, ensure_ascii=False),
                json.dumps(suggestions, ensure_ascii=False),
                json.dumps(tool_trace, ensure_ascii=False),
                goal_source,
                utc_now(),
                report_id,
            ),
        )
        conn.commit()


def update_report_goal(report_id: str, goal: str) -> bool:
    """用户事后补充/修正项目目标（goal_source=user）。"""
    with _write_lock, get_conn() as conn:
        cur = conn.execute(
            "UPDATE reports SET goal = ?, goal_source = 'user' WHERE id = ?",
            (goal, report_id),
        )
        conn.execute(
            """UPDATE projects SET goal = ? WHERE id =
               (SELECT project_id FROM reports WHERE id = ?)""",
            (goal, report_id),
        )
        conn.commit()
        return cur.rowcount > 0


def _new_id() -> str:
    import uuid
    return uuid.uuid4().hex[:12]
