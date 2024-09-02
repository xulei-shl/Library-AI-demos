import streamlit as st
import json

def load_prompts(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_prompts(prompts, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(prompts, file, ensure_ascii=False, indent=4)

def edit_prompt(prompts, index, new_label, new_description):
    prompts[index]['label'] = new_label
    prompts[index]['description'] = new_description
    return prompts

def delete_prompt(prompts, index):
    del prompts[index]
    return prompts

def add_prompt(prompts, new_item):
    prompts.append(new_item)
    return prompts

def prompts_page(file_path):
    prompts = load_prompts(file_path)

    st.title("提示词管理")

    for i, item in enumerate(prompts):
        with st.expander(f"{item['label']}"):
            new_label = st.text_input("标签", item['label'], key=f"prompt_label_{i}")
            new_description = st.text_area("描述", item['description'], key=f"prompt_desc_{i}")
            if new_label != item['label'] or new_description != item['description']:
                prompts = edit_prompt(prompts, i, new_label, new_description)
                st.session_state.prompts_changed = True

            if st.button("删除", key=f"delete_prompt_{i}"):
                prompts = delete_prompt(prompts, i)
                st.session_state.prompts_changed = True
                st.session_state.prompt_deleted = True

    if st.button("添加新提示词"):
        new_item = {"label": "", "description": ""}
        prompts = add_prompt(prompts, new_item)
        st.session_state.prompts_changed = True

        with st.expander("新提示词", expanded=True):
            new_label = st.text_input("标签", key=f"prompt_new_label")
            new_description = st.text_area("描述", key=f"prompt_new_desc")
            new_item['label'] = new_label
            new_item['description'] = new_description

    if st.button("保存") or st.session_state.get('prompts_changed', False):
        save_prompts(prompts, file_path)
        st.success("提示词已保存")
        st.session_state.prompts_changed = False
        st.rerun()

    if st.session_state.get('prompt_deleted', False):
        save_prompts(prompts, file_path)
        st.session_state.prompt_deleted = False
        st.rerun()