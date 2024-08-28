import streamlit as st
import json
from utils import save_to_indexeddb, load_from_indexeddb
from typing import Any, Dict, List
from api_utils import call_api



def browse_data_page():
    st.title("数据浏览")

    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0

    if 'flattened_data' not in st.session_state:
        load_from_indexeddb()

        # 处理嵌套的列表结构
        if isinstance(st.session_state.data, list):
            flattened_data = []
            for i, item in enumerate(st.session_state.data):
                if isinstance(item, dict) and 'performingEvent' in item:
                    flattened_data.append((i, 0, item['performingEvent']))
                elif isinstance(item, list):
                    for j, sub_item in enumerate(item):
                        if isinstance(sub_item, dict) and 'performingEvent' in sub_item:
                            flattened_data.append((i, j, sub_item['performingEvent']))
            st.session_state.flattened_data = flattened_data
        else:
            st.error("Unexpected data format. Expected a list of dictionaries or lists.")
            return

    if not st.session_state.flattened_data:
        st.warning("未找到数据。请先上传 JSON 文件并加载数据。")
        return

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

    # 显示表单
    display_form(st.session_state.current_index)

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
                    st.experimental_rerun()

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

def initialize_session_state(index: int, current_data: Dict[str, Any]):
    if f'casts_{index}' not in st.session_state:
        st.session_state[f'casts_{index}'] = current_data.get('performanceCasts', {}).get('content', [])
    if f'involved_parties_{index}' not in st.session_state:
        st.session_state[f'involved_parties_{index}'] = current_data.get('involvedParties', [])
    if f'troupes_{index}' not in st.session_state:
        st.session_state[f'troupes_{index}'] = current_data.get('performingTroupes', [])
    if f'works_{index}' not in st.session_state:
        st.session_state[f'works_{index}'] = current_data.get('performanceWorks', {}).get('content', [])

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

def update_field(index, i, field, value):
    st.session_state[f'casts_{index}'][i][field] = value

def display_form(index: int):
    if 0 <= index < len(st.session_state.flattened_data):
        data_index, sub_index, current_data = st.session_state.flattened_data[index]

        initialize_session_state(index, current_data)

        st.markdown(f"""<h3 style='text-align: center; color: #6FC1FF'>{current_data.get('name', '未指定')}</h3>""", unsafe_allow_html=True)
        
        # 更新显示逻辑以反映搜索结果中的位置
        if 'search_results' in st.session_state and st.session_state.search_results:
            current_position = st.session_state.search_results.index(index) + 1
            total_results = len(st.session_state.search_results)
            st.markdown(f"""<div style='text-align: center;'>搜索结果：第 {current_position} 条 / 共 {total_results} 条</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div style='text-align: center;'>当前：第 {data_index + 1} 条数据第 {sub_index + 1} 个事件 / 共 {len(st.session_state.flattened_data)} 个事件</div>""", unsafe_allow_html=True)
        
        st.markdown("---")


        # 基本信息
        with st.expander("📌 演出事件", expanded=False):
            st.text_input("名称", value=current_data.get('name', ''), key=f"name_{index}")
            st.text_input("时间", value=current_data.get('time', ''), key=f"time_{index}")
            st.text_area("描述", value=current_data.get('description', ''), key=f"description_{index}")
            st.text_input("活动类型", value=current_data.get('eventType', {}).get('type', ''), key=f"event_type_{index}")

        # 地点
        with st.expander("📍 演出地点", expanded=False):
            location = current_data.get('location', {})
            st.text_input("场地", value=location.get('venue', ''), key=f"venue_{index}")
            st.text_area("描述", value=location.get('description', ''), key=f"location_description_{index}")
            st.text_input("地址", value=location.get('address', ''), key=f"address_{index}")

        # 相关方
        with st.expander("👥 参与团体", expanded=False):
            st.button("➕ 新增", key=f"add_party_{index}", on_click=add_item_callback, args=(f'involved_parties_{index}',))
            for i, party in enumerate(st.session_state[f'involved_parties_{index}']):
                cols = st.columns([3, 3, 1])
                with cols[0]:
                    party['name'] = st.text_input("名称", value=party.get('name', ''), key=f"party_name_{index}_{i}")
                with cols[1]:
                    party['role'] = st.text_input("角色", value=party.get('role', ''), key=f"party_role_{index}_{i}")
                with cols[2]:
                    st.button("🗑️", key=f"delete_party_{index}_{i}", on_click=delete_item_callback, args=(f'involved_parties_{index}', i))
                party['description'] = st.text_area("描述", value=party.get('description', ''), key=f"party_description_{index}_{i}")

        # 演出团体
        with st.expander("🎭 演出团体", expanded=False):
            st.button("➕ 新增", key=f"add_troupe_{index}", on_click=add_item_callback, args=(f'troupes_{index}',))
            for i, troupe in enumerate(st.session_state[f'troupes_{index}']):
                cols = st.columns([3, 3, 1])
                with cols[0]:
                    troupe['name'] = st.text_input("名称", value=troupe.get('name', ''), key=f"troupe_name_{index}_{i}")
                with cols[1]:
                    troupe['role'] = st.text_input("角色", value=troupe.get('role', ''), key=f"troupe_role_{index}_{i}")
                with cols[2]:
                    st.button("🗑️", key=f"delete_troupe_{index}_{i}", on_click=delete_item_callback, args=(f'troupes_{index}', i))
                troupe['description'] = st.text_area("描述", value=troupe.get('description', ''), key=f"troupe_description_{index}_{i}")

        # 演出作品
        with st.expander("🎬 演出作品", expanded=False):
            st.button("➕ 新增", key=f"add_work_{index}", on_click=add_work_callback, args=(f'works_{index}',))
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
                    
                    cast = work.get('castDescription', {}) if isinstance(work.get('castDescription'), dict) else {}
                    cast['description'] = st.text_area("演员描述", value=cast.get('description', ''), key=f"work_cast_{index}_{i}")
                    
                    st.write("演出职责:")
                    st.button("➕ 新增", key=f"add_resp_{index}_{i}", on_click=add_responsibility_callback, args=(f'works_{index}', i))
                    for j, resp in enumerate(cast.get('performanceResponsibilities', [])):
                        cols = st.columns([3, 3, 3, 1])
                        with cols[0]:
                            resp['performerName'] = st.text_input("演员姓名", value=resp.get('performerName', ''), key=f"performer_name_{index}_{i}_{j}")
                        with cols[1]:
                            resp['responsibility'] = st.text_input("职责", value=resp.get('responsibility', ''), key=f"performer_resp_{index}_{i}_{j}")
                        with cols[2]:
                            resp['characterName'] = st.text_input("角色名称", value=resp.get('characterName', ''), key=f"performer_char_{index}_{i}_{j}")
                        with cols[3]:
                            st.button("🗑️", key=f"delete_resp_{index}_{i}_{j}", on_click=delete_responsibility_callback, args=(f'works_{index}', i, j))
                st.markdown("---")

        # 演出阵容
        with st.expander("👨‍👩‍👧‍👦 演职人员", expanded=False):
            st.button("➕ 新增", key=f"add_cast_{index}", on_click=add_item_callback, args=(f'casts_{index}',))
            for i, cast in enumerate(st.session_state[f'casts_{index}']):
                cols = st.columns([3, 1, 3, 3, 1])
                
                name_key = f"cast_name_{index}_{i}"
                # 检查是否有来自 API 的新值
                if f"{name_key}_api_result" in st.session_state:
                    cast['name'] = st.session_state[f"{name_key}_api_result"]
                    del st.session_state[f"{name_key}_api_result"]                

                with cols[0]:
                    cast['name'] = st.text_input("姓名", value=cast.get('name', ''), key=f"cast_name_{index}_{i}")
                with cols[1]:
                    if st.button("🔍", key=f"api_name_{index}_{i}"):
                        result = call_api(cast['name'])
                        if result:
                            st.session_state[f"{name_key}_api_result"] = result
                with cols[2]:
                    cast['role'] = st.text_input("角色", value=cast.get('role', ''), key=f"cast_role_{index}_{i}")
                with cols[3]:
                    cast['description'] = st.text_input("描述", value=cast.get('description', ''), key=f"cast_description_{index}_{i}")
                with cols[4]:
                    st.button("🗑️", key=f"delete_cast_{index}_{i}", on_click=delete_item_callback, args=(f'casts_{index}', i))

                # API 结果显示在下一行
                if f"{name_key}_api_result" in st.session_state:
                    #st.write("姓名 API 结果:")
                    st.write(st.session_state[f"{name_key}_api_result"])
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("应用", key=f"apply_name_{index}_{i}"):
                            update_field(index, i, 'name', st.session_state[f"{name_key}_api_result"])
                            del st.session_state[f"{name_key}_api_result"]
                    with col2:
                        if st.button("舍弃", key=f"discard_name_{index}_{i}"):
                            del st.session_state[f"{name_key}_api_result"]                

        # 修改导航和保存按钮的布局
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("⬅️ 上一条"):
                navigate_data(-1)
                st.experimental_rerun()
        with col2:
            if st.button("💾 保存更改"):
                save_changes(index, current_data)
                st.success("更改已保存！")            
        with col3:
            json_data = json.dumps(st.session_state.data, ensure_ascii=False, indent=4)
            st.download_button(
                label="📥 下载JSON数据",
                data=json_data,
                file_name="modified_data.json",
                mime="application/json"
            )          
        with col4:
            if st.button("➡️ 下一条"):
                navigate_data(1)
                st.experimental_rerun()


def navigate_data(direction: int):
    if 'search_results' in st.session_state and st.session_state.search_results:
        current_result_index = st.session_state.search_results.index(st.session_state.current_index)
        new_result_index = (current_result_index + direction) % len(st.session_state.search_results)
        st.session_state.current_index = st.session_state.search_results[new_result_index]
    else:
        st.session_state.current_index = (st.session_state.current_index + direction) % len(st.session_state.flattened_data)


def save_changes(index, current_data):
    # 更新 current_data 中的值
    current_data['name'] = st.session_state.get(f"name_{index}", "")
    current_data['time'] = st.session_state.get(f"time_{index}", "")
    current_data['description'] = st.session_state.get(f"description_{index}", "")
    
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
    
    # 更新 session state 数据
    st.session_state.data[index] = current_data
    
    # 保存到 IndexedDB
    save_to_indexeddb(st.session_state.data)