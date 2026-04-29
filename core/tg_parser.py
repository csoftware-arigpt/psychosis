"""Telegram export (result.json) parser + style profile extractor.

Telegram desktop export schema (relevant fields only):
{
  "name": "<chat title>",
  "type": "personal_chat" | "private_group" | "private_supergroup",
  "id": <int>,
  "messages": [
    {
      "id": <int>,
      "type": "message" | "service",
      "date": "YYYY-MM-DDTHH:MM:SS",
      "from": "<display name>",
      "from_id": "user<numeric>" | "channel<numeric>",
      "text": "<plain str>" OR [<plain str> | {"type": "<entity>", "text": "..."}]
    }
  ]
}
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any


_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF"
    "\u2600-\u27BF]"
)
_WORD_RE = re.compile(r"\b[\w']+\b", re.UNICODE)
_SLANG_HINTS = {
    "щас", "чё", "че", "норм", "ок", "оке", "спс", "нзч", "кек", "лол",
    "мб", "кмк", "имхо", "типа", "капец", "пздц", "сорян", "ору", "база",
    "бро", "сис", "гг", "хз", "фиг", "ыыы", "ахаха", "лан",
}


def _flatten_text(text_field: Any) -> str:
    """TG `text` may be plain str or list of str/dicts. Flatten to single str."""
    if isinstance(text_field, str):
        return text_field
    if isinstance(text_field, list):
        out: list[str] = []
        for part in text_field:
            if isinstance(part, str):
                out.append(part)
            elif isinstance(part, dict):
                out.append(part.get("text", ""))
        return "".join(out)
    return ""


def parse_telegram_export(data: dict, target_from: str | None = None) -> list[str]:
    """Extract plain-text messages, optionally filtered by sender display name."""
    msgs = data.get("messages") or []
    out: list[str] = []
    for m in msgs:
        if m.get("type") != "message":
            continue
        if target_from and m.get("from") != target_from:
            continue
        text = _flatten_text(m.get("text")).strip()
        if text:
            out.append(text)
    return out


def list_senders(data: dict) -> list[str]:
    """Unique sender display names with non-empty messages, frequency-sorted."""
    counts: Counter[str] = Counter()
    for m in data.get("messages") or []:
        if m.get("type") != "message":
            continue
        text = _flatten_text(m.get("text")).strip()
        if not text:
            continue
        name = m.get("from")
        if name:
            counts[name] += 1
    return [n for n, _ in counts.most_common()]


def build_style_profile(messages: list[str]) -> dict:
    """Compute aggregate stylometric features over a corpus of one user."""
    if not messages:
        return {
            "count": 0,
            "avg_len": 0.0,
            "lower_ratio": 0.0,
            "emoji_per_msg": 0.0,
            "no_punct_ratio": 0.0,
            "top_tokens": [],
            "slang": [],
        }

    lengths = [len(_WORD_RE.findall(m)) for m in messages]
    lowers = [m for m in messages if m and m[0].islower()]
    emojis_total = sum(len(_EMOJI_RE.findall(m)) for m in messages)
    no_punct = [m for m in messages if m and m[-1] not in ".!?…"]
    tokens: list[str] = []
    for m in messages:
        tokens.extend(t.lower() for t in _WORD_RE.findall(m))
    token_counts = Counter(tokens)
    top_tokens = [t for t, _ in token_counts.most_common(20) if len(t) > 2]
    slang_used = [t for t in token_counts if t in _SLANG_HINTS]

    return {
        "count": len(messages),
        "avg_len": sum(lengths) / max(1, len(messages)),
        "lower_ratio": len(lowers) / max(1, len(messages)),
        "emoji_per_msg": emojis_total / max(1, len(messages)),
        "no_punct_ratio": len(no_punct) / max(1, len(messages)),
        "top_tokens": top_tokens,
        "slang": slang_used,
    }
