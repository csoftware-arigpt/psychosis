# Psychosis NXT

A bot for active personality assessment and direct work with the user's
problems through a dialogue that imitates real conversation. It runs
screening, builds a diagnostic picture against key criteria, and conducts
adaptive therapeutic work within the session.

> ⚠️ Not a substitute for clinical care. Prototype.

## Features

- **Therapy** — live chat split into multiple messages (`<newmessage time="N">`),
  with personas and adaptive selection of a therapeutic module
  (CBT / DBT / REBT / Schema / MI / BA / CBT-i / exposure / 5-4-3-2-1).
- **Screening** — validated questionnaires: PHQ-9, GAD-7, PCL-5, AUDIT, MDQ.
- **Diagnostic picture** — LLM synthesis against DSM-5 / ICD-11 based on
  screening, dialogue, and mood history.
- **Analytics** — mood and screening-score curves, session-level activity.
- **Style copying** — upload a Telegram export (`result.json`) and the AI
  writes in the chosen user's style.
- **Crisis detection** — chat triggers a banner with hotlines.
- **Per-user persistence** — users, sessions, messages, screenings,
  diagnoses, mood, style profiles in SQLite.

## Install

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Layout

```
psychosis/
├── app.py                  # entry + login + dashboard
├── pages/                  # Streamlit auto-routed
│   ├── 1_💬_Therapy.py
│   ├── 2_📋_Screening.py
│   ├── 3_🧩_Diagnosis.py
│   ├── 4_📈_Analytics.py
│   └── 5_⚙️_Settings.py
├── core/
│   ├── llm.py              # backend dispatch (g4f / OpenAI / Anthropic)
│   ├── llm_official.py     # OpenAI + Anthropic clients
│   ├── chunker.py          # <newmessage time="N"> parser
│   ├── analyzer.py         # scoring, severity, crisis, dx synthesis
│   └── tg_parser.py        # TG export → style profile
├── data/
│   ├── db.py               # SQLite persistence
│   └── models.py           # Pydantic models
└── prompts/
    ├── style.py            # live-human + TG style copy
    ├── screening.py        # instruments + chat-driven screening prompt
    ├── diagnostic.py       # DSM-5 / ICD-11 + synthesis prompt
    ├── therapy.py          # 10 modules + system prompt
    └── personas.py         # 5 personas
```

## LLM backends

| Backend | Purpose | Required |
|---|---|---|
| `g4f` (default) | Free providers | Nothing, falls back through the chain |
| `openai` | Official OpenAI API | `OPENAI_API_KEY` (optional `OPENAI_BASE_URL` for Azure / Together / OpenRouter) |
| `anthropic` | Claude Messages API | `ANTHROPIC_API_KEY` |

Switch via env, or at runtime in **⚙️ Settings → LLM backend**.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PSYCHOSIS_DB` | `psychosis.db` | SQLite path |
| `PSYCHOSIS_BACKEND` | `g4f` | `g4f` / `openai` / `anthropic` |
| `PSYCHOSIS_MODEL` | `gpt-4o-mini` | Model (Anthropic default: `claude-sonnet-4-6`) |
| `PSYCHOSIS_PROVIDERS` | `Copilot,DDG,Blackbox,DarkAI,Liaobots` | g4f fallback chain |
| `OPENAI_API_KEY` | — | OpenAI key |
| `OPENAI_BASE_URL` | — | Optional (proxy / Azure / OpenRouter) |
| `ANTHROPIC_API_KEY` | — | Anthropic key |

## Origins

- Live-chat split + multi-message rhythm — ported from
  `psychosis-legacy/penesnakata/bot.py`.
- Streamlit scaffold + AI Mode selectbox — from the old `psychosis/main.py`
  (fully rewritten).
- Screening instruments — public domain (PHQ, GAD, PCL, AUDIT, MDQ).

## Disclaimer

Not a clinical tool. Do not use it to diagnose or treat. If something hurts,
see a licensed professional.
