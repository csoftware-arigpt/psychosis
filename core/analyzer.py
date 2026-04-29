"""Scoring, severity mapping, crisis detection, diagnostic synthesis."""
from __future__ import annotations

import json
import re
from typing import Iterable

from prompts.diagnostic import DIAGNOSTIC_SYNTHESIS_PROMPT
from prompts.screening import SCREENING_INSTRUMENTS, Instrument
from .llm import generate_reply


CRISIS_PATTERNS = [
    r"\b(не\s*хочу\s*жить|покончить|суицид|повесит|вскры|покончу)\b",
    r"\b(kill\s*myself|end\s*it|suicid|hang\s*myself)\b",
    r"\b(нет\s*смысла|пропади\s*оно|устал\s*жить)\b",
    r"\b(передоз|таблеток\s*наглота)\b",
    r"\b(self[-\s]?harm|cut\s*myself|порежу|режу\s*себя)\b",
]


def detect_crisis_signals(text: str) -> list[str]:
    """Return matched crisis pattern names. Empty list = no signals."""
    if not text:
        return []
    found: list[str] = []
    low = text.lower()
    for pat in CRISIS_PATTERNS:
        if re.search(pat, low):
            found.append(pat)
    return found


def score_screening(instrument: Instrument, answers: list[int]) -> int:
    if len(answers) != len(instrument["items"]):
        raise ValueError(
            f"{instrument['code']} expects {len(instrument['items'])} answers, got {len(answers)}"
        )
    return sum(int(a) for a in answers)


def severity_for(instrument: Instrument, total_score: int) -> str:
    label = instrument["cutoffs"][0][1]
    for threshold, name in instrument["cutoffs"]:
        if total_score >= threshold:
            label = name
    return label


_RESULT_RE = re.compile(
    r"<SCREENING_RESULT>\s*(\{.*?\})\s*</SCREENING_RESULT>", re.DOTALL
)


def extract_screening_result(text: str) -> dict | None:
    if not text:
        return None
    m = _RESULT_RE.search(text)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
        if "code" in data and "answers" in data and isinstance(data["answers"], list):
            return data
    except json.JSONDecodeError:
        return None
    return None


def synthesize_diagnosis(
    screenings: Iterable[dict],
    transcript_excerpts: Iterable[str],
    history_excerpts: Iterable[str],
) -> str:
    screening_block = "\n".join(
        f"- {s['instrument_code']}: {s['total_score']} ({s['severity']})"
        for s in screenings
    ) or "(нет данных скрининга)"

    transcript_block = "\n".join(f"- {t}" for t in transcript_excerpts) or "(нет данных)"
    history_block = "\n".join(f"- {h}" for h in history_excerpts) or "(нет данных)"

    prompt = DIAGNOSTIC_SYNTHESIS_PROMPT.format(
        screening_block=screening_block,
        transcript_block=transcript_block,
        history_block=history_block,
    )
    return generate_reply(
        system_prompt="Ты — диагностический ассистент. Не клинический диагноз.",
        history=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.4,
    )
