# ui/app.py
import json
import os
import streamlit as st
import requests

SERVER_URL = os.getenv("MIRAI_SERVER_URL", "http://127.0.0.1:8000")
DEFAULT_SESSION_ID = "ui_default"

st.set_page_config(page_title="Mirai", page_icon="🍭")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = DEFAULT_SESSION_ID

def render_tool_activity(placeholder, activities):
    if not activities:
        placeholder.empty()
        return

    content = "### Tool Activity\n" + "\n".join(f"- {item}" for item in activities)
    placeholder.markdown(content)

with st.sidebar:
    st.markdown("### Control Panel")
    if st.button("Clear Memory", use_container_width=True):
        try:
            response = requests.post(
                f"{SERVER_URL}/clear",
                params={"session_id": st.session_state.session_id},
                timeout=10,
            )
            response.raise_for_status()
            st.session_state.messages = []
            st.rerun()
        except requests.RequestException as e:
            st.error(f"Failed to clear memory: {e}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Say something to Mirai..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        tool_placeholder = st.empty()
        response_placeholder = st.empty()
        response_parts = []
        tool_activities = []
        had_error = False

        url = f"{SERVER_URL}/chat"
        payload = {
            "prompt": prompt,
            "session_id": st.session_state.session_id,
        }

        try:
            with requests.post(url, json=payload, stream=True) as response:
                response.raise_for_status()

                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue

                    event = json.loads(line)
                    event_type = event.get("type")

                    if event_type == "text":
                        response_parts.append(event.get("content", ""))
                        response_placeholder.markdown("".join(response_parts))
                    elif event_type == "tool_status":
                        tool_activities.append(event.get("content", ""))
                        render_tool_activity(tool_placeholder, tool_activities)
                    elif event_type == "error":
                        had_error = True
                        tool_placeholder.error(event.get("content", "Unknown backend error."))
        except (requests.RequestException, json.JSONDecodeError) as e:
            had_error = True
            tool_placeholder.error(f"Backend request failed: {e}")

        response_text = "".join(response_parts)
        if response_text and not had_error:
            st.session_state.messages.append({"role": "assistant", "content": response_text})