import streamlit as st
import pandas as pd
import os
from tools.utils import read_csv, search_data
from tools.topic_path import load_topics, get_file_path

def topic_search_page():
    st.title('🔍 定题文献检索')

    # 加载主题词
    topics_df = load_topics()
    
    # 选择主题词
    selected_topic = st.selectbox("#### ✨ 选择定题知识库", topics_df['topic'].tolist())
    folder_path = get_file_path(selected_topic)
    file_name = selected_topic.replace(' ', '_') + '.csv'
    file_path = os.path.join(folder_path, file_name)

    # 设置 CSS 样式
    st.markdown("""
    <style>
    .reportview-container {
        background: #f0f2f6;
    }
    .sidebar .sidebar-content {
        background: #f0f2f6;
    }
    .stButton > button {
        width: 38px;
        height: 38px;
        line-height: 38px;
        padding: 0px;
        font-size: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .search-button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
    }
    .clear-button {
        background-color: #f44336;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)

    try:
        df = read_csv(file_path)

        # 初始化 session state
        if 'conditions' not in st.session_state:
            st.session_state.conditions = []
        if 'search_result' not in st.session_state:
            st.session_state.search_result = None
        if 'keyword_value' not in st.session_state:
            st.session_state.keyword_value = ''

        # 修改清除所有检索条件的函数
        def clear_conditions():
            st.session_state.conditions = []
            st.session_state.search_result = None
            st.session_state.keyword_value = ''  # 清除关键词值

        # 搜索功能
        def add_condition():
            st.session_state.conditions.append(('题名', '', '与'))

        def remove_condition(index):
            st.session_state.conditions.pop(index)

        # 初始检索条件
        cols = st.columns([3, 3, 1])
        with cols[0]:
            search_options = ['题名', '作者', '关键词', '摘要']
            search_column = st.selectbox('检索条件', search_options, key='initial_search_column')
        with cols[1]:
            keyword = st.text_input('输入检索词', key='initial_keyword', value=st.session_state.keyword_value)
            # 更新 keyword_value
            st.session_state.keyword_value = keyword
        with cols[2]:
            st.markdown('<div style="margin-top: 32px;"></div>', unsafe_allow_html=True)
            if st.button('➕', key='add_button', help='增加检索条件'):
                add_condition()

        # 动态添加的检索条件
        for i, (search_column, keyword, logic) in enumerate(st.session_state.conditions):
            cols = st.columns([1, 3, 3, 1])
            with cols[0]:
                logic_options = ['与', '或', '非']
                new_logic = st.selectbox(f'逻辑', logic_options, index=logic_options.index(logic), key=f'logic_{i}')
            with cols[1]:
                new_search_column = st.selectbox(f'检索条件', search_options, index=search_options.index(search_column), key=f'search_column_{i}')
            with cols[2]:
                new_keyword = st.text_input(f'输入检索词', value=keyword, key=f'keyword_{i}')
            with cols[3]:
                st.markdown('<div style="margin-top: 24px;"></div>', unsafe_allow_html=True)
                if st.button('➖', key=f'remove_{i}', help='去除检索条件'):
                    st.session_state.conditions.pop(i)
                    st.rerun()
            
            # 更新条件
            st.session_state.conditions[i] = (new_search_column, new_keyword, new_logic)

        # 执行搜索和清除检索条件
        col1, col2 = st.columns(2)
        with col1:
            if st.button('搜索', key='search_button', help='执行搜索', use_container_width=True):
                conditions = [(search_column, keyword, '与')] + st.session_state.conditions
                result = search_data(df, conditions)
                # 排除指定的列
                columns_to_exclude = ['编号', '专辑', '专题', '爬取时间']
                result = result.drop(columns=columns_to_exclude, errors='ignore')
                st.session_state.search_result = result
        with col2:
            if st.button('清除检索条件', key='clear_button', help='清除所有检索条件', use_container_width=True):
                clear_conditions()
                st.rerun()

        # 应用自定义样式
        st.markdown("""
        <script>
        var buttons = window.parent.document.querySelectorAll('.stButton button');
        buttons[buttons.length - 2].classList.add('search-button');
        buttons[buttons.length - 1].classList.add('clear-button');
        </script>
        """, unsafe_allow_html=True)


        # 显示搜索结果
        if st.session_state.search_result is not None:
            st.write(f'搜索结果：共找到 {len(st.session_state.search_result)} 条记录')
            st.dataframe(st.session_state.search_result)

    except Exception as e:
        st.error(f'错误：{str(e)}')

if __name__ == "__main__":
    topic_search_page()