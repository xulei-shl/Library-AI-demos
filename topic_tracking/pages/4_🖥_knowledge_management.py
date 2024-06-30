import streamlit as st
from tools.topic_path import load_topics, get_file_path
from tools.csv2md import convert_csv_to_md
from tools.md_spli_emb import process_md_file, load_and_split_document, get_split_examples
import os
import pandas as pd

def reset_state():
    for key in ['show_examples', 'optimize']:
        if key in st.session_state:
            del st.session_state[key]

def knowledge_base_management_page():
    st.title("⚡️ 知识库管理")
    st.markdown("---")
    st.markdown("### 🗃️ CSV 文献库转为 Markdown ")

    if 'topics_df' not in st.session_state:
        st.session_state.topics_df = load_topics()

    selected_topic = st.selectbox("选择主题词", st.session_state.topics_df['topic'].tolist())
    if st.button("开始转换"):
        convert_csv_to_md(selected_topic, st=st)

    st.markdown("---")
    st.markdown("### 💾 MD 文本向量化 ")

    folder_path = get_file_path(selected_topic)
    md_files = [f for f in os.listdir(folder_path) if f.endswith('.md')]

    if md_files:
        selected_file = st.selectbox("选择要向量化的文件", md_files)
        
        if 'show_examples' not in st.session_state:
            st.session_state.show_examples = False
        
        if 'optimize' not in st.session_state:
            st.session_state.optimize = False

        col1, col2 = st.columns(2)
        with col1:
            if st.button("向量存储"):
                st.session_state.show_examples = True
                st.session_state.optimize = False
        with col2:
            if st.button("取消"):
                reset_state()
                st.rerun()

        if st.session_state.show_examples:
            md_file_path = os.path.join(folder_path, selected_file)
            docs = load_and_split_document(md_file_path)
            st.info(get_split_examples(docs))

            col1, col2 = st.columns(2)
            with col1:
                if st.button("确认"):
                    result = process_md_file(selected_topic, selected_file)
                    st.success(result)
                    st.session_state.show_examples = False
            with col2:
                if st.button("优化"):
                    st.session_state.optimize = True

        if st.session_state.optimize:
            st.markdown("### 优化参数")
            separators = st.text_input("Separators (用逗号分隔)", "---")
            chunk_size = st.number_input("Chunk Size", min_value=100, max_value=5000, value=1000, step=100)
            chunk_overlap = st.number_input("Chunk Overlap", min_value=0, max_value=1000, value=100, step=10)

            if st.button("重新分割"):
                md_file_path = os.path.join(folder_path, selected_file)
                separators_list = [sep.strip() for sep in separators.split(',')]
                docs = load_and_split_document(md_file_path, separators=separators_list, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                st.info(get_split_examples(docs))

            if st.button("确认并向量化"):
                result = process_md_file(selected_topic, selected_file, separators=[sep.strip() for sep in separators.split(',')], chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                st.success(result)
                st.session_state.optimize = False
                st.session_state.show_examples = False

    else:
        st.warning("当前主题词文件夹下没有MD文件。")

    st.markdown("---")
    st.markdown("### 📊 向量化日志 ")

    log_file_name = '向量化日志.xlsx'
    log_file_path = os.path.join(folder_path, log_file_name)

    # 读取Excel文件
    if os.path.exists(log_file_path):
        df = pd.read_excel(log_file_path)
        st.dataframe(df)  # 使用st.dataframe显示数据
    else:
        st.error("日志文件不存在")        

if __name__ == "__main__":
    knowledge_base_management_page()