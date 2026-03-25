# ui/app.py
import os
import streamlit as st
import requests

SERVER_URL = os.getenv("MIRAI_SERVER_URL", "http://127.0.0.1:8000")
DEFAULT_SESSION_ID = "ui_default"

# 页面基础设置
st.set_page_config(page_title="Mirai", page_icon="🍭")

# 初始化前端的显示列表（只用于屏幕刷新时重绘UI，不发给后端）
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = DEFAULT_SESSION_ID

# 侧边栏：放一些控制按钮
with st.sidebar:
    st.markdown("### 控制面板")
    if st.button("🧹 清空记忆 (重新开始)", use_container_width=True):
        # 呼叫后端的 /clear 接口清空真正的记忆
        try:
            requests.post(
                f"{SERVER_URL}/clear",
                params={"session_id": st.session_state.session_id},
            )
            st.session_state.messages = [] # 清空屏幕
            st.rerun()
        except:
            st.error("无法连接到后端")

# 1. 遍历并画出屏幕上已有的历史对话
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. 接收用户底部输入
if prompt := st.chat_input("对 Mirai 说点什么吧..."):
    
    # 把用户的话画在屏幕上
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. 从 FastAPI 接收流式打字机效果
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
            yield f"⚠️ 后端连接异常: {e}"

    # 画出 AI 的回复框，并执行流式输出
    with st.chat_message("assistant"):
        response = st.write_stream(stream_parser())
        # 把 AI 回答完的完整句子存入前端显示列表
        st.session_state.messages.append({"role": "assistant", "content": response})