import streamlit as st
from utils import load_from_db, load_settings, get_column_names
import sqlite3
import json

def load_data_page(db_path):
    conn = sqlite3.connect(db_path)
    
    # 显示表结构
    st.write("数据库表结构示例:")
    tables = ['main_table', 'version_history', 'EVENT_TYPES']
    for table in tables:
        columns = get_column_names(conn, table)
        st.info(f"{table} 列: {', '.join(columns)}")
    
    # Load settings
    settings = load_settings(conn)
    st.session_state.settings = settings
    st.success("设置已加载")
    st.markdown(f"""
    - 事件类型: {len(settings['EVENT_TYPES'])} 项
    - 材料类型: {len(settings['MATERIAL_TYPES'])} 项
    - 材料关系类型: {len(settings['materials_relationship'])} 项
    - 场地关系类型: {len(settings['architectures_relationship'])} 项
    - 作品关系类型: {len(settings['works_relationship'])} 项
    - 团体关系类型: {len(settings['groups_relationship'])} 项
    - 事件关系类型: {len(settings['events_relationship'])} 项
    - 人物关系类型: {len(settings['persons_relationship'])} 项
    """)

    
    # Load main data
    db_data = load_from_db(conn)
    conn.close()
    
    if db_data:
        st.write("开始加载数据...")
        try:
            st.session_state.data = [json.loads(item['data']) for item in db_data]
            st.session_state.data_ids = {item['id']: item['id'] for item in db_data}  # Update to use 'id' field directly

            st.info(f"Data IDs: {', '.join(st.session_state.data_ids.keys())}")

            # 处理嵌套的列表结构
            flattened_data = []
            for i, item in enumerate(st.session_state.data):
                if isinstance(item, dict) and 'performingEvent' in item:
                    flattened_data.append((i, 0, item['performingEvent']))
                elif isinstance(item, list):
                    for j, sub_item in enumerate(item):
                        if isinstance(sub_item, dict) and 'performingEvent' in sub_item:
                            flattened_data.append((i, j, sub_item['performingEvent']))
            st.session_state.flattened_data = flattened_data
            
            st.success(f"成功加载 {len(st.session_state.data)} 条数据")
            st.write("---")
            st.info("数据示例:")
            st.json(st.session_state.data[:1])
            return True
        except Exception as e:
            st.error(f"处理数据时出错: {str(e)}")
            return False
    else:
        st.warning("未找到数据或数据结构不正确")
        return False
