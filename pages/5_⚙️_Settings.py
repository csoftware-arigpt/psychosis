"""Settings: persona/model defaults + Telegram export style upload."""
from __future__ import annotations

import json

import streamlit as st

from core import build_style_profile, parse_telegram_export
from core.tg_parser import list_senders
from data import save_style_profile, get_style_profile
from prompts import PERSONAS


st.set_page_config(page_title="Настройки | Psychosis NXT", page_icon="⚙️", layout="wide")

if "user_id" not in st.session_state:
    st.warning("Сначала войди на главной странице.")
    st.stop()

USER_ID = st.session_state.user_id

st.title("⚙️ Настройки")

st.markdown("### Персона по умолчанию")
for code, p in PERSONAS.items():
    with st.expander(f"{p['name']} ({code})"):
        st.caption(p["description"])
        st.code(p["voice"], language=None)

st.divider()

st.markdown("### Копирование стиля из Telegram-экспорта")
st.markdown(
    "1. В Telegram Desktop: **Настройки → Продвинутые → Экспорт данных → Личные чаты, формат JSON**.\n"
    "2. Загрузи `result.json` ниже.\n"
    "3. Выбери, чей стиль копировать.\n"
    "4. AI будет писать в этом стиле в терапии."
)

current = get_style_profile(USER_ID)
if current:
    profile = json.loads(current.profile_json)
    st.success(
        f"Активный профиль: **{current.target_name}** "
        f"({profile.get('count', 0)} сообщений, "
        f"avg_len={profile.get('avg_len', 0):.1f}, "
        f"emoji/msg={profile.get('emoji_per_msg', 0):.2f})"
    )

uploaded = st.file_uploader("result.json (Telegram export)", type=["json"])
if uploaded:
    try:
        data = json.load(uploaded)
    except json.JSONDecodeError as e:
        st.error(f"Не получилось распарсить JSON: {e}")
        st.stop()

    senders = list_senders(data)
    if not senders:
        st.warning("В экспорте нет сообщений с отправителями.")
        st.stop()

    target = st.selectbox("Чей стиль копировать?", options=senders)
    if st.button("Извлечь стиль", type="primary"):
        messages = parse_telegram_export(data, target_from=target)
        profile = build_style_profile(messages)
        examples = messages[-50:]
        save_style_profile(USER_ID, target, profile, examples)
        st.success(
            f"Сохранил профиль для **{target}**: {profile['count']} сообщений, "
            f"средняя длина {profile['avg_len']:.1f} слов."
        )
        with st.expander("Профиль"):
            st.json(profile)
        with st.expander(f"Примеры (последние {min(20, len(examples))})"):
            for ex in examples[-20:]:
                st.code(ex, language=None)

st.divider()

# ---------- LLM backend ----------
st.markdown("### LLM backend")
st.caption(
    "Выбери источник модели. **g4f** — бесплатные провайдеры (нестабильно). "
    "**openai** / **anthropic** — официальные API (нужен ключ)."
)

import os as _os
current_backend = st.session_state.get("llm_backend", _os.environ.get("PSYCHOSIS_BACKEND", "g4f"))
backend = st.radio(
    "Backend",
    ["g4f", "openai", "anthropic"],
    index=["g4f", "openai", "anthropic"].index(current_backend) if current_backend in ("g4f", "openai", "anthropic") else 0,
    horizontal=True,
)

default_models = {
    "g4f": "gpt-4o-mini",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-6",
}
model = st.text_input(
    "Модель",
    value=st.session_state.get("llm_model") or _os.environ.get("PSYCHOSIS_MODEL") or default_models[backend],
)

if backend == "openai":
    api_key = st.text_input(
        "OPENAI_API_KEY", type="password", value=_os.environ.get("OPENAI_API_KEY", "")
    )
    base_url = st.text_input(
        "OPENAI_BASE_URL (опционально — Azure/Together/OpenRouter)",
        value=_os.environ.get("OPENAI_BASE_URL", ""),
    )
    if st.button("Применить", type="primary"):
        _os.environ["PSYCHOSIS_BACKEND"] = "openai"
        _os.environ["PSYCHOSIS_MODEL"] = model
        if api_key:
            _os.environ["OPENAI_API_KEY"] = api_key
        if base_url:
            _os.environ["OPENAI_BASE_URL"] = base_url
        st.session_state.llm_backend = "openai"
        st.session_state.llm_model = model
        st.success("OpenAI backend активен в этой сессии.")
elif backend == "anthropic":
    api_key = st.text_input(
        "ANTHROPIC_API_KEY", type="password", value=_os.environ.get("ANTHROPIC_API_KEY", "")
    )
    if st.button("Применить", type="primary"):
        _os.environ["PSYCHOSIS_BACKEND"] = "anthropic"
        _os.environ["PSYCHOSIS_MODEL"] = model
        if api_key:
            _os.environ["ANTHROPIC_API_KEY"] = api_key
        st.session_state.llm_backend = "anthropic"
        st.session_state.llm_model = model
        st.success("Anthropic backend активен в этой сессии.")
else:
    providers = st.text_input(
        "Цепочка g4f провайдеров",
        value=_os.environ.get("PSYCHOSIS_PROVIDERS", "Copilot,DDG,Blackbox,DarkAI,Liaobots"),
    )
    if st.button("Применить", type="primary"):
        _os.environ["PSYCHOSIS_BACKEND"] = "g4f"
        _os.environ["PSYCHOSIS_MODEL"] = model
        _os.environ["PSYCHOSIS_PROVIDERS"] = providers
        st.session_state.llm_backend = "g4f"
        st.session_state.llm_model = model
        st.success("g4f backend активен в этой сессии.")

# reload module so dispatch picks up new env
if st.session_state.get("llm_backend"):
    import importlib
    from core import llm as _llm_mod
    importlib.reload(_llm_mod)

st.divider()

st.markdown("### Параметры окружения (статика)")
st.code(
    "PSYCHOSIS_DB=psychosis.db                  # путь к SQLite\n"
    "PSYCHOSIS_BACKEND=g4f|openai|anthropic     # активный backend\n"
    "PSYCHOSIS_MODEL=gpt-4o-mini                # модель\n"
    "PSYCHOSIS_PROVIDERS=Copilot,DDG,Blackbox   # цепочка g4f\n"
    "OPENAI_API_KEY=...                         # для openai\n"
    "OPENAI_BASE_URL=...                        # опционально (proxy/Azure)\n"
    "ANTHROPIC_API_KEY=...                      # для anthropic",
    language="bash",
)
st.caption("Можно задать переменные окружения перед `streamlit run app.py` или менять выше runtime.")
