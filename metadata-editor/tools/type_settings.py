import streamlit as st
import sqlite3
from utils import load_settings, save_settings, edit_settings, delete_item, add_item

def settings_page(db_path):
    conn = sqlite3.connect(db_path)
    settings = load_settings(conn)
    conn.close()

    st.title("设置")

    tabs = st.tabs(['材料类型', '活动类型'])

    for i, setting_type in enumerate(['MATERIAL_TYPES', 'EVENT_TYPES']):
        with tabs[i]:
            st.header(f"{'材料类型' if setting_type == 'MATERIAL_TYPES' else '活动类型'}")
            
            for i, item in enumerate(settings[setting_type]):
                if item.get('deleted', False):
                    continue
                with st.expander(f"{item['label']}"):
                    new_label = st.text_input("标签", item['label'], key=f"{setting_type}_label_{i}")
                    new_description = st.text_area("描述", item['description'], key=f"{setting_type}_desc_{i}")
                    if new_label != item['label'] or new_description != item['description']:
                        settings = edit_settings(settings, setting_type, item, {'label': new_label, 'description': new_description})
                        st.session_state.settings_changed = True

                    if st.button("删除", key=f"delete_{setting_type}_{i}"):
                        settings = delete_item(settings, setting_type, i)
                        st.session_state.settings_changed = True
                        st.session_state.item_deleted = True

            if st.button(f"添加新{'材料类型' if setting_type == 'MATERIAL_TYPES' else '活动类型'}", key=f"add_{setting_type}"):
                new_item = {"label": "", "description": "", "deleted": False}
                settings = add_item(settings, setting_type, new_item)
                st.session_state.settings_changed = True

                with st.expander(f"新{'材料类型' if setting_type == 'MATERIAL_TYPES' else '活动类型'}", expanded=True):
                    new_label = st.text_input("标签", key=f"{setting_type}_new_label")
                    new_description = st.text_area("描述", key=f"{setting_type}_new_desc")
                    new_item['label'] = new_label
                    new_item['description'] = new_description

    if st.button("保存设置") or st.session_state.get('settings_changed', False):
        save_settings(settings, db_path)
        st.success("设置已保存")
        st.session_state.settings_changed = False
        st.rerun()

    if st.session_state.get('item_deleted', False):
        save_settings(settings, db_path)
        st.session_state.item_deleted = False
        st.rerun()