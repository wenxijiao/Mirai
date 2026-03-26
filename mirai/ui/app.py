# ui/app.py
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

    def stream_parser():
        url = f"{SERVER_URL}/chat"
        payload = {
            "prompt": prompt,
            "session_id": st.session_state.session_id,
        }
        
        try:
            with requests.post(url, json=payload, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        yield chunk
        except Exception as e:
            yield f"[Backend Error] {e}"

    with st.chat_message("assistant"):
        response = st.write_stream(stream_parser())
        st.session_state.messages.append({"role": "assistant", "content": response})