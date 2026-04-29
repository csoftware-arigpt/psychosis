"""SQLite persistence layer for users / sessions / messages / scores."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .models import (
    Diagnosis,
    Message,
    MoodEntry,
    ScreeningResult,
    Session,
    StyleProfile,
    User,
)


DB_PATH = Path(os.environ.get("PSYCHOSIS_DB", "psychosis.db"))


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    persona TEXT NOT NULL DEFAULT 'warm_friend',
    module TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    ai_generated INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS screening_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    instrument_code TEXT NOT NULL,
    total_score INTEGER NOT NULL,
    severity TEXT NOT NULL,
    answers_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS diagnoses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    content_md TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mood_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    score INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS style_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    target_name TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    examples_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_screening_user ON screening_results(user_id);
CREATE INDEX IF NOT EXISTS idx_mood_user ON mood_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_session_user ON sessions(user_id);
"""


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with _conn() as c:
        c.executescript(SCHEMA)


def get_or_create_user(username: str) -> User:
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if row:
            return User(**dict(row))
        now = _now()
        cur = c.execute(
            "INSERT INTO users(username, created_at) VALUES (?,?)", (username, now)
        )
        return User(id=cur.lastrowid, username=username, created_at=datetime.fromisoformat(now))


def list_users() -> list[User]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [User(**dict(r)) for r in rows]


def create_session(user_id: int, persona: str = "warm_friend", module: str | None = None) -> Session:
    with _conn() as c:
        now = _now()
        cur = c.execute(
            "INSERT INTO sessions(user_id, started_at, persona, module) VALUES (?,?,?,?)",
            (user_id, now, persona, module),
        )
        return Session(
            id=cur.lastrowid,
            user_id=user_id,
            started_at=datetime.fromisoformat(now),
            persona=persona,
            module=module,
        )


def end_session(session_id: int) -> None:
    with _conn() as c:
        c.execute("UPDATE sessions SET ended_at=? WHERE id=?", (_now(), session_id))


def list_sessions(user_id: int, limit: int = 50) -> list[Session]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM sessions WHERE user_id=? ORDER BY started_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [Session(**dict(r)) for r in rows]


def save_message(session_id: int, role: str, content: str, ai_generated: bool = False) -> Message:
    with _conn() as c:
        now = _now()
        cur = c.execute(
            "INSERT INTO messages(session_id, role, content, ai_generated, created_at) VALUES (?,?,?,?,?)",
            (session_id, role, content, int(ai_generated), now),
        )
        return Message(
            id=cur.lastrowid,
            session_id=session_id,
            role=role,
            content=content,
            ai_generated=ai_generated,
            created_at=datetime.fromisoformat(now),
        )


def list_messages(session_id: int) -> list[Message]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY id ASC", (session_id,)
        ).fetchall()
        return [
            Message(
                id=r["id"],
                session_id=r["session_id"],
                role=r["role"],
                content=r["content"],
                ai_generated=bool(r["ai_generated"]),
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


def save_screening_result(
    user_id: int, instrument_code: str, total_score: int, severity: str, answers: list[int]
) -> ScreeningResult:
    with _conn() as c:
        now = _now()
        aj = json.dumps(answers)
        cur = c.execute(
            """INSERT INTO screening_results(user_id, instrument_code, total_score, severity, answers_json, created_at)
               VALUES (?,?,?,?,?,?)""",
            (user_id, instrument_code, total_score, severity, aj, now),
        )
        return ScreeningResult(
            id=cur.lastrowid,
            user_id=user_id,
            instrument_code=instrument_code,
            total_score=total_score,
            severity=severity,
            answers_json=aj,
            created_at=datetime.fromisoformat(now),
        )


def list_screening_results(user_id: int) -> list[ScreeningResult]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM screening_results WHERE user_id=? ORDER BY created_at ASC", (user_id,)
        ).fetchall()
        return [ScreeningResult(**dict(r)) for r in rows]


def save_diagnosis(user_id: int, content_md: str) -> Diagnosis:
    with _conn() as c:
        now = _now()
        cur = c.execute(
            "INSERT INTO diagnoses(user_id, content_md, created_at) VALUES (?,?,?)",
            (user_id, content_md, now),
        )
        return Diagnosis(
            id=cur.lastrowid,
            user_id=user_id,
            content_md=content_md,
            created_at=datetime.fromisoformat(now),
        )


def list_diagnoses(user_id: int) -> list[Diagnosis]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM diagnoses WHERE user_id=? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
        return [Diagnosis(**dict(r)) for r in rows]


def save_mood(user_id: int, score: int, note: str = "") -> MoodEntry:
    with _conn() as c:
        now = _now()
        cur = c.execute(
            "INSERT INTO mood_entries(user_id, score, note, created_at) VALUES (?,?,?,?)",
            (user_id, score, note, now),
        )
        return MoodEntry(
            id=cur.lastrowid,
            user_id=user_id,
            score=score,
            note=note,
            created_at=datetime.fromisoformat(now),
        )


def list_moods(user_id: int) -> list[MoodEntry]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM mood_entries WHERE user_id=? ORDER BY created_at ASC", (user_id,)
        ).fetchall()
        return [MoodEntry(**dict(r)) for r in rows]


def save_style_profile(
    user_id: int, target_name: str, profile: dict, examples: list[str]
) -> StyleProfile:
    with _conn() as c:
        now = _now()
        pj = json.dumps(profile, ensure_ascii=False)
        ej = json.dumps(examples, ensure_ascii=False)
        c.execute("DELETE FROM style_profiles WHERE user_id=?", (user_id,))
        cur = c.execute(
            """INSERT INTO style_profiles(user_id, target_name, profile_json, examples_json, created_at)
               VALUES (?,?,?,?,?)""",
            (user_id, target_name, pj, ej, now),
        )
        return StyleProfile(
            id=cur.lastrowid,
            user_id=user_id,
            target_name=target_name,
            profile_json=pj,
            examples_json=ej,
            created_at=datetime.fromisoformat(now),
        )


def get_style_profile(user_id: int) -> StyleProfile | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM style_profiles WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return StyleProfile(**dict(row)) if row else None


def user_stats(user_id: int) -> dict:
    with _conn() as c:
        sessions = c.execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (user_id,)).fetchone()[0]
        msgs = c.execute(
            """SELECT COUNT(*) FROM messages m
               JOIN sessions s ON m.session_id=s.id WHERE s.user_id=?""",
            (user_id,),
        ).fetchone()[0]
        ai_msgs = c.execute(
            """SELECT COUNT(*) FROM messages m
               JOIN sessions s ON m.session_id=s.id WHERE s.user_id=? AND m.ai_generated=1""",
            (user_id,),
        ).fetchone()[0]
        screenings = c.execute(
            "SELECT COUNT(*) FROM screening_results WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        moods = c.execute(
            "SELECT COUNT(*), AVG(score) FROM mood_entries WHERE user_id=?", (user_id,)
        ).fetchone()
        last_session = c.execute(
            "SELECT MAX(started_at) FROM sessions WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        return {
            "sessions": sessions,
            "messages": msgs,
            "ai_messages": ai_msgs,
            "screenings": screenings,
            "mood_entries": moods[0] or 0,
            "mood_avg": float(moods[1]) if moods[1] is not None else None,
            "last_session_at": last_session,
        }
