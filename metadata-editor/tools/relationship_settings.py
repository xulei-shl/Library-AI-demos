import streamlit as st
import sqlite3
from utils import load_settings, save_settings, edit_settings, delete_item, add_item

RELATIONSHIP_TABLES = [
    'materials_relationship',
    'architectures_relationship',
    'works_relationship',
    'groups_relationship',
    'events_relationship',
    'persons_relationship'
]

def add_new_item(settings, table, table_name_map):
    new_item = {"label": "", "description": "", "deleted": False}
    temp_key = f"temp_{table}"
    if temp_key not in st.session_state:
        st.session_state[temp_key] = new_item.copy()

    with st.expander(f"新的{table_name_map[table]}", expanded=True):
        new_label = st.text_input("标签", key=f"{table}_new_label")
        new_description = st.text_area("描述", key=f"{table}_new_desc")
        
        if new_label or new_description:
            if new_label != st.session_state[temp_key]['label'] or new_description != st.session_state[temp_key]['description']:
                st.session_state[temp_key]['label'] = new_label
                st.session_state[temp_key]['description'] = new_description
                add_item(settings, table, st.session_state[temp_key])
                st.session_state.settings_changed = True
                del st.session_state[temp_key]
                st.success("新项目已添加")
                st.experimental_rerun()

def relationship_settings_page(db_path):
    st.title("关系词表设置")
    conn = sqlite3.connect(db_path)
    settings = load_settings(conn)
    conn.close()

    table_name_map = {
        'materials_relationship': '材料关系类型',
        'architectures_relationship': '场地关系类型',
        'works_relationship': '作品关系类型',
        'groups_relationship': '团体关系类型',
        'events_relationship': '事件关系类型',
        'persons_relationship': '人物关系类型'
    }

    tabs = st.tabs([table_name_map[table] for table in RELATIONSHIP_TABLES])

    for i, table in enumerate(RELATIONSHIP_TABLES):
        with tabs[i]:
            st.header(table_name_map[table])

            for j, item in enumerate(settings[table]):
                if item.get('deleted', False):
                    continue
                with st.expander(f"{item['label']}"):
                    new_label = st.text_input("标签", item['label'], key=f"{table}_label_{j}")
                    new_description = st.text_area("描述", item['description'], key=f"{table}_desc_{j}")
                    if new_label != item['label'] or new_description != item['description']:
                        settings = edit_settings(settings, table, item, {'label': new_label, 'description': new_description})
                        st.session_state.settings_changed = True

                    if st.button("删除", key=f"delete_{table}_{j}"):
                        settings = delete_item(settings, table, j)
                        st.session_state.settings_changed = True

            if st.button(f"添加新的{table_name_map[table]}", key=f"add_{table}"):
                new_item = {"label": "", "description": "", "deleted": False}
                settings = add_item(settings, table, new_item)
                st.session_state.settings_changed = True

                with st.expander(f"新{table_name_map[table]}", expanded=True):
                    new_label = st.text_input("标签", key=f"{table}_new_label")
                    new_description = st.text_area("描述", key=f"{table}_new_desc")
                    new_item['label'] = new_label
                    new_item['description'] = new_description

    if st.button("保存设置") or st.session_state.get('settings_changed', False):
        save_settings(settings, db_path)
        st.success("设置已保存")
        st.session_state.settings_changed = False
        st.experimental_rerun()

    if st.session_state.get('item_deleted', False):
        save_settings(settings, db_path)
        st.session_state.item_deleted = False
        st.experimental_rerun()
