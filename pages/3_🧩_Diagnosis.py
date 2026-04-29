"""Diagnostic picture synthesis page."""
from __future__ import annotations

import streamlit as st

from core import synthesize_diagnosis
from data import (
    list_screening_results,
    list_sessions,
    list_messages,
    save_diagnosis,
    list_diagnoses,
    list_moods,
)
from prompts import DSM5_CRITERIA, ICD11_CRITERIA


st.set_page_config(page_title="Диагноз | Psychosis NXT", page_icon="🧩", layout="wide")

if "user_id" not in st.session_state:
    st.warning("Сначала войди на главной странице.")
    st.stop()

USER_ID = st.session_state.user_id

st.title("🧩 Диагностическая картина")
st.caption(
    "Рабочая гипотеза по DSM-5/ICD-11 на основе скрининга, диалога и истории "
    "настроения. **Не клинический диагноз.**"
)

with st.expander("Справка: DSM-5 и ICD-11"):
    tab1, tab2 = st.tabs(["DSM-5", "ICD-11"])
    with tab1:
        for code, c in DSM5_CRITERIA.items():
            st.markdown(f"**{code} — {c['name']}**")
            st.caption(c.get("min_criteria", ""))
            for crit in c.get("criteria", []):
                st.markdown(f"- {crit}")
            st.divider()
    with tab2:
        for code, c in ICD11_CRITERIA.items():
            st.markdown(f"- **{code}** — {c['name']} (см. {c.get('see','')})")


def _collect_inputs() -> tuple[list[dict], list[str], list[str]]:
    screenings = [
        {
            "instrument_code": r.instrument_code,
            "total_score": r.total_score,
            "severity": r.severity,
        }
        for r in list_screening_results(USER_ID)
    ]
    transcript: list[str] = []
    for s in list_sessions(USER_ID, limit=5):
        for m in list_messages(s.id):
            if m.role == "user":
                t = m.content.strip().replace("\n", " ")
                if len(t) > 200:
                    t = t[:200] + "…"
                transcript.append(f"[{s.id}] {t}")
    transcript = transcript[-50:]

    moods = list_moods(USER_ID)
    history = [
        f"{m.created_at:%Y-%m-%d}: настроение {m.score}/10"
        + (f" — {m.note}" if m.note else "")
        for m in moods[-30:]
    ]
    return screenings, transcript, history


col1, col2 = st.columns([1, 2])
with col1:
    if st.button("🔄 Сгенерировать картину", type="primary"):
        screenings, transcript, history = _collect_inputs()
        with st.spinner("Синтезирую..."):
            md = synthesize_diagnosis(screenings, transcript, history)
        save_diagnosis(USER_ID, md)
        st.success("Готово")

with col2:
    st.caption("Используются: последние 5 сессий, все скрининги, последние 30 записей настроения.")

st.divider()
st.markdown("### История диагностических картин")
diags = list_diagnoses(USER_ID)
if not diags:
    st.caption("Пока пусто. Сгенерируй первую картину выше.")
for d in diags:
    with st.expander(f"{d.created_at:%Y-%m-%d %H:%M}"):
        st.markdown(d.content_md)
