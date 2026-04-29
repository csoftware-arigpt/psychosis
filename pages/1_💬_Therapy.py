"""Therapy chat page — live multi-message dialog with adaptive modules."""
from __future__ import annotations

import json
import time

import streamlit as st

from core import (
    generate_reply,
    parse_chunks,
    detect_crisis_signals,
)
from data import (
    create_session,
    end_session,
    save_message,
    list_messages,
    save_mood,
    get_style_profile,
)
from prompts import (
    LIVE_HUMAN_STYLE,
    THERAPY_MODULES,
    PERSONAS,
    build_persona_prompt,
    build_style_copy_prompt,
)
from prompts.therapy import build_therapy_system_prompt


st.set_page_config(page_title="Терапия | Psychosis NXT", page_icon="💬", layout="wide")

if "user_id" not in st.session_state:
    st.warning("Сначала войди на главной странице.")
    st.stop()

USER_ID = st.session_state.user_id


def _start_new_session(persona: str, module: str | None) -> None:
    s = create_session(USER_ID, persona=persona, module=module)
    st.session_state.current_session_id = s.id
    st.session_state.messages = []


def _build_system_prompt(persona: str, module: str | None) -> str:
    parts = [
        LIVE_HUMAN_STYLE,
        build_persona_prompt(persona),
        build_therapy_system_prompt(module),
    ]
    sp = get_style_profile(USER_ID)
    if sp:
        profile = json.loads(sp.profile_json)
        examples = json.loads(sp.examples_json)
        parts.append(
            build_style_copy_prompt(
                target_name=sp.target_name,
                examples=examples,
                avg_len=profile.get("avg_len", 0),
                lower_ratio=profile.get("lower_ratio", 0),
                emoji_per_msg=profile.get("emoji_per_msg", 0),
                no_punct_ratio=profile.get("no_punct_ratio", 0),
                top_tokens=profile.get("top_tokens", []),
                slang=profile.get("slang", []),
            )
        )
    return "\n\n".join(parts)


with st.sidebar:
    st.markdown("### Сессия")
    persona_code = st.selectbox(
        "Персона",
        options=list(PERSONAS.keys()),
        format_func=lambda c: PERSONAS[c]["name"],
        key="therapy_persona",
    )
    module_code = st.selectbox(
        "Терапевтический модуль",
        options=["auto"] + list(THERAPY_MODULES.keys()),
        format_func=lambda c: "авто (по сигналам)" if c == "auto" else THERAPY_MODULES[c]["name"],
        key="therapy_module",
    )
    module_param = None if module_code == "auto" else module_code

    st.divider()
    if "current_session_id" not in st.session_state:
        if st.button("▶️ Начать сессию", type="primary", use_container_width=True):
            _start_new_session(persona_code, module_param)
            st.rerun()
    else:
        st.success(f"Сессия #{st.session_state.current_session_id}")
        if st.button("⏹ Завершить сессию", use_container_width=True):
            end_session(st.session_state.current_session_id)
            del st.session_state.current_session_id
            st.session_state.messages = []
            st.rerun()

    st.divider()
    st.markdown("### Настроение сейчас (0–10)")
    mood = st.slider("0 — ужасно, 10 — отлично", 0, 10, 5, key="mood_slider")
    note = st.text_input("Короткая заметка", key="mood_note")
    if st.button("Сохранить настроение", use_container_width=True):
        save_mood(USER_ID, mood, note)
        st.toast("Записал")


st.title("💬 Терапия")

if "current_session_id" not in st.session_state:
    st.info("Начни сессию слева. Можно выбрать персону и терапевтический модуль.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": m.role, "content": m.content, "ai": m.ai_generated}
        for m in list_messages(st.session_state.current_session_id)
    ]


def _render_history() -> None:
    for msg in st.session_state.messages:
        avatar = "🤖" if msg.get("ai") else None
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])


_render_history()

if user_text := st.chat_input("Напиши..."):
    save_message(st.session_state.current_session_id, "user", user_text, ai_generated=False)
    st.session_state.messages.append({"role": "user", "content": user_text, "ai": False})

    with st.chat_message("user"):
        st.markdown(user_text)

    crisis = detect_crisis_signals(user_text)
    if crisis:
        with st.chat_message("assistant", avatar="🚨"):
            st.error(
                "Слышу тебя. Если есть мысли о том, чтобы причинить себе вред "
                "или умереть — сейчас важно поговорить с человеком, который "
                "может помочь немедленно.\n\n"
                "**Кризисные линии:**\n"
                "- РФ: 8-800-2000-122 (бесплатно, круглосуточно)\n"
                "- Беларусь: 8-801-100-1611\n"
                "- Украина: 7333\n"
                "- US: 988\n\n"
                "Я остаюсь с тобой. Хочешь рассказать, что происходит?"
            )

    system_prompt = _build_system_prompt(
        st.session_state.therapy_persona,
        None if st.session_state.therapy_module == "auto" else st.session_state.therapy_module,
    )
    history = [
        {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
    ]

    with st.spinner("..."):
        raw = generate_reply(
            system_prompt=system_prompt,
            history=history,
            max_tokens=400,
            temperature=0.85,
        )

    chunks = parse_chunks(raw)
    for ch in chunks:
        if ch.delay > 0:
            time.sleep(min(ch.delay, 4))
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(ch.text)
        save_message(st.session_state.current_session_id, "assistant", ch.text, ai_generated=True)
        st.session_state.messages.append({"role": "assistant", "content": ch.text, "ai": True})
