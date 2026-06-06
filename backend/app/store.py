"""Structured local persistence (SQLite): projects, conversations, messages, and a
per-project source library that accumulates DOI-verified sources across conversations.

A connection is opened per call (simplest correct approach under uvicorn's async +
worker threads). The method surface is intentionally storage-agnostic so it can be
swapped for DynamoDB at deploy time without touching callers.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

from .config import get_settings

_DEFAULT_SOURCES = ["openalex", "scopus", "arxiv"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, brief TEXT DEFAULT '',
  sources TEXT DEFAULT '["openalex","scopus","arxiv"]',
  created_at REAL, updated_at REAL
);
CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
  role TEXT, content TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS library (
  project_id TEXT NOT NULL, dedup_key TEXT NOT NULL,
  doi TEXT, title TEXT, authors TEXT, year TEXT, venue TEXT,
  verified INTEGER, created_at REAL,
  PRIMARY KEY (project_id, dedup_key)
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY, username TEXT, created_at REAL, expires_at REAL
);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conv_proj ON conversations(project_id);
"""


class Store:
    def __init__(self, path: str):
        self._path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)
            # migrate older DBs that predate the sources column
            try:
                c.execute(
                    "ALTER TABLE projects ADD COLUMN sources TEXT "
                    "DEFAULT '[\"openalex\",\"scopus\",\"arxiv\"]'"
                )
            except sqlite3.OperationalError:
                pass

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self._path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    @staticmethod
    def _proj(row: sqlite3.Row) -> dict:
        d = dict(row)
        try:
            d["sources"] = json.loads(d.get("sources") or "") or list(_DEFAULT_SOURCES)
        except Exception:  # noqa: BLE001
            d["sources"] = list(_DEFAULT_SOURCES)
        return d

    # --- projects ---
    def create_project(self, name: str) -> dict:
        pid, now = uuid.uuid4().hex, time.time()
        with self._conn() as c:
            c.execute(
                "INSERT INTO projects(id,name,brief,created_at,updated_at) VALUES(?,?,?,?,?)",
                (pid, name, "", now, now),
            )
        return {
            "id": pid, "name": name, "brief": "", "sources": list(_DEFAULT_SOURCES),
            "created_at": now, "updated_at": now,
        }

    def list_projects(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        return [self._proj(r) for r in rows]

    def get_project(self, pid: str) -> dict | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        return self._proj(r) if r else None

    def update_sources(self, pid: str, sources: list[str]) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE projects SET sources=?, updated_at=? WHERE id=?",
                (json.dumps(list(sources)), time.time(), pid),
            )

    def update_brief(self, pid: str, brief: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE projects SET brief=?, updated_at=? WHERE id=?", (brief, time.time(), pid)
            )

    def rename_project(self, pid: str, name: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE projects SET name=?, updated_at=? WHERE id=?", (name, time.time(), pid)
            )

    def delete_project(self, pid: str) -> None:
        with self._conn() as c:
            convs = [
                r["id"]
                for r in c.execute(
                    "SELECT id FROM conversations WHERE project_id=?", (pid,)
                ).fetchall()
            ]
            for cid in convs:
                c.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
            c.execute("DELETE FROM conversations WHERE project_id=?", (pid,))
            c.execute("DELETE FROM library WHERE project_id=?", (pid,))
            c.execute("DELETE FROM projects WHERE id=?", (pid,))

    def touch_project(self, pid: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE projects SET updated_at=? WHERE id=?", (time.time(), pid))

    # --- conversations ---
    def create_conversation(self, project_id: str, title: str = "New conversation") -> dict:
        cid, now = uuid.uuid4().hex, time.time()
        with self._conn() as c:
            c.execute(
                "INSERT INTO conversations(id,project_id,title,created_at) VALUES(?,?,?,?)",
                (cid, project_id, title, now),
            )
        return {"id": cid, "project_id": project_id, "title": title, "created_at": now}

    def list_conversations(self, project_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM conversations WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_conversation(self, cid: str) -> dict | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
        return dict(r) if r else None

    def rename_conversation(self, cid: str, title: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE conversations SET title=? WHERE id=?", (title, cid))

    def delete_conversation(self, cid: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
            c.execute("DELETE FROM conversations WHERE id=?", (cid,))

    # --- messages ---
    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",
                (conversation_id, role, content, time.time()),
            )

    def get_messages(self, conversation_id: str, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT role,content,created_at FROM messages WHERE conversation_id=? "
                "ORDER BY id ASC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_project_drafts(self, pid: str, max_chars: int = 20000) -> str:
        """Concatenate the assistant-written material across all of a project's
        conversations (the drafted content the Editor assembles into the paper)."""
        parts: list[str] = []
        for conv in self.list_conversations(pid):
            for m in self.get_messages(conv["id"], limit=100):
                if m["role"] == "assistant" and m["content"].strip():
                    parts.append(f"## from conversation: {conv['title']}\n{m['content']}")
        return "\n\n".join(parts)[:max_chars]

    # --- per-project source library ---
    def add_library(self, project_id: str, sources: list[dict]) -> None:
        now = time.time()
        with self._conn() as c:
            for s in sources:
                key = (s.get("doi") or s.get("title") or "").lower().strip()
                if not key:
                    continue
                c.execute(
                    "INSERT OR IGNORE INTO library"
                    "(project_id,dedup_key,doi,title,authors,year,venue,verified,created_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        project_id, key, s.get("doi", ""), s.get("title", ""),
                        s.get("authors", ""), str(s.get("year", "")), s.get("venue", ""),
                        1 if s.get("verified") else 0, now,
                    ),
                )

    def get_library(self, project_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT doi,title,authors,year,venue,verified FROM library "
                "WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        return [dict(r) for r in rows]


    # --- auth sessions (server-side, so logout truly revokes) ---
    def create_session(self, token: str, username: str, expires_at: float) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO sessions(token,username,created_at,expires_at) VALUES(?,?,?,?)",
                (token, username, time.time(), expires_at),
            )

    def get_session(self, token: str) -> dict | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM sessions WHERE token=?", (token,)).fetchone()
        if not r:
            return None
        if r["expires_at"] < time.time():
            self.delete_session(token)
            return None
        return dict(r)

    def delete_session(self, token: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM sessions WHERE token=?", (token,))

    def purge_expired_sessions(self) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store(get_settings().store_path)
    return _store
