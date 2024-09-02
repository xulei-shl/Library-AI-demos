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
        st.session_state.show_prompts = False
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
        <h2>🔗 实体 API</h4>
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
    search_query = st.text_input("", key="search_query", placeholder="请输入搜索演出事件关键词")

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
                st.success("更改已保存！")
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

def add_relatedTo_callback(key: str):
    st.session_state[key].insert(0, {"type": "", "type": ""})
def delete_relatedTo_callback(key: str, idx: int):
    st.session_state[key].pop(idx)

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
            st.session_state[entity_list_key] = current_data.get(entity_list, [])
        for i, _ in enumerate(st.session_state[entity_list_key]):
            related_key = f'{entity_name}_relatedTo_{index}_{i}'
            if related_key not in st.session_state:
                st.session_state[related_key] = []

    # Initialize performer related keys
    works_key = f'works_{index}'
    if works_key in st.session_state:
        for i, work in enumerate(st.session_state[works_key]):
            cast = work.get('castDescription', {})
            if isinstance(cast, dict):
                responsibilities = cast.get('performanceResponsibilities', [])
            elif isinstance(cast, list):
                responsibilities = cast
            else:
                responsibilities = [cast] if cast else []

            for j, _ in enumerate(responsibilities):
                performer_key = f'performer_relatedTo_{index}_{i}_{j}'
                if performer_key not in st.session_state:
                    st.session_state[performer_key] = []

    # Ensure all initialized keys are lists
    for key in st.session_state:
        if key.startswith(('work_relatedTo_', 'party_relatedTo_', 'troupe_relatedTo_', 'cast_relatedTo_', 'performer_relatedTo_')):
            if not isinstance(st.session_state[key], list):
                st.session_state[key] = []

def display_form(index: int):
    if 0 <= index < len(st.session_state.flattened_data):
        data_index, sub_index, current_data = st.session_state.flattened_data[index]
        initialize_session_state(index, current_data)
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
        

        st.markdown("**🤝 演出事件相关实体**")
        relationship_types = [item['label'] for item in st.session_state.settings.get('events_relationship', [])]
        if not relationship_types:
            relationship_types = ['未指定']

        if 'relatedTo' not in st.session_state:
            st.session_state['relatedTo'] = []

        if st.button("➕ 添加相关实体", key=f"add_relatedTo_main"):
            add_relatedTo_callback('relatedTo')
            st.rerun()  # Rerun the app to reflect the changes immediately

        for i, relatedTo in enumerate(st.session_state['relatedTo']):
            st.markdown(f"---\n相关实体 {i+1}")
            cols = st.columns([3, 3, 1])
            with cols[0]:
                current_type = relatedTo.get('type', '')
                if current_type not in relationship_types:
                    current_type = relationship_types[0]
                type_index = relationship_types.index(current_type)
                relatedTo['type'] = st.selectbox("类型", relationship_types, index=type_index, key=f"relatedTo_type_main_{i}")
            with cols[1]:
                relatedTo['uri'] = st.text_input("URI", value=relatedTo.get('uri', ''), key=f"relatedTo_uri_main_{i}")
            with cols[2]:
                if st.button("🗑️", key=f"delete_relatedTo_main_{i}"):
                    delete_relatedTo_callback('relatedTo', i)
                    st.rerun()  # Rerun the app to reflect the changes immediately

        st.markdown("---")

    # 地点
    with st.expander("📍 演出场地", expanded=False):
        location = current_data.get('location', {})
        st.text_input("场地", value=location.get('venue', ''), key=f"venue_{index}")
        st.text_area("描述", value=location.get('description', ''), key=f"location_description_{index}")
        st.text_input("地址", value=location.get('address', ''), key=f"address_{index}")
        # Add button to add new relatedTo
        st.markdown("**🤝 场地相关实体**")
        if st.button("➕ 添加相关实体", key=f"add_location_relatedTo_{index}"):
            add_relatedTo_callback(f'location_relatedTo_{index}')
            st.rerun()

        for i, relatedTo in enumerate(st.session_state.get(f'location_relatedTo_{index}', [])):
            st.markdown(f"---\n相关实体 {i+1}")
            cols = st.columns([3, 3, 1])
            with cols[0]:
                relatedTo['type'] = st.text_input("类型", value=relatedTo.get('type', ''), key=f"location_relatedTo_type_{index}_{i}")
            with cols[1]:
                relatedTo['uri'] = st.text_input("URI", value=relatedTo.get('uri', ''), key=f"location_relatedTo_uri_{index}_{i}")
            with cols[2]:
                if st.button("🗑️", key=f"delete_location_relatedTo_{index}_{i}"):
                    delete_relatedTo_callback(f'location_relatedTo_{index}', i)
            st.markdown("---")

        st.markdown("---")

    # 相关方
    with st.expander("👥 参与团体", expanded=False):
        st.button("➕ ", key=f"add_party_{index}", on_click=add_item_callback, args=(f'involved_parties_{index}',))
        for i, party in enumerate(st.session_state[f'involved_parties_{index}']):
            st.markdown(f"##### 参与团体 {i+1}")
            cols = st.columns([3, 3, 1])
            with cols[0]:
                party['name'] = st.text_input("名称", value=party.get('name', ''), key=f"party_name_{index}_{i}")
            with cols[1]:
                party['role'] = st.text_input("角色", value=party.get('role', ''), key=f"party_role_{index}_{i}")
            with cols[2]:
                st.button("🗑️", key=f"delete_party_{index}_{i}", on_click=delete_item_callback, args=(f'involved_parties_{index}', i))
            # Add button to add new relatedTo
            st.markdown("**🤝 团体相关实体**")
            if st.button("➕ 添加相关实体", key=f"add_party_relatedTo_{index}_{i}"):
                add_relatedTo_callback(f'party_relatedTo_{index}_{i}')

            for j, relatedTo in enumerate(st.session_state.get(f'party_relatedTo_{index}_{i}', [])):
                unique_id = str(uuid.uuid4())  # Generate a unique identifier
                st.markdown(f"---\n相关实体 {j+1}")
                cols = st.columns([3, 3, 1])
                with cols[0]:
                    relatedTo['type'] = st.text_input("类型", value=relatedTo.get('type', ''), key=f"party_relatedTo_type_{index}_{i}_{j}_{unique_id}")
                with cols[1]:
                    relatedTo['uri'] = st.text_input("URI", value=relatedTo.get('uri', ''), key=f"party_relatedTo_uri_{index}_{i}_{j}_{unique_id}")
                with cols[2]:
                    if st.button("🗑️", key=f"delete_party_relatedTo_{index}_{i}_{j}_{unique_id}"):
                        delete_relatedTo_callback(f'party_relatedTo_{index}_{i}', j)
                        st.rerun()  # 重新运行以更新显示
            st.markdown("---")


    # 演出团体
    with st.expander("🎭 演出团体", expanded=False):
        st.button("➕ ", key=f"add_troupe_{index}", on_click=add_item_callback, args=(f'troupes_{index}',))
        for i, troupe in enumerate(st.session_state[f'troupes_{index}']):
            cols = st.columns([3, 3, 1])
            with cols[0]:
                troupe['name'] = st.text_input("名称", value=troupe.get('name', ''), key=f"troupe_name_{index}_{i}")
            with cols[1]:
                troupe['role'] = st.text_input("角色", value=troupe.get('role', ''), key=f"troupe_role_{index}_{i}")
            with cols[2]:
                st.button("🗑️", key=f"delete_troupe_{index}_{i}", on_click=delete_item_callback, args=(f'troupes_{index}', i))
            # Add button to add new relatedTo
            st.markdown("**🤝 团体相关实体**")
            st.markdown("---")
    
    # 演出作品
    with st.expander("🎬 演出作品", expanded=False):
        st.button("➕ ", key=f"add_work_{index}", on_click=add_work_callback, args=(f'works_{index}',))
        for i, work in enumerate(st.session_state[f'works_{index}']):
            col1, col2 = st.columns([11, 1])
            with col1:
                work_expanded = st.checkbox(f"展开作品 {i+1}: {work.get('name', '')}", key=f"work_expanded_{index}_{i}")
            with col2:
                st.button("🗑️", key=f"delete_work_{index}_{i}", on_click=delete_item_callback, args=(f'works_{index}', i))
            if work_expanded:
                work['name'] = st.text_input("名称", value=work.get('name', ''), key=f"work_name_{index}_{i}")
                work['description'] = st.text_area("描述", value=work.get('description', ''), key=f"work_description_{index}_{i}")
                work['sectionsOrActs'] = st.text_input("段落/幕", value=work.get('sectionsOrActs', ''), key=f"work_sections_{index}_{i}")
                # Add button to add new relatedTo
                st.markdown("**🤝 作品相关实体**")
                st.markdown("---")
                
                cast = work.get('castDescription', {}) if isinstance(work.get('castDescription'), dict) else {}
                cast['description'] = st.text_area("演员描述", value=cast.get('description', ''), key=f"work_cast_{index}_{i}")
                st.markdown("---")
                st.write("演出职责:")
                st.button("➕ ", key=f"add_resp_{index}_{i}", on_click=add_responsibility_callback, args=(f'works_{index}', i))
                for j, resp in enumerate(cast.get('performanceResponsibilities', [])):
                    cols = st.columns([3, 3, 3])
                    with cols[0]:
                        resp['performerName'] = st.text_input("演员姓名", value=resp.get('performerName', ''), key=f"performer_name_{index}_{i}_{j}")
                    with cols[1]:
                        resp['responsibility'] = st.text_input("职责", value=resp.get('responsibility', ''), key=f"performer_resp_{index}_{i}_{j}")
                    with cols[2]:
                        resp['characterName'] = st.text_input("角色名称", value=resp.get('characterName', ''), key=f"performer_char_{index}_{i}_{j}")
                    cols2 = st.columns([3, 1])
                    with cols2[0]:
                        # Add button to add new relatedTo
                        st.markdown("**🤝 人员相关实体**")
                    st.markdown("---")
            st.markdown("---")
    # 演出阵容
    with st.expander("👨‍👩‍👧‍👦 演职人员", expanded=False):
        st.button("➕ ", key=f"add_cast_{index}", on_click=add_item_callback, args=(f'casts_{index}',))
        for i, cast in enumerate(st.session_state[f'casts_{index}']):
            cols = st.columns([3, 3, 1])
            with cols[0]:
                cast['name'] = st.text_input("姓名", value=cast.get('name', ''), key=f"cast_name_{index}_{i}")
            with cols[1]:
                cast['role'] = st.text_input("角色", value=cast.get('role', ''), key=f"cast_role_{index}_{i}")
            with cols[2]:
                st.button("🗑️", key=f"delete_cast_{index}_{i}", on_click=delete_item_callback, args=(f'casts_{index}', i))
            # Add button to add new relatedTo
            st.markdown("**🤝 人员相关实体**")

            st.markdown("---")

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
        st.markdown("**🤝 演出相关实体**")
        st.markdown("---")

        season_location = season.get('location', {})
        st.markdown("**📍 演出季地点信息**")
        st.text_input("场地", value=season_location.get('venue', ''), key=f"season_venue_{index}")
        st.text_area("描述", value=season_location.get('description', ''), key=f"season_location_description_{index}")
        st.text_input("地址", value=season_location.get('address', ''), key=f"season_address_{index}")
        # Add button to add new relatedTo
        st.markdown("**🤝 场地相关实体**")


    with st.expander("📎 相关材料", expanded=False):
        has_materials = current_data.get('hasMaterials', {})
        
        # Filter out deleted material types
        material_types = [mt['label'] for mt in st.session_state.settings["MATERIAL_TYPES"] if not mt.get('deleted', False)]
        current_material_type = has_materials.get('type', '')
        material_type_index = material_types.index(current_material_type) if current_material_type in material_types else 0
        selected_material_type = st.selectbox("材料类型", material_types, index=material_type_index, key=f"materials_type_{index}")
        
        st.text_input("材料链接ID", value=has_materials.get('linkID', ''), key=f"materials_linkID_{index}")
        # Add button to add new relatedTo
        st.markdown("**🤝 材料相关实体**")

        st.markdown("---")

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

    # 更新 current_data 中的值
    current_data['name'] = st.session_state.get(f"name_{index}", "")
    current_data['time'] = st.session_state.get(f"time_{index}", "")
    current_data['description'] = st.session_state.get(f"description_{index}", "")
    current_data['relatedTo'] = st.session_state.get(f"relatedTo_{index}", [])  # 主节点的 relatedTo
    
    # 更新 eventType
    if 'eventType' not in current_data:
        current_data['eventType'] = {}
    current_data['eventType']['type'] = st.session_state.get(f"event_type_{index}", "")
    
    # 更新地点信息
    if 'location' not in current_data:
        current_data['location'] = {}
    current_data['location']['venue'] = st.session_state.get(f"venue_{index}", "")
    current_data['location']['description'] = st.session_state.get(f"location_description_{index}", "")
    current_data['location']['address'] = st.session_state.get(f"address_{index}", "")
    current_data['location']['relatedTo'] = st.session_state.get(f"location_relatedTo_{index}", [])  # 地点的 relatedTo
    
    # 更新相关方
    current_data['involvedParties'] = st.session_state[f'involved_parties_{index}']
    
    # 更新演出团体
    current_data['performingTroupes'] = st.session_state[f'troupes_{index}']
    
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

    # Update session state data
    data_index, sub_index, _ = st.session_state.flattened_data[index]
    st.session_state.data[data_index]['performingEvent'] = current_data
    
    # Save to database
    db_path = 'E:\\scripts\\jiemudan\\2\\output\\database\\database.db'
    data_id = current_data['id']
    # st.success("\n--------------------------------\n")
    # st.success(data_id)
    
    # Update main_table and version_history
    save_to_db(db_path, st.session_state.data[data_index], data_id)
    
    st.success("数据已成功保存到数据库！")