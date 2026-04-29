"""Multi-message chunker. Parses LLM output containing <newmessage time="N"></newmessage>
markers into a sequence of (text, delay_seconds) pairs.

Ported from legacy `parse_response`, hardened: handles both self-closing and
paired tags, missing time attr, leading/trailing whitespace, empty chunks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


_TAG_RE = re.compile(
    r'<newmessage\s+time\s*=\s*["\']?(\d+)["\']?\s*>\s*</newmessage>'
    r'|<newmessage\s+time\s*=\s*["\']?(\d+)["\']?\s*/?>',
    re.IGNORECASE,
)


@dataclass
class ChunkedMessage:
    text: str
    delay: int


def parse_chunks(response: str) -> list[ChunkedMessage]:
    """Split LLM response into ordered chunks with per-chunk display delays.

    First chunk delay=0. Subsequent chunks inherit the time= attr from preceding
    tag, clamped 0..30s.
    """
    if not response:
        return []
    parts: list[ChunkedMessage] = []
    pos = 0
    pending_delay = 0
    for m in _TAG_RE.finditer(response):
        chunk = response[pos : m.start()].strip()
        if chunk:
            parts.append(ChunkedMessage(text=chunk, delay=pending_delay))
        delay = int(m.group(1) or m.group(2) or 0)
        pending_delay = max(0, min(delay, 30))
        pos = m.end()
    tail = response[pos:].strip()
    if tail:
        parts.append(ChunkedMessage(text=tail, delay=pending_delay))
    if not parts:
        parts.append(ChunkedMessage(text=response.strip(), delay=0))
    return parts
