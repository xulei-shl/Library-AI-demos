import streamlit as st
import json

def load_knowledge_bases(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_knowledge_bases(knowledge_bases, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(knowledge_bases, file, ensure_ascii=False, indent=4)

def edit_knowledge_base(knowledge_bases, index, new_config):
    knowledge_bases[index] = new_config
    return knowledge_bases

def delete_knowledge_base(knowledge_bases, index):
    del knowledge_bases[index]
    return knowledge_bases

def add_knowledge_base(knowledge_bases, new_item):
    knowledge_bases.append(new_item)
    return knowledge_bases

def knowledge_bases_page(file_path):
    knowledge_bases = load_knowledge_bases(file_path)

    st.title("知识库管理")

    for i, item in enumerate(knowledge_bases):
        with st.expander(f"{item['name']}"):
            new_name = st.text_input("名称", item['name'], key=f"kb_name_{i}")
            new_api_key = st.text_input("API Key", item['api_key'], key=f"kb_api_key_{i}", type="password")  # Masked input
            new_api_url = st.text_input("API URL", item['api_url'], key=f"kb_api_url_{i}")
            if new_name != item['name'] or new_api_key != item['api_key'] or new_api_url != item['api_url']:
                new_config = {
                    'name': new_name,
                    'api_key': new_api_key,
                    'api_url': new_api_url
                }
                knowledge_bases = edit_knowledge_base(knowledge_bases, i, new_config)
                st.session_state.knowledge_bases_changed = True

            if st.button("删除", key=f"delete_kb_{i}"):
                knowledge_bases = delete_knowledge_base(knowledge_bases, i)
                st.session_state.knowledge_bases_changed = True
                st.session_state.knowledge_base_deleted = True

    if st.button("添加新知识库"):
        new_item = {"name": "", "api_key": "", "api_url": ""}
        knowledge_bases = add_knowledge_base(knowledge_bases, new_item)
        st.session_state.knowledge_bases_changed = True

        with st.expander("新知识库", expanded=True):
            new_name = st.text_input("名称", key=f"kb_new_name")
            new_api_key = st.text_input("API Key", key=f"kb_new_api_key", type="password")  # Masked input
            new_api_url = st.text_input("API URL", key=f"kb_new_api_url")
            new_item['name'] = new_name
            new_item['api_key'] = new_api_key
            new_item['api_url'] = new_api_url

    if st.button("保存") or st.session_state.get('knowledge_bases_changed', False):
        save_knowledge_bases(knowledge_bases, file_path)
        st.success("知识库已保存")
        st.session_state.knowledge_bases_changed = False
        st.rerun()

    if st.session_state.get('knowledge_base_deleted', False):
        save_knowledge_bases(knowledge_bases, file_path)
        st.session_state.knowledge_base_deleted = False
        st.rerun()