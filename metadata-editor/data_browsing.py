import streamlit as st
import json
from utils import save_to_db, load_settings
from typing import Any, Dict, List
import api_utils
import pyperclip
import uuid
from tools.prompts_manager import load_prompts
from tools.knowledge_manager import load_knowledge_bases
from tools.models_manager import load_models
import os
import copy


base_dir = os.path.dirname(os.path.abspath(__file__))

# 准备调整 上一条下一条按钮。使得页面垂直居中

def display_prompt_ui(key_suffix: str, confirm_function):
    """
    显示提示词选择、用户输入/自定义提示词和确认按钮部分
    :param key_suffix: 唯一的关键字后缀，用于区分不同的输入字段和按钮
    :param confirm_function: 点击确认按钮时调用的函数
    """
    models_file_path = os.path.join(base_dir, 'jsondata', 'llm_settings.json')
    konwledge_file_path = os.path.join(base_dir, 'jsondata', 'knowledge_settings.json')
    prompts_file_path = os.path.join(base_dir, 'jsondata', 'prompts.json')
    
    key_suffix_zh = {
        'knowledge': '知识库',
        'qa': '问答'
    }.get(key_suffix, key_suffix)
    
    st.warning(f"{key_suffix_zh} - AI")

    if key_suffix == 'qa':
        models = load_models(models_file_path)
        api_options = {model['name']: model for model in models}
        selected_api = st.selectbox("选择大模型:", options=list(api_options.keys()), key=f"api_selectbox_{key_suffix}")
        api_config = api_options[selected_api]
    elif key_suffix == 'knowledge':
        knowledge_bases = load_knowledge_bases(konwledge_file_path)
        api_options = {kb['name']: kb for kb in knowledge_bases}
        selected_api = st.selectbox("选择知识库:", options=list(api_options.keys()), key=f"api_selectbox_{key_suffix}")
        api_config = api_options[selected_api]

    st.write("---") 

    if 'prompt_options' not in st.session_state:
        prompts = load_prompts(prompts_file_path)
        st.session_state.prompt_options = [item['label'] for item in prompts]
        st.session_state.candidates = {item['label']: item['description'] for item in prompts}
    
    selected_label = st.selectbox("提示词选择:", 
                                   options=st.session_state.prompt_options,
                                   index=0,
                                   key=f"prompt_selectbox_{key_suffix}")

    custom_text = st.session_state.get(f"custom_text_{key_suffix}", "")
    clipboard_text = pyperclip.paste() or ""
    st.text_area("用户输入 / 自定义提示词:", value=clipboard_text, key=f"custom_text_{key_suffix}")

    if st.button("确认", key=f"confirm_{key_suffix}"):
        if selected_label == "请选择一个操作":
            combined_text = custom_text
        else:
            st.session_state.selected_label = selected_label
            selected_description = st.session_state.candidates[selected_label]
            combined_text = f"{selected_description}: {custom_text}"

        if key_suffix == 'qa':
            result = confirm_function(combined_text, api_config['api_key'], api_config['api_url'], api_config['model'])
        elif key_suffix == 'knowledge':
            result = confirm_function(combined_text, api_config['api_key'], api_config['api_url'])

        st.session_state.search_result = result
        st.session_state.show_prompts = True  # 保持 show_prompts 为 True
        return result

    return None

def browse_data_page():
    st.title("实体编辑")
    filtered_data = [event for event in st.session_state.flattened_data if not event[2].get('deleted', False)]
    st.session_state.flattened_data = filtered_data

    if 'current_index' in st.session_state:
        current_index = st.session_state.current_index
        current_data = st.session_state.flattened_data[current_index][2]

    with st.sidebar:
        st.sidebar.info(f"当前数据条数: {len(st.session_state.data)}")
        st.write("---")
        st.markdown("""
        <h2>🔗 实体 / LLM API</h4>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("👤", help="搜索人名"):
                st.session_state.show_prompts = False
                st.session_state.search_result = None
                clipboard_text = pyperclip.paste()
                if clipboard_text:
                    result = api_utils.get_person_uri(clipboard_text)
                    if result is None:
                        st.session_state.search_result = "没有搜索到结果"
                    else:
                        st.session_state.search_result = result
                    st.session_state.current_page = 1
        with col2:
            if st.button("📖", help="AI 知识库"):
                st.session_state.show_prompts = True
                st.session_state.selected_label = None
                st.session_state.search_result = None
                st.session_state.prompt_type = 'knowledge'

        with col3:
            if st.button("🤖", help="AI 问答"):
                st.session_state.show_prompts = True
                st.session_state.selected_label = None
                st.session_state.search_result = None
                st.session_state.prompt_type = 'qa'

        if st.session_state.get('show_prompts', False):
            if st.session_state.get('prompt_type') == 'knowledge':
                display_prompt_ui("knowledge", api_utils.dify_request)
                
            elif st.session_state.get('prompt_type') == 'qa':
                display_prompt_ui("qa", api_utils.llm_requstion)

        # Display search result in the main content area
        if 'search_result' in st.session_state:
            st.markdown("---")
            if isinstance(st.session_state.search_result, dict) and 'data' in st.session_state.search_result:
                st.write("人名规范库结果:")

                # Pagination controls
                if 'current_page' not in st.session_state:
                    st.session_state.current_page = 1
                total_pages = st.session_state.search_result['pager']['pageCount']  # Get total pages from API response
                col1, col2, col3 = st.columns([2, 2, 2])
                with col1:
                    if st.button("⬅️") and st.session_state.current_page > 1:
                        st.session_state.current_page -= 1
                        clipboard_text = pyperclip.paste()
                        result = api_utils.get_person_uri(clipboard_text, st.session_state.current_page)
                        st.session_state.search_result = result
                    # st.rerun() 
                with col2:
                    st.write(f"{st.session_state.current_page} / {total_pages}")
                with col3:
                    if st.button("➡️") and st.session_state.current_page < total_pages:
                        st.session_state.current_page += 1
                        clipboard_text = pyperclip.paste()
                        result = api_utils.get_person_uri(clipboard_text, st.session_state.current_page)
                        st.session_state.search_result = result
                        #不刷新可能翻页有问题
                        # st.rerun() 

                # Display results for the current page
                for item in st.session_state.search_result['data']:
                    display_data = {
                        'fname': item.get('fname', ''),
                        'place': item.get('place', ''),
                        'uri': item.get('uri', ''),
                        'briefBiography': item.get('briefBiography', ''),
                        'start': item.get('start', ''),
                        'end': item.get('end', '')
                    }
                    
                    life_info = []
                    if display_data['start'] or display_data['end']:
                        life_span = f"{display_data['start'] or ''}{'-' if display_data['start'] and display_data['end'] else ''}{display_data['end'] or ''}"
                        life_info.append(life_span)
                    if display_data['place']:
                        life_info.append(display_data['place'])
                    life_info_str = " ".join(life_info)

                    markdown_str = f"""<div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; color: #DDDDDA">
        <strong>{display_data['fname']}</strong>"""

                    if life_info_str:
                        markdown_str += f" - {life_info_str}"

                    if display_data['uri']:
                        markdown_str += f"""
        <div style="margin-top: 10px; word-wrap: break-word;"><a href="{display_data['uri']}" target="_blank">{display_data['uri']}</a></div>"""

                    if display_data['briefBiography']:
                        markdown_str += f"""
        <div style="margin-top: 10px;"><span style="color: #D4D4D2;">{display_data['briefBiography']}</span></div>"""

                    markdown_str += "</div>"

                    st.markdown(markdown_str, unsafe_allow_html=True)
            elif st.session_state.search_result == "没有搜索到结果":
                st.write("没有搜索到结果")
            else:
                st.write("AI 结果:")
                st.write(st.session_state.search_result)

        if 'current_index' not in st.session_state:
            st.session_state.current_index = 0

        if 'flattened_data' not in st.session_state:
            st.error("未加载数据。请先前往数据加载页面加载数据。")
            return
        if 'settings' not in st.session_state:
            st.session_state.settings = load_settings()

    # 添加搜索功能
    search_query = st.text_input("", key="search_query", placeholder="请输入演出事件关键词")

    if search_query:
        search_results = search_data(search_query)
        if search_results:
            st.session_state.search_results = search_results
            display_search_results(search_results)
        else:
            st.session_state.search_results = None
            st.warning("未找到匹配的搜索结果。")
    else:
        st.session_state.search_results = None

    # 移动导航按钮到顶部
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        if st.button("⬅️ 上一条", key="prev_main"):
            navigate_data(-1)
            st.rerun()
    
    with col2:
        if 0 <= st.session_state.current_index < len(st.session_state.flattened_data):
            _, _, current_data = st.session_state.flattened_data[st.session_state.current_index]
            st.markdown(f"""<h3 style='text-align: center; color: #6FC1FF'>{current_data.get('name', '未指定')}</h3>""", unsafe_allow_html=True)
    
    with col3:
        if st.button("➡️ 下一条", key="next_main"):
            navigate_data(1)
            st.rerun()

    # 显示当前位置信息
    if 'search_results' in st.session_state and st.session_state.search_results:
        if st.session_state.current_index in st.session_state.search_results:
            current_position = st.session_state.search_results.index(st.session_state.current_index) + 1
            total_results = len(st.session_state.search_results)
            st.markdown(f"""<div style='text-align: center;'>搜索结果：第 {current_position} 条 / 共 {total_results} 条</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div style='text-align: center;'>当前项不在搜索结果中</div>""", unsafe_allow_html=True)
    else:
        data_index, sub_index, _ = st.session_state.flattened_data[st.session_state.current_index]
        st.markdown(f"""<div style='text-align: center;'>当前：第 {data_index + 1} 条数据第 {sub_index + 1} 个事件 / 共 {len(st.session_state.flattened_data)} 个事件</div>""", unsafe_allow_html=True)
    

    st.markdown("---")
    st.markdown(f"**数据 ID**: {current_data['id']}")
    # 显示表单
    display_form(st.session_state.current_index)
 
     # 修改保存和下载按钮的布局
    st.markdown("<br>", unsafe_allow_html=True)  # 添加一些垂直空间
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        col_left, col_right = st.columns(2)
        with col_left:
            if st.button("💾 保存更改", use_container_width=True):
                save_changes(st.session_state.current_index, st.session_state.flattened_data[st.session_state.current_index][2])
                st.success("更改已永久保存！")
        with col_right:
            json_data = json.dumps(st.session_state.data, ensure_ascii=False, indent=4)
            st.download_button(
                label="📥 下载JSON数据",
                data=json_data,
                file_name="modified_data.json",
                mime="application/json",
                use_container_width=True
            )
def display_search_results(search_results: List[int]):
    st.write(f"搜索结果：找到 {len(search_results)} 条记录")
    
    # 添加一些CSS样式
    st.markdown("""
    <style>
    .search-result-item {
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 5px;
        margin-bottom: 10px;
        background-color: #262730;
        transition: background-color 0.3s;
        cursor: pointer;
    }
    .search-result-item:hover {
        background-color: #1B1B1F;
    }
    .search-result-name {
        font-weight: bold;
        color: #1E90FF;
    }
    .search-result-info {
        color: #D6D6D6;
        font-size: 0.9em;
    }
    .custom-button {
        padding: 51px 50px 50px 50px; /* Adjust the padding values as needed */
    }
    </style>
    """, unsafe_allow_html=True)

    for result_idx in search_results:
        data_index, sub_index, current_data = st.session_state.flattened_data[result_idx]
        
        # 使用container来创建可点击的区域
        with st.container():
            col1, col2 = st.columns([9, 1])
            with col1:
                st.markdown(f"""
                <div class="search-result-item">
                    <div class="search-result-name">{current_data.get('name', '未指定')}</div>
                    <div class="search-result-info">时间: {current_data.get('time', '未指定')} | 地点: {current_data.get('location', {}).get('venue', '未指定')}</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button("查看", key=f"view_{result_idx}", help="查看详细信息", kwargs={"class": "custom-button"}):
                    st.session_state.current_index = result_idx
                    st.rerun()

    st.markdown("---")

def search_data(query: str) -> List[int]:
    """
    搜索匹配查询的数据，返回匹配项的索引列表
    """
    if not query:
        return []
    
    query = query.lower()
    results = []
    for idx, item in enumerate(st.session_state.flattened_data):
        if query in item[2].get('name', '').lower():
            results.append(idx)
    return results

def add_item_callback(key: str):
    st.session_state[key].insert(0, {"name": "", "role": "", "description": ""})
def delete_item_callback(key: str, idx: int):
    st.session_state[key].pop(idx)

def add_work_callback(key: str):
    st.session_state[key].insert(0, {
        "name": "",
        "description": "",
        "sectionsOrActs": "",
        "castDescription": {
            "description": "",
            "performanceResponsibilities": []
        }
    })

def add_responsibility_callback(work_key: str, work_idx: int):
    st.session_state[work_key][work_idx]['castDescription']['performanceResponsibilities'].insert(0, {
        "performerName": "",
        "responsibility": "",
        "characterName": ""
    })

def delete_responsibility_callback(work_key: str, work_idx: int, resp_idx: int):
    st.session_state[work_key][work_idx]['castDescription']['performanceResponsibilities'].pop(resp_idx)

def update_field(index, i, field, value, original_value=None):
    if original_value is not None:
        st.session_state[f'casts_{index}'][i][field] = original_value
    else:
        st.session_state[f'casts_{index}'][i][field] = value

# 可以直接复用的函数
def add_relatedTo_callback(key: str):
    st.session_state[key].insert(0, {"type": "", "uri": ""})

def delete_relatedTo_callback(key: str, idx: int):
    st.session_state[key].pop(idx)

def add_related_entity(key: str, entity_index: int):
    entity = st.session_state[key][entity_index]
    if 'relatedTo' not in entity:
        entity['relatedTo'] = []
    default_type = st.session_state.settings.get('groups_relationship', [{'label': '未指定'}])[0]['label']
    entity['relatedTo'].append({"type": default_type, "uri": ""})

def delete_entity_relatedTo(key: str, entity_index: int, relatedTo_index: int):
    st.session_state[key][entity_index]['relatedTo'].pop(relatedTo_index)

def delete_entity(key: str, entity_index: int):
    st.session_state[key].pop(entity_index)

def update_entities(index: int, entity_type: str):
    key = f'{entity_type}_{index}'
    if key in st.session_state:
        st.session_state.flattened_data[index][2][entity_type] = copy.deepcopy(st.session_state[key])
        st.success(f"{ENTITY_TYPE_NAMES[entity_type]}数据已更新，请点击【保存更改】按钮以永久保存。")
    else:
        st.error(f"没有找到要更新的{ENTITY_TYPE_NAMES[entity_type]}数据。")

def entity_on_change(entity_type: str):
    update_entities(st.session_state.current_index, entity_type)

def initialize_session_state(index: int, current_data: Dict[str, Any]):
    # Define all top-level keys that need initialization
    top_level_keys = [
        ('casts', 'performanceCasts', 'content'),
        ('involved_parties', 'involvedParties'),
        ('troupes', 'performingTroupes'),
        ('works', 'performanceWorks', 'content'),
        ('relatedTo', 'relatedTo'),
        ('location_relatedTo', 'location', 'relatedTo'),
        ('season_relatedTo', 'performingSeason', 'relatedTo'),
        ('season_location_relatedTo', 'performingSeason', 'location', 'relatedTo'),
        ('materials_relatedTo', 'hasMaterials', 'relatedTo')
    ]

    # Initialize top-level keys
    for session_key, *data_keys in top_level_keys:
        full_session_key = f'{session_key}_{index}'
        if full_session_key not in st.session_state:
            value = current_data
            for key in data_keys:
                value = value.get(key, {})
            st.session_state[full_session_key] = value if isinstance(value, list) else []

    # Ensure all related entity keys are initialized as lists
    for key in ['relatedTo', 'location_relatedTo', 'season_relatedTo', 'season_location_relatedTo', 'materials_relatedTo']:
        full_key = f'{key}_{index}'
        if not isinstance(st.session_state.get(full_key), list):
            st.session_state[full_key] = []

    # Initialize nested related entity keys
    nested_entities = [
        ('works', 'work'),
        ('involved_parties', 'party'),
        ('troupes', 'troupe'),
        ('casts', 'cast')
    ]

    for entity_list, entity_name in nested_entities:
        entity_list_key = f'{entity_list}_{index}'
        if entity_list_key not in st.session_state:
            entities = current_data.get(entity_list, [])
            # 确保每个实体都有 relatedTo 字段，并且是一个列表
            for entity in entities:
                if 'relatedTo' not in entity:
                    entity['relatedTo'] = []
                elif not isinstance(entity['relatedTo'], list):
                    entity['relatedTo'] = [entity['relatedTo']] if entity['relatedTo'] else []
            st.session_state[entity_list_key] = entities

    # 移除单独的 relatedTo session state 键的初始化
    # 因为现在 relatedTo 是每个实体对象的一个属性

    # 确保所有初始化的键都是列表（如果需要的话）
    for key in st.session_state:
        if key.endswith(('_works', '_involved_parties', '_troupes', '_casts')):
            if not isinstance(st.session_state[key], list):
                st.session_state[key] = []


ENTITY_TYPE_NAMES = {
    'involvedParties': '参与团体',
    'performingTroupes': '演出团体',
    'casts': '演职人员'
}

def render_entities(index, entity_type, entities, relationship_types):
    entity_name = ENTITY_TYPE_NAMES[entity_type]
    for i, entity in enumerate(entities):
        st.markdown(f"""
        <div style="display: flex; justify-content: center;">
            <div style="text-align: center; background-color: #FFC7D642; padding: 9px; border-radius: 20px; width: 600px;">
                <strong> >>> {entity_name} {i+1} <<< </strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        cols = st.columns([3, 3, 1])
        with cols[0]:
            entity['name'] = st.text_input("姓名" if entity_type == 'casts' else "名称", value=entity.get('name', ''), key=f"{entity_type}_name_{index}_{i}_{st.session_state.get('render_key', 0)}")
        with cols[1]:
            entity['role'] = st.text_input("角色", value=entity.get('role', ''), key=f"{entity_type}_role_{index}_{i}_{st.session_state.get('render_key', 0)}")
        with cols[2]:
            if st.button("🗑️", key=f"delete_{entity_type}_{index}_{i}_{st.session_state.get('render_key', 0)}"):
                delete_entity(f'{entity_type}_{index}', i)
                st.session_state['render_key'] = st.session_state.get('render_key', 0) + 1
                return True
        
        # 添加 description 字段
        entity['description'] = st.text_area("描述", value=entity.get('description', ''), key=f"{entity_type}_description_{index}_{i}_{st.session_state.get('render_key', 0)}")
        
        if render_related_entities(index, entity_type, i, entity, relationship_types):
            return True
        
        st.markdown("---")
    return False

def render_related_entities(index, entity_type, entity_index, entity, relationship_types):
    related_entity_name = "人员相关实体" if entity_type == 'casts' else "团体相关实体"
    st.markdown(f"**🤝 {related_entity_name}**")

    if 'relatedTo' not in entity:
        entity['relatedTo'] = []

    if st.button(f"➕ 添加{related_entity_name}", key=f"add_{entity_type}_relatedTo_{index}_{entity_index}_{st.session_state.get('render_key', 0)}"):
        add_related_entity(f'{entity_type}_{index}', entity_index)
        st.session_state['render_key'] = st.session_state.get('render_key', 0) + 1
        return True

    for j, relatedTo in enumerate(entity['relatedTo']):
        cols = st.columns([3, 3, 1])
        with cols[0]:
            current_type = relatedTo.get('type', '')
            type_index = relationship_types.index(current_type) if current_type in relationship_types else 0
            new_type = st.selectbox("类型", relationship_types, index=type_index, key=f"{entity_type}_relatedTo_type_{index}_{entity_index}_{j}_{st.session_state.get('render_key', 0)}")
        
        with cols[1]:
            new_uri = st.text_input("URI", value=relatedTo.get('uri', ''), key=f"{entity_type}_relatedTo_uri_{index}_{entity_index}_{j}_{st.session_state.get('render_key', 0)}")
        
        entity['relatedTo'][j] = {"type": new_type, "uri": new_uri}

        with cols[2]:
            if st.button("🗑️", key=f"delete_{entity_type}_relatedTo_{index}_{entity_index}_{j}_{st.session_state.get('render_key', 0)}"):
                delete_entity_relatedTo(f'{entity_type}_{index}', entity_index, j)
                st.session_state['render_key'] = st.session_state.get('render_key', 0) + 1
                return True
        st.markdown("---")
    return False


def display_entity_section(index, entity_type, current_data):
    entity_name = ENTITY_TYPE_NAMES[entity_type]
    relationship_type = 'persons_relationship' if entity_type == 'casts' else 'groups_relationship'
    relationship_types = [item['label'] for item in st.session_state.settings.get(relationship_type, [])]
    
    if not relationship_types:
        relationship_types = ['未指定']

    if f'{entity_type}_{index}' not in st.session_state:
        st.session_state[f'{entity_type}_{index}'] = copy.deepcopy(current_data.get(entity_type, []))

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button(f"➕ 添加{entity_name}", key=f"add_{entity_type}_{index}"):
            st.session_state[f'{entity_type}_{index}'].append({"name": "", "role": "", "description": "", "relatedTo": []})
    with col2:
        if st.button(f"🔄 更新{entity_name}", key=f"update_{entity_type}_{index}"):
            update_entities(index, entity_type)

    entities_container = st.empty()
    
    def render():
        with entities_container.container():
            if render_entities(index, entity_type, st.session_state[f'{entity_type}_{index}'], relationship_types):
                render()

    render()

def handle_related_entities(index, key, entity_type, relationship_types):
    st.markdown(f"**🤝 {entity_type}相关实体**")
    
    if f'{key}_{index}' not in st.session_state:
        st.session_state[f'{key}_{index}'] = []

    st.button(f"➕ 添加{entity_type}相关实体", key=f"add_{key}_{index}", on_click=add_relatedTo_callback, args=(f'{key}_{index}',))

    for i, relatedTo in enumerate(st.session_state[f'{key}_{index}']):
        st.markdown(f"---\n{entity_type}相关实体 {i+1}")
        cols = st.columns([3, 3, 1])
        with cols[0]:
            current_type = relatedTo.get('type', '')
            if current_type not in relationship_types:
                current_type = relationship_types[0]
            type_index = relationship_types.index(current_type)
            relatedTo['type'] = st.selectbox("类型", relationship_types, index=type_index, key=f"{key}_type_{index}_{i}")
        with cols[1]:
            relatedTo['uri'] = st.text_input("URI", value=relatedTo.get('uri', ''), key=f"{key}_uri_{index}_{i}")
        with cols[2]:
            st.button("🗑️", key=f"delete_{key}_{index}_{i}", on_click=delete_relatedTo_callback, args=(f'{key}_{index}', i))

    st.markdown("---")

#演出作品处理
def render_work_related_entities(index, work_index, work, relationship_types, render_key):
    st.markdown("**🤝 作品相关实体**")
    
    if 'relatedTo' not in work:
        work['relatedTo'] = []

    def add_work_related_entity():
        work['relatedTo'].append({"type": relationship_types[0], "uri": ""})

    st.button(f"➕ 添加作品相关实体", key=f"add_work_relatedTo_{index}_{work_index}_{render_key}", on_click=add_work_related_entity)

    for j, relatedTo in enumerate(work['relatedTo']):
        cols = st.columns([3, 3, 1])
        with cols[0]:
            current_type = relatedTo.get('type', '')
            type_index = relationship_types.index(current_type) if current_type in relationship_types else 0
            new_type = st.selectbox("类型", relationship_types, index=type_index, key=f"work_relatedTo_type_{index}_{work_index}_{j}_{render_key}")
        
        with cols[1]:
            new_uri = st.text_input("URI", value=relatedTo.get('uri', ''), key=f"work_relatedTo_uri_{index}_{work_index}_{j}_{render_key}")
        
        work['relatedTo'][j] = {"type": new_type, "uri": new_uri}

        with cols[2]:
            def delete_work_related_entity(j=j):
                work['relatedTo'].pop(j)

            st.button("🗑️", key=f"delete_work_relatedTo_{index}_{work_index}_{j}_{render_key}", on_click=delete_work_related_entity)

def render_performer_related_entities(index, work_index, performer_index, performer, relationship_types, render_key):
    st.markdown("**🤝 人员相关实体**")
    
    if 'relatedTo' not in performer:
        performer['relatedTo'] = []

    def add_performer_related_entity():
        performer['relatedTo'].append({"type": relationship_types[0], "uri": ""})

    st.button(f"➕ 添加人员相关实体", key=f"add_performer_relatedTo_{index}_{work_index}_{performer_index}_{render_key}", on_click=add_performer_related_entity)

    for j, relatedTo in enumerate(performer['relatedTo']):
        cols = st.columns([3, 3, 1])
        with cols[0]:
            current_type = relatedTo.get('type', '')
            type_index = relationship_types.index(current_type) if current_type in relationship_types else 0
            new_type = st.selectbox("类型", relationship_types, index=type_index, key=f"performer_relatedTo_type_{index}_{work_index}_{performer_index}_{j}_{render_key}")
        
        with cols[1]:
            new_uri = st.text_input("URI", value=relatedTo.get('uri', ''), key=f"performer_relatedTo_uri_{index}_{work_index}_{performer_index}_{j}_{render_key}")
        
        performer['relatedTo'][j] = {"type": new_type, "uri": new_uri}

        with cols[2]:
            def delete_performer_related_entity(j=j):
                performer['relatedTo'].pop(j)

            st.button("🗑️", key=f"delete_performer_relatedTo_{index}_{work_index}_{performer_index}_{j}_{render_key}", on_click=delete_performer_related_entity)

def render_works(index, works, work_relationship_types, person_relationship_types):
    render_key = st.session_state.get('render_key', 0)
    for i, work in enumerate(works):
        col1, col2 = st.columns([11, 1])
        with col1:
            work_expanded = st.checkbox(f"展开作品 {i+1}: {work.get('name', '')}", key=f"work_expanded_{index}_{i}_{render_key}")
        with col2:
            def delete_work(i=i):
                works.pop(i)

            st.button("🗑️", key=f"delete_work_{index}_{i}_{render_key}", on_click=delete_work)
        if work_expanded:
            work['name'] = st.text_input("名称", value=work.get('name', ''), key=f"work_name_{index}_{i}_{render_key}")
            work['description'] = st.text_area("描述", value=work.get('description', ''), key=f"work_description_{index}_{i}_{render_key}")
            work['sectionsOrActs'] = st.text_input("段落/幕", value=work.get('sectionsOrActs', ''), key=f"work_sections_{index}_{i}_{render_key}")
            
            render_work_related_entities(index, i, work, work_relationship_types, render_key)
            
            st.markdown("---")
            
            cast = work.get('castDescription', {}) if isinstance(work.get('castDescription'), dict) else {}
            cast['description'] = st.text_area("演员描述", value=cast.get('description', ''), key=f"work_cast_{index}_{i}_{render_key}")
            st.markdown("---")
            st.write("演出职责:")

            def add_performance_responsibility():
                if 'performanceResponsibilities' not in cast:
                    cast['performanceResponsibilities'] = []
                cast['performanceResponsibilities'].append({"performerName": "", "responsibility": "", "characterName": "", "relatedTo": []})

            st.button("➕ 添加演出职责", key=f"add_resp_{index}_{i}_{render_key}", on_click=add_performance_responsibility)
            
            for j, resp in enumerate(cast.get('performanceResponsibilities', [])):
                cols = st.columns([3, 3, 3, 1])
                with cols[0]:
                    resp['performerName'] = st.text_input("演员姓名", value=resp.get('performerName', ''), key=f"performer_name_{index}_{i}_{j}_{render_key}")
                with cols[1]:
                    resp['responsibility'] = st.text_input("职责", value=resp.get('responsibility', ''), key=f"performer_resp_{index}_{i}_{j}_{render_key}")
                with cols[2]:
                    resp['characterName'] = st.text_input("角色名称", value=resp.get('characterName', ''), key=f"performer_char_{index}_{i}_{j}_{render_key}")
                with cols[3]:
                    def delete_performance_responsibility(j=j):
                        cast['performanceResponsibilities'].pop(j)

                    st.button("🗑️", key=f"delete_resp_{index}_{i}_{j}_{render_key}", on_click=delete_performance_responsibility)
                
                render_performer_related_entities(index, i, j, resp, person_relationship_types, render_key)
                
                st.markdown("---")
            
            work['castDescription'] = cast
        st.markdown("---")



def display_works_section(index, current_data):
    work_relationship_types = [item['label'] for item in st.session_state.settings.get('works_relationship', [])]
    person_relationship_types = [item['label'] for item in st.session_state.settings.get('persons_relationship', [])]
    
    if not work_relationship_types:
        work_relationship_types = ['未指定']
    if not person_relationship_types:
        person_relationship_types = ['未指定']

    if f'works_{index}' not in st.session_state:
        st.session_state[f'works_{index}'] = copy.deepcopy(current_data.get('works', []))

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("➕ 添加演出作品", key=f"add_work_{index}"):
            st.session_state[f'works_{index}'].append({"name": "", "description": "", "sectionsOrActs": "", "relatedTo": [], "castDescription": {"description": "", "performanceResponsibilities": []}})
    with col2:
        if st.button("🔄 更新演出作品", key=f"update_works_{index}"):
            update_works(index)

    works_container = st.empty()
    
    def render():
        with works_container.container():
            if render_works(index, st.session_state[f'works_{index}'], work_relationship_types, person_relationship_types):
                render()

    render()

def update_works(index: int):
    if f'works_{index}' in st.session_state:
        st.session_state.flattened_data[index][2]['works'] = copy.deepcopy(st.session_state[f'works_{index}'])
        st.success("演出作品数据已更新，请点击【保存更改】按钮以永久保存。")
    else:
        st.error("没有找到要更新的演出作品数据。")

def display_form(index: int):
    # 检查 flattened_data 是否存在
    if 'flattened_data' not in st.session_state:
        st.error("数据未正确加载，请刷新页面。")
        return

    # 检查索引是否有效
    if 0 <= index < len(st.session_state.flattened_data):
        data_index, sub_index, current_data = st.session_state.flattened_data[index]
        initialize_session_state(index, current_data)
    else:
        st.error("无效的数据索引。")
        return
    # 基本信息
    with st.expander("📌 演出事件", expanded=False):
        st.text_input("名称", value=current_data.get('name', ''), key=f"name_{index}")
        st.text_input("时间", value=current_data.get('time', ''), key=f"time_{index}")
        st.text_area("描述", value=current_data.get('description', ''), key=f"description_{index}")
    
        # Filter out deleted event types
        event_types = [et['label'] for et in st.session_state.settings["EVENT_TYPES"] if not et.get('deleted', False)]
        current_event_type = current_data.get('eventType', {}).get('type', '')
        event_type_index = event_types.index(current_event_type) if current_event_type in event_types else 0
        selected_event_type = st.selectbox("活动类型", event_types, index=event_type_index, key=f"event_type_{index}")
        
        relationship_types = [item['label'] for item in st.session_state.settings.get('events_relationship', [])]
        handle_related_entities(index, 'relatedTo', '演出事件', relationship_types)

        st.markdown("---")

    # 地点
    with st.expander("📍 演出场地", expanded=False):
        location = current_data.get('location', {})
        st.text_input("场地", value=location.get('venue', ''), key=f"venue_{index}")
        st.text_area("描述", value=location.get('description', ''), key=f"location_description_{index}")
        st.text_input("地址", value=location.get('address', ''), key=f"address_{index}")
        
        # 从数据库获取 architectures_relationship 词表
        architecture_relationship_types = [item['label'] for item in st.session_state.settings.get('architectures_relationship', [])]
        handle_related_entities(index, 'location_relatedTo', '场地', architecture_relationship_types)


    # 相关方
    with st.expander("👥 参与团体", expanded=False):
        display_entity_section(index, 'involvedParties', current_data)

    # 演出团体
    with st.expander("🎭 演出团体", expanded=False):
        display_entity_section(index, 'performingTroupes', current_data)
    
    # 演出作品
    with st.expander("🎬 演出作品", expanded=False):
        display_works_section(index, current_data)
    # 演出阵容
    with st.expander("👨‍👩‍👧‍👦 演职人员", expanded=False):
        display_entity_section(index, 'casts', current_data)

    # 演出季
    with st.expander("🗓️ 演出季", expanded=False):
        season = current_data.get('performingSeason', {})
        st.text_input("名称", value=season.get('name', ''), key=f"season_name_{index}")
        
        # 修改为使用事件类型
        event_types = [et['label'] for et in st.session_state.settings["EVENT_TYPES"] if not et.get('deleted', False)]
        current_season_type = season.get('type', '')
        season_type_index = event_types.index(current_season_type) if current_season_type in event_types else 0
        selected_season_type = st.selectbox("类型", event_types, index=season_type_index, key=f"season_type_{index}")
        
        st.text_input("时间", value=season.get('time', ''), key=f"season_time_{index}")
        # Add button to add new relatedTo
        
        relationship_types = [item['label'] for item in st.session_state.settings.get('events_relationship', [])]
        handle_related_entities(index, 'season_relatedTo', '演出季', relationship_types)


        season_location = season.get('location', {})
        st.markdown("**📍 演出季地点信息**")
        st.text_input("场地", value=season_location.get('venue', ''), key=f"season_venue_{index}")
        st.text_area("描述", value=season_location.get('description', ''), key=f"season_location_description_{index}")
        st.text_input("地址", value=season_location.get('address', ''), key=f"season_address_{index}")
        
        # 从数据库获取 architectures_relationship 词表
        architecture_relationship_types = [item['label'] for item in st.session_state.settings.get('architectures_relationship', [])]
        handle_related_entities(index, 'season_location_relatedTo', '演出季场地', architecture_relationship_types)

    # 相关材料
    with st.expander("📎 相关材料", expanded=False):
        has_materials = current_data.get('hasMaterials', {})
        
        # Filter out deleted material types
        material_types = [mt['label'] for mt in st.session_state.settings["MATERIAL_TYPES"] if not mt.get('deleted', False)]
        current_material_type = has_materials.get('type', '')
        material_type_index = material_types.index(current_material_type) if current_material_type in material_types else 0
        selected_material_type = st.selectbox("材料类型", material_types, index=material_type_index, key=f"materials_type_{index}")
        
        st.text_input("材料链接ID", value=has_materials.get('linkID', ''), key=f"materials_linkID_{index}")
        
        # 从数据库获取 materials_relationship 词表
        material_relationship_types = [item['label'] for item in st.session_state.settings.get('materials_relationship', [])]
        handle_related_entities(index, 'materials_relatedTo', '材料', material_relationship_types)


def navigate_data(direction: int):
    if 'search_results' in st.session_state and st.session_state.search_results:
        current_result_index = st.session_state.search_results.index(st.session_state.current_index)
        new_result_index = (current_result_index + direction) % len(st.session_state.search_results)
        st.session_state.current_index = st.session_state.search_results[new_result_index]
    else:
        st.session_state.current_index = (st.session_state.current_index + direction) % len(st.session_state.flattened_data)


def save_changes(index, current_data):
    # Ensure 'id' field is initialized
    current_data['id'] = st.session_state.get(f"id_{index}", current_data.get('id', ""))

    if not current_data['id']:
        st.error("Data ID missing, cannot save to database!")
        return

    # Update current_data with session state values
    current_data['name'] = st.session_state.get(f"name_{index}", "")
    current_data['time'] = st.session_state.get(f"time_{index}", "")
    current_data['description'] = st.session_state.get(f"description_{index}", "")
    current_data['relatedTo'] = st.session_state.get(f'relatedTo_{index}', [])
    
    # Update eventType
    if 'eventType' not in current_data:
        current_data['eventType'] = {}
    current_data['eventType']['type'] = st.session_state.get(f"event_type_{index}", "")
    
    # Update location information
    if 'location' not in current_data:
        current_data['location'] = {}
    current_data['location']['venue'] = st.session_state.get(f"venue_{index}", "")
    current_data['location']['description'] = st.session_state.get(f"location_description_{index}", "")
    current_data['location']['address'] = st.session_state.get(f"address_{index}", "")
    current_data['location']['relatedTo'] = st.session_state.get(f"location_relatedTo_{index}", [])
      
    # 更新相关方、演出团体
    for entity_type in ['involvedParties', 'performingTroupes']:
        if f'{entity_type}_{index}' in st.session_state:
            current_data[entity_type] = copy.deepcopy(st.session_state[f'{entity_type}_{index}'])
   
    # 更新演出作品
    if 'performanceWorks' not in current_data:
        current_data['performanceWorks'] = {'content': []}
    current_data['performanceWorks']['content'] = st.session_state[f'works_{index}']
    
    # 更新演出阵容
    if 'performanceCasts' not in current_data:
        current_data['performanceCasts'] = {'content': []}
    current_data['performanceCasts']['content'] = st.session_state[f'casts_{index}']

    # 更新新增字段
    if 'hasMaterials' not in current_data:
        current_data['hasMaterials'] = {}
    current_data['hasMaterials']['type'] = st.session_state.get(f"materials_type_{index}", "")
    current_data['hasMaterials']['linkID'] = st.session_state.get(f"materials_linkID_{index}", "")
    current_data['hasMaterials']['relatedTo'] = st.session_state.get(f"materials_relatedTo_{index}", [])  # 材料的 relatedTo

    # 更新演出季信息
    if 'performingSeason' not in current_data:
        current_data['performingSeason'] = {}
    current_data['performingSeason']['name'] = st.session_state.get(f"season_name_{index}", "")
    current_data['performingSeason']['type'] = st.session_state.get(f"season_type_{index}", "")
    current_data['performingSeason']['time'] = st.session_state.get(f"season_time_{index}", "")
    current_data['performingSeason']['relatedTo'] = st.session_state.get(f"season_relatedTo_{index}", [])  # 演出季的 relatedTo

    if 'location' not in current_data['performingSeason']:
        current_data['performingSeason']['location'] = {}
    current_data['performingSeason']['location']['venue'] = st.session_state.get(f"season_venue_{index}", "")
    current_data['performingSeason']['location']['description'] = st.session_state.get(f"season_location_description_{index}", "")
    current_data['performingSeason']['location']['address'] = st.session_state.get(f"season_address_{index}", "")
    current_data['performingSeason']['location']['relatedTo'] = st.session_state.get(f"season_location_relatedTo_{index}", [])  # 演出季地点的 relatedTo

    # Display data ID
    # st.info(f"Saving changes for Data ID: {current_data['id']}")

    # 更新会话状态数据
    data_index, sub_index, _ = st.session_state.flattened_data[index]
    st.session_state.data[data_index]['performingEvent'] = current_data
    
    # 保存到数据库
    db_path = 'E:\\scripts\\jiemudan\\2\\output\\database\\database.db'
    data_id = current_data['id']
    
    # 更新 main_table 和 version_history
    save_to_db(db_path, st.session_state.data[data_index], data_id)
    
    st.success("数据已成功保存到数据库！")