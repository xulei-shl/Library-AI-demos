import streamlit as st
import json
from tools.type_settings import settings_page
from tools.relationship_settings import relationship_settings_page
from tools.prompts_manager import prompts_page
from tools.models_manager import models_page
from tools.knowledge_manager import knowledge_bases_page
from utils import load_settings
import sqlite3
from data_loading import load_data_page
import os


base_dir = os.path.dirname(os.path.abspath(__file__))

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = []
if 'model' not in st.session_state:
    st.session_state.model = None
if 'settings' not in st.session_state:
    st.session_state.settings = None

# Import page modules
import data_loading
import data_browsing

def handle_url_params():
    if 'data' in st.query_params:
        data_str = st.query_params['data']
        try:
            st.session_state.data = json.loads(data_str)
            st.success("成功从 URL 参数加载数据。")
        except json.JSONDecodeError:
            st.error("无法解析 URL 中的数据参数。请确保它是有效的 JSON 格式。")
        st.query_params.clear()
        st.rerun()

def auto_load_data():
    if 'data' not in st.session_state or not st.session_state.data:
        st.info("正在自动加载数据...")
        load_data_page(db_path)
        return True  # 表示数据被加载
    return False  # 表示数据已经存在，没有加载

def display_data_info():
    st.success(f"已加载 {len(st.session_state.data)} 条演出事件数据")
    if st.session_state.settings:
        st.success("设置已加载")
        st.markdown(f"""
        - 事件类型: {len(st.session_state.settings['EVENT_TYPES'])} 项
        - 材料类型: {len(st.session_state.settings['MATERIAL_TYPES'])} 项
        - 材料关系类型: {len(st.session_state.settings['materials_relationship'])} 项
        - 场地关系类型: {len(st.session_state.settings['architectures_relationship'])} 项
        - 作品关系类型: {len(st.session_state.settings['works_relationship'])} 项
        - 团体关系类型: {len(st.session_state.settings['groups_relationship'])} 项
        - 事件关系类型: {len(st.session_state.settings['events_relationship'])} 项
        - 人物关系类型: {len(st.session_state.settings['persons_relationship'])} 项
        """)


st.set_page_config(page_title="JSON Data Editor", layout="wide")

# Load settings
db_path = 'E:\\scripts\\jiemudan\\2\\output\\database\\database.db'
if st.session_state.settings is None:
    conn = sqlite3.connect(db_path)
    st.session_state.settings = load_settings(conn)
    conn.close()

models_file_path = os.path.join(base_dir, 'jsondata', 'llm_settings.json')
konwledge_file_path = os.path.join(base_dir, 'jsondata', 'knowledge_settings.json')
prompts_file_path = os.path.join(base_dir, 'jsondata', 'prompts.json')

# Sidebar for navigation
st.sidebar.title("实体编辑DEMO")
page = st.sidebar.radio("选择页面", ["数据加载", "实体编辑", "事件类型词表", "实体关系词表", "大模型管理", "提示词管理", "知识库管理"])


if page == "数据加载":
    if auto_load_data():
        st.success("数据已自动加载")
    if st.button("重新加载数据"):
        load_data_page(db_path)
        st.success("数据已重新加载")
        st.rerun()
    display_data_info()
elif page == "实体编辑":
    data_browsing.browse_data_page()
elif page == "事件类型词表":
    settings_page(db_path)
elif page == "实体关系词表":
    relationship_settings_page(db_path)
elif page == "大模型管理":
    models_page(models_file_path)
elif page == "知识库管理":
    knowledge_bases_page(konwledge_file_path)  
elif page == "提示词管理": 
    prompts_page(prompts_file_path)


if __name__ == "__main__":
    handle_url_params()