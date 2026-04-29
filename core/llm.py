"""LLM wrapper with backend dispatch (g4f / OpenAI / Anthropic).

Backend chosen by `PSYCHOSIS_BACKEND` env: `g4f` (default, free), `openai`,
`anthropic`. Each backend has its own model + auth env vars. Falls back to
offline canned reply if backend unavailable.
"""
from __future__ import annotations

import logging
import os
from typing import Iterable

from .llm_official import call_anthropic, call_openai

logger = logging.getLogger(__name__)

BACKEND = os.environ.get("PSYCHOSIS_BACKEND", "g4f").lower()
DEFAULT_MODEL = os.environ.get("PSYCHOSIS_MODEL", "gpt-4o-mini")
PROVIDER_CHAIN_NAMES = os.environ.get(
    "PSYCHOSIS_PROVIDERS", "Copilot,DDG,Blackbox,DarkAI,Liaobots"
).split(",")

DEFAULT_MODEL_BY_BACKEND = {
    "g4f": "gpt-4o-mini",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-6",
}


def _load_g4f():
    try:
        from g4f.client import Client
        import g4f.Provider as P
        return Client, P
    except Exception as e:  # pragma: no cover
        logger.warning("g4f unavailable: %s", e)
        return None, None


def build_messages(
    system_prompt: str,
    history: Iterable[dict],
    extra_user_directive: str | None = None,
) -> list[dict]:
    """Compose chat-completions messages array.

    `history` items: {"role": "user"|"assistant", "content": str}.
    """
    msgs: list[dict] = [{"role": "system", "content": system_prompt}]
    for h in history:
        role = h["role"] if h["role"] in ("user", "assistant", "system") else "user"
        msgs.append({"role": role, "content": h["content"]})
    if extra_user_directive:
        msgs.append({"role": "user", "content": extra_user_directive})
    return msgs


def generate_reply(
    system_prompt: str,
    history: Iterable[dict],
    *,
    extra_user_directive: str | None = None,
    model: str | None = None,
    max_tokens: int = 600,
    temperature: float = 0.8,
    backend: str | None = None,
) -> str:
    """Dispatch to backend (g4f / openai / anthropic). Returns stripped reply."""
    msgs = build_messages(system_prompt, history, extra_user_directive)
    chosen = (backend or BACKEND).lower()
    chosen_model = model or os.environ.get("PSYCHOSIS_MODEL") or DEFAULT_MODEL_BY_BACKEND.get(chosen, DEFAULT_MODEL)

    try:
        if chosen == "openai":
            return call_openai(msgs, model=chosen_model, max_tokens=max_tokens, temperature=temperature)
        if chosen == "anthropic":
            return call_anthropic(msgs, model=chosen_model, max_tokens=max_tokens, temperature=temperature)
    except Exception as e:
        logger.error("%s backend failed: %s — falling back to g4f", chosen, e)

    return _generate_g4f(msgs, chosen_model, max_tokens, temperature, history)


def _generate_g4f(
    msgs: list[dict],
    model: str,
    max_tokens: int,
    temperature: float,
    history: Iterable[dict],
) -> str:
    Client, Providers = _load_g4f()
    if Client is None:
        return _offline_fallback(history)
    last_err: Exception | None = None
    for prov_name in PROVIDER_CHAIN_NAMES:
        prov_name = prov_name.strip()
        provider = getattr(Providers, prov_name, None) if prov_name else None
        try:
            client = Client()
            kwargs = dict(
                model=model,
                messages=msgs,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if provider is not None:
                kwargs["provider"] = provider
            response = client.chat.completions.create(**kwargs)
            content = (response.choices[0].message.content or "").strip()
            if content:
                return content
            last_err = RuntimeError("empty content")
        except Exception as e:
            logger.warning("provider %s failed: %s", prov_name, e)
            last_err = e
            continue
    logger.error("all g4f providers failed: %s", last_err)
    return _offline_fallback(history)


def _offline_fallback(history: Iterable[dict]) -> str:
    last_user = ""
    for h in history:
        if h.get("role") == "user":
            last_user = h.get("content", "")
    if not last_user:
        return "я тут. что у тебя?"
    return (
        "слышу тебя\n"
        '<newmessage time="2"></newmessage>\n'
        "сложно сейчас?"
    )
