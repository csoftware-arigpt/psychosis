"""Validated screening forms (PHQ-9, GAD-7, PCL-5, AUDIT, MDQ)."""
from __future__ import annotations

import streamlit as st

from core import score_screening, severity_for
from data import save_screening_result, list_screening_results
from prompts import SCREENING_INSTRUMENTS


st.set_page_config(page_title="Скрининг | Psychosis NXT", page_icon="📋", layout="wide")

if "user_id" not in st.session_state:
    st.warning("Сначала войди на главной странице.")
    st.stop()

USER_ID = st.session_state.user_id

st.title("📋 Скрининг")
st.caption(
    "Валидированные опросники. Результат — ориентир, не диагноз. "
    "При выраженных значениях имеет смысл показать клиницисту."
)

instr_code = st.selectbox(
    "Инструмент",
    options=list(SCREENING_INSTRUMENTS.keys()),
    format_func=lambda c: f"{c} — {SCREENING_INSTRUMENTS[c]['name']}",
)
instrument = SCREENING_INSTRUMENTS[instr_code]
st.markdown(f"**{instrument['description']}**")

with st.form(f"form_{instr_code}"):
    answers: list[int] = []
    for i, item in enumerate(instrument["items"]):
        choice = st.radio(
            f"{i+1}. {item}",
            options=instrument["scale"],
            format_func=lambda o: f"{o['score']} — {o['label']}",
            horizontal=True,
            key=f"{instr_code}_{i}",
        )
        answers.append(choice["score"])
    submitted = st.form_submit_button("Сохранить и оценить", type="primary")

if submitted:
    total = score_screening(instrument, answers)
    sev = severity_for(instrument, total)
    save_screening_result(USER_ID, instrument["code"], total, sev, answers)
    st.success(f"**Сумма:** {total} — **{sev}**")
    if instrument["code"] == "PHQ-9" and answers[-1] >= 1:
        st.error(
            "Ты отметил пункт 9 (мысли о смерти/самоповреждении). "
            "Это важный сигнал — пожалуйста, поговори со специалистом сегодня. "
            "Кризисная линия РФ: 8-800-2000-122 / US: 988."
        )

st.divider()
st.markdown("### История по инструменту")
history = [r for r in list_screening_results(USER_ID) if r.instrument_code == instr_code]
if not history:
    st.caption("Пока пусто.")
else:
    for r in reversed(history):
        st.write(f"- **{r.created_at:%Y-%m-%d %H:%M}** — {r.total_score} ({r.severity})")
