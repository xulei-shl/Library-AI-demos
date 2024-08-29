import streamlit as st
import pandas as pd
import json
import os
from utils import save_to_indexeddb, create_pydantic_model

def load_data_page():
    st.title("数据加载")
    
    uploaded_file = st.file_uploader("选择一个 JSON 文件", type="json")
    if uploaded_file is not None:
        st.write("开始加载数据...")
        try:
            json_data = json.load(uploaded_file)
            st.session_state.data = json_data
            st.write(f"成功加载 {len(st.session_state.data)} 条数据")
            
            save_to_indexeddb(st.session_state.data)
            #st.success("数据加载成功！")
            st.write("---")
            if 'data' in st.session_state:
                st.write("数据示例:")
                st.json(st.session_state.data[:2])
        except Exception as e:
            st.error(f"处理数据时出错: {str(e)}")
