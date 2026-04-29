"""Pydantic models mirroring SQLite tables."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class User(BaseModel):
    id: int | None = None
    username: str
    created_at: datetime


class Session(BaseModel):
    id: int | None = None
    user_id: int
    started_at: datetime
    ended_at: datetime | None = None
    persona: str = "warm_friend"
    module: str | None = None


class Message(BaseModel):
    id: int | None = None
    session_id: int
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    ai_generated: bool = False
    created_at: datetime


class ScreeningResult(BaseModel):
    id: int | None = None
    user_id: int
    instrument_code: str
    total_score: int
    severity: str
    answers_json: str
    created_at: datetime


class Diagnosis(BaseModel):
    id: int | None = None
    user_id: int
    content_md: str
    created_at: datetime


class MoodEntry(BaseModel):
    id: int | None = None
    user_id: int
    score: int  # 0–10
    note: str = ""
    created_at: datetime


class StyleProfile(BaseModel):
    id: int | None = None
    user_id: int
    target_name: str
    profile_json: str
    examples_json: str
    created_at: datetime
