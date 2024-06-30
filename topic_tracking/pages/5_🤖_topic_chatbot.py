import streamlit as st
from tools.topic_path import load_topics, get_file_path
import os
import subprocess
import time
from tools.kill_qdrant import kill_qdrant_instances_one, kill_qdrant_instances_two



def knowledge_bot_page():
    st.title("🫧 AI 聊天机器人")
    st.markdown("---")


    if 'topics_df' not in st.session_state:
        st.session_state.topics_df = load_topics()

    selected_topic = st.selectbox("选择主题词", st.session_state.topics_df['topic'].tolist())
    folder_path = get_file_path(selected_topic)
    if st.button("启动 AIBot"):
        # 设置环境变量
        os.environ["QDRANT_PATH"] = os.path.join(folder_path, "local_qdrant")
        # 运行 Chainlit 脚本
        script_path = os.path.join(os.path.dirname(__file__), "..", "chainlit_topic.py")
        subprocess.Popen(["chainlit", "run", script_path, "-w"])
        time.sleep(3.5)
        st.success("🥳 Chainlit 脚本已启动！")
        time.sleep(1.5)
        st.rerun()

    if st.button("关闭 AIBot"):
        kill_qdrant_instances_one()
        kill_qdrant_instances_two()
        time.sleep(3.5)
        st.info("Chainlit 脚本已关闭")
        time.sleep(1.5)
        st.rerun()

if __name__ == "__main__":
    knowledge_bot_page()