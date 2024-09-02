import streamlit as st
import json

def load_models(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_models(models, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(models, file, ensure_ascii=False, indent=4)

def edit_model(models, index, new_config):
    models[index] = new_config
    return models

def delete_model(models, index):
    del models[index]
    return models

def add_model(models, new_item):
    models.append(new_item)
    return models

def models_page(file_path):
    models = load_models(file_path)

    st.title("大模型管理")

    for i, item in enumerate(models):
        with st.expander(f"{item['name']}"):
            new_name = st.text_input("名称", item['name'], key=f"model_name_{i}")
            new_api_key = st.text_input("API Key", item['api_key'], key=f"model_api_key_{i}", type="password")
            new_api_url = st.text_input("API URL", item['api_url'], key=f"model_api_url_{i}")
            new_model = st.text_input("模型", item['model'], key=f"model_model_{i}")
            if new_name != item['name'] or new_api_key != item['api_key'] or new_api_url != item['api_url'] or new_model != item['model']:
                new_config = {
                    'name': new_name,
                    'api_key': new_api_key,
                    'api_url': new_api_url,
                    'model': new_model
                }
                models = edit_model(models, i, new_config)
                st.session_state.models_changed = True

            if st.button("删除", key=f"delete_model_{i}"):
                models = delete_model(models, i)
                st.session_state.models_changed = True
                st.session_state.model_deleted = True

    if st.button("添加新模型"):
        new_item = {"name": "", "api_key": "", "api_url": "", "model": ""}
        models = add_model(models, new_item)
        st.session_state.models_changed = True

        with st.expander("新模型", expanded=True):
            new_name = st.text_input("名称", key=f"model_new_name")
            new_api_key = st.text_input("API Key", key=f"model_new_api_key", type="password")
            new_api_url = st.text_input("API URL", key=f"model_new_api_url")
            new_model = st.text_input("模型", key=f"model_new_model")
            new_item['name'] = new_name
            new_item['api_key'] = new_api_key
            new_item['api_url'] = new_api_url
            new_item['model'] = new_model

    if st.button("保存") or st.session_state.get('models_changed', False):
        save_models(models, file_path)
        st.success("大模型已保存")
        st.session_state.models_changed = False
        st.rerun()

    if st.session_state.get('model_deleted', False):
        save_models(models, file_path)
        st.session_state.model_deleted = False
        st.rerun()