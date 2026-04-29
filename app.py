"""Psychosis NXT — entry point + login + dashboard."""
from __future__ import annotations

import streamlit as st

from data import init_db, get_or_create_user, list_users, user_stats


st.set_page_config(
    page_title="Psychosis NXT",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def _bootstrap() -> bool:
    init_db()
    return True


_bootstrap()


def _login_block() -> None:
    st.markdown("### Войти")
    existing = list_users()
    options = ["— новый пользователь —"] + [u.username for u in existing]
    pick = st.selectbox("Выбери пользователя", options, key="login_pick")
    if pick == options[0]:
        username = st.text_input("Имя пользователя", placeholder="например, anon42")
        if st.button("Войти / создать", type="primary", disabled=not username.strip()):
            user = get_or_create_user(username.strip())
            st.session_state.user_id = user.id
            st.session_state.username = user.username
            st.rerun()
    else:
        if st.button(f"Войти как {pick}", type="primary"):
            user = get_or_create_user(pick)
            st.session_state.user_id = user.id
            st.session_state.username = user.username
            st.rerun()


def _dashboard(user_id: int, username: str) -> None:
    stats = user_stats(user_id)
    st.markdown(f"### Привет, **{username}**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Сессий", stats["sessions"])
    c2.metric("Сообщений", stats["messages"])
    c3.metric("Скринингов", stats["screenings"])
    c4.metric(
        "Среднее настроение",
        f"{stats['mood_avg']:.1f}" if stats["mood_avg"] is not None else "—",
    )
    st.divider()

    st.markdown(
        "**Что делать дальше**\n\n"
        "- 💬 **Терапия** — поговорить вживую с поддерживающим собеседником\n"
        "- 📋 **Скрининг** — пройти валидированный опрос (PHQ-9 / GAD-7 / PCL-5 / AUDIT / MDQ)\n"
        "- 🧩 **Диагностическая картина** — собрать рабочую гипотезу из всего, что есть\n"
        "- 📈 **Аналитика** — посмотреть динамику настроения и активности\n"
        "- ⚙️ **Настройки** — выбрать персону, загрузить экспорт Telegram для копирования стиля"
    )

    if stats["last_session_at"]:
        st.caption(f"Последняя сессия: {stats['last_session_at']}")


def main() -> None:
    st.title("🧠 Psychosis NXT")
    st.caption(
        "Активная оценка личности и работа с проблемами через диалог. "
        "Скрининг → диагностическая картина → адаптивная терапия в сессии."
    )

    if "user_id" not in st.session_state:
        _login_block()
        with st.expander("⚠️ Дисклеймер"):
            st.markdown(
                "Это **не** замена клинической помощи. "
                "При остром кризисе позвони на горячую линию: "
                "РФ 8-800-2000-122, Беларусь 8-801-100-1611, US 988."
            )
        return

    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.username}**")
        if st.button("Выйти"):
            for k in ("user_id", "username", "current_session_id", "messages"):
                st.session_state.pop(k, None)
            st.rerun()

    _dashboard(st.session_state.user_id, st.session_state.username)


main()
