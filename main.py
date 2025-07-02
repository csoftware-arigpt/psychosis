import streamlit as st
from g4f.client import Client
from g4f.Provider import Copilot
import prompts
import uuid
import json

st.markdown("# Psychosis NXT")
st.text("New way to talk AI with people")

g4f_client = Client()

def format_conversation(messages):
    return [{"role": m["role"], "content": m["content"]} for m in messages]

def generate_ai_response(role, adv_par, messages):
    conversation = format_conversation(messages)
    prompt = f"ROLE: {role}\nMESSAGES: {conversation}\n{adv_par}"
    print(prompt)
    response = g4f_client.chat.completions.create(
        model="o1",
        messages=[
            {"role": "system", "content": prompts.style_copy},
            {"role": "user", "content": prompt}
        ],
        provider=Copilot
    )
    return response.choices[0].message.content.strip()

with st.sidebar:
    ai_mode = st.selectbox(
        "AI Mode",
        ("Conversation", "Chat assistance", "Analyse")
    )

if ai_mode == "Chat assistance":

    if "messages" not in st.session_state:
        st.session_state.messages = []

    col1, col2 = st.columns(2)

    with col1:
        with st.container(height=400):
            role_selection, message_input = st.columns(2)

            with role_selection:
                chat_role = st.selectbox("Role", options=("Sender", "Reciever"), label_visibility="collapsed")

            with message_input:
                chat_input = st.chat_input("Message")
                if chat_input:
                    st.session_state.messages.append({
                        "role": chat_role,
                        "content": chat_input,
                        "ai_generated": False,
                        "uuid": str(uuid.uuid4())
                    })

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    role_label = f"##### {message['role']} {'(AI)' if message['ai_generated'] else ''}"
                    st.markdown(role_label)
                    st.markdown(message["content"])

                    if message["ai_generated"]:
                        if st.button("Regenerate", key=message['uuid']):
                            with st.status("Regenerating answer"):
                                adv_par = message.get("adv_params", "")
                                role = message["role"]
                                while st.session_state.messages and st.session_state.messages[-1]["uuid"] != message["uuid"]:
                                    st.session_state.messages.pop()
                                if st.session_state.messages:
                                    st.session_state.messages.pop()
                                ai_reply = generate_ai_response(role, adv_par, st.session_state.messages)
                                st.session_state.messages.append({
                                    "role": role,
                                    "content": ai_reply,
                                    "ai_generated": True,
                                    "adv_params": adv_par,
                                    "uuid": str(uuid.uuid4())
                                })
                                st.rerun()
            progress_container = st.container()
    with col2:
        with st.container(height=400):
            st.file_uploader(
                "Upload your chat export to continue (.JSON)",
                accept_multiple_files=False,
                type="json"
            )

            role_picker = st.selectbox("Select role", options=("Sender", "Reciever"))

            adv_par = st.text_input("Instructions (optional)", placeholder="Instructions", label_visibility="collapsed")
            if st.button("Generate", use_container_width=True):
                    with progress_container:
                        with st.status("Generating answer"):
                            adv_text = f"ADVANCED INSTRUCTIONS: {adv_par}" if adv_par else ""
                            ai_reply = generate_ai_response(role_picker, adv_text, st.session_state.messages)
                            st.session_state.messages.append({
                                "role": role_picker,
                                "content": ai_reply,
                                "ai_generated": True,
                                "adv_params": adv_text,
                                "uuid": str(uuid.uuid4())
                            })
                            st.rerun()

    st.container(height=100).write("Export chat")

elif ai_mode == "Analyse":
    st.write("Block 3 (under construction)")
