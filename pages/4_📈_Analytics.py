"""Per-user analytics: mood trend, screening trajectory, activity."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from data import (
    list_moods,
    list_screening_results,
    list_sessions,
    list_messages,
    user_stats,
)


st.set_page_config(page_title="Аналитика | Psychosis NXT", page_icon="📈", layout="wide")

if "user_id" not in st.session_state:
    st.warning("Сначала войди на главной странице.")
    st.stop()

USER_ID = st.session_state.user_id

st.title("📈 Аналитика")

stats = user_stats(USER_ID)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Сессий", stats["sessions"])
c2.metric("Сообщений", stats["messages"])
c3.metric("AI-сообщений", stats["ai_messages"])
c4.metric("Скринингов", stats["screenings"])
c5.metric(
    "Среднее настроение",
    f"{stats['mood_avg']:.1f}" if stats["mood_avg"] is not None else "—",
)

st.divider()

st.markdown("### Динамика настроения")
moods = list_moods(USER_ID)
if not moods:
    st.caption("Пока нет записей. Заходи в Терапию и записывай настроение.")
else:
    df = pd.DataFrame(
        [{"дата": m.created_at, "настроение": m.score, "заметка": m.note} for m in moods]
    )
    fig = px.line(
        df,
        x="дата",
        y="настроение",
        markers=True,
        hover_data=["заметка"],
        range_y=[0, 10],
    )
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### Скрининги во времени")
screenings = list_screening_results(USER_ID)
if not screenings:
    st.caption("Пока нет данных скрининга.")
else:
    sdf = pd.DataFrame(
        [
            {
                "дата": r.created_at,
                "инструмент": r.instrument_code,
                "сумма": r.total_score,
                "степень": r.severity,
            }
            for r in screenings
        ]
    )
    fig2 = px.line(
        sdf,
        x="дата",
        y="сумма",
        color="инструмент",
        markers=True,
        hover_data=["степень"],
    )
    fig2.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(sdf, use_container_width=True, hide_index=True)

st.markdown("### Активность по сессиям")
sessions = list_sessions(USER_ID, limit=200)
if not sessions:
    st.caption("Пока нет сессий.")
else:
    rows = []
    for s in sessions:
        msgs = list_messages(s.id)
        rows.append(
            {
                "id": s.id,
                "начало": s.started_at,
                "конец": s.ended_at,
                "персона": s.persona,
                "модуль": s.module or "auto",
                "сообщений": len(msgs),
                "от пользователя": sum(1 for m in msgs if m.role == "user"),
                "от ИИ": sum(1 for m in msgs if m.role == "assistant"),
            }
        )
    sdf2 = pd.DataFrame(rows)
    st.dataframe(sdf2, use_container_width=True, hide_index=True)

    fig3 = px.bar(
        sdf2.head(30).iloc[::-1],
        x="начало",
        y="сообщений",
        color="персона",
    )
    fig3.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig3, use_container_width=True)
