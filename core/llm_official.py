"""Official API wrappers: OpenAI + Anthropic.

Reads keys from env: OPENAI_API_KEY, ANTHROPIC_API_KEY.
Optional: OPENAI_BASE_URL (proxy/Azure/Together/OpenRouter compatible).
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def call_openai(
    messages: list[dict],
    *,
    model: str,
    max_tokens: int = 600,
    temperature: float = 0.8,
) -> str:
    """OpenAI chat completion. Compatible w/ any OpenAI-spec endpoint."""
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("openai package not installed") from e

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    base_url = os.environ.get("OPENAI_BASE_URL") or None
    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()


def call_anthropic(
    messages: list[dict],
    *,
    model: str,
    max_tokens: int = 600,
    temperature: float = 0.8,
) -> str:
    """Anthropic Messages API. System prompt extracted from first system msg."""
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError("anthropic package not installed") from e

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    system_prompt = ""
    user_assistant: list[dict] = []
    for m in messages:
        if m["role"] == "system":
            system_prompt = (system_prompt + "\n\n" + m["content"]).strip()
        else:
            user_assistant.append({"role": m["role"], "content": m["content"]})

    if user_assistant and user_assistant[0]["role"] == "assistant":
        user_assistant.insert(0, {"role": "user", "content": "(start)"})

    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        system=system_prompt or "You are a helpful assistant.",
        messages=user_assistant,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()
