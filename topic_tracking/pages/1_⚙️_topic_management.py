import streamlit as st
import pandas as pd
import os
import time
import shutil
from tools.CNKI_spider import cnki_spider
from tools.exceptions import NoResultsFoundException
from tools.topic_path import load_topics, create_csv_file, TOPICS_FILE

def save_topics(topics_df):
    topics_df.to_csv(TOPICS_FILE, index=False)

def add_topic(new_topic):
    if new_topic and new_topic not in st.session_state.topics_df['topic'].values:
        new_folder_path = create_csv_file(new_topic)
        new_row = pd.DataFrame({'topic': [new_topic], 'folder_path': [new_folder_path]})
        st.session_state.topics_df = pd.concat([st.session_state.topics_df, new_row], ignore_index=True)
        save_topics(st.session_state.topics_df)
        st.success(f"已添加主题词：{new_topic}")
    elif new_topic in st.session_state.topics_df['topic'].values:
        st.error("该主题词已存在")
    else:
        st.error("请输入主题词")

    time.sleep(1.5)
    st.rerun()        

def delete_topic(topic_to_delete):
    topic_row = st.session_state.topics_df[st.session_state.topics_df['topic'] == topic_to_delete]
    if not topic_row.empty:
        folder_path = topic_row['folder_path'].values[0]
        del_folder_path = os.path.join('data', 'del')
        if not os.path.exists(del_folder_path):
            os.makedirs(del_folder_path)
        new_folder_path = os.path.join(del_folder_path, os.path.basename(folder_path))
        shutil.move(folder_path, new_folder_path)
        st.session_state.topics_df = st.session_state.topics_df[st.session_state.topics_df['topic'] != topic_to_delete]
        save_topics(st.session_state.topics_df)
        return True
    return False

def topic_management_page():
    st.title("⚙️ 主题词管理")
    st.markdown("---")

    if not os.path.exists('data'):
        os.makedirs('data')

    if 'topics_df' not in st.session_state:
        st.session_state.topics_df = load_topics()
    
    if 'confirm_delete' not in st.session_state:
        st.session_state.confirm_delete = False

    col1, col2 = st.columns(2)

    with col1:
        with st.form(key='add_topic_form'):
            st.markdown("#### 🆕 新增")
            new_topic = st.text_input("输入新主题词")
            submit_button = st.form_submit_button(label='添加')
            if submit_button:
                add_topic(new_topic)

    with col2:
        with st.form(key='delete_topic_form'):
            st.markdown("#### 🗑️ 删除")
            topic_to_delete = st.selectbox("选择要删除的主题词", st.session_state.topics_df['topic'].tolist())
            
            if not st.session_state.confirm_delete:
                delete_button = st.form_submit_button(label='删除')
                if delete_button:
                    st.session_state.confirm_delete = True
                    st.rerun()
            else:
                st.warning(f"您确定要删除主题词：{topic_to_delete} 及其文献知识库吗？")
                col1, col2 = st.columns(2)
                with col1:
                    confirm_button = st.form_submit_button(label='确认', type='primary')
                with col2:
                    cancel_button = st.form_submit_button(label='取消')
                
                if confirm_button:
                    if delete_topic(topic_to_delete):
                        st.error(f"已删除主题词：{topic_to_delete} 及其文献知识库")
                    else:
                        st.error("删除失败，未找到该主题词")
                    st.session_state.confirm_delete = False
                    time.sleep(1.5)
                    st.rerun()
                elif cancel_button:
                    st.session_state.confirm_delete = False
                    st.rerun()

def literature_management_page():
    st.title("📚 文献库管理")
    st.markdown("---")

    if 'topics_df' not in st.session_state:
        st.session_state.topics_df = load_topics()

    with st.form(key='knowledge_base_form'):
        selected_topic = st.selectbox("选择主题词", st.session_state.topics_df['topic'].tolist())
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            start_year = st.selectbox("起始年份", range(2000, 2025), index=21)  # 默认选择2021年
        with col2:
            end_year = st.selectbox("结束年份", range(2025, 2000, -1), index=1)  # 默认选择2024年
        with col3:
            st.empty()  # 创建一个小的空间
            st.markdown('<div style="margin-top: 1.7em;"></div>', unsafe_allow_html=True)  # 添加0.5em的垂直间距
            submit_button = st.form_submit_button(label='确认')
        
        if submit_button:
            if start_year <= end_year:
                placeholder = st.empty()  # 创建一个占位符
                st.info(f"正在为主题词 '{selected_topic}' 爬取 {start_year} 到 {end_year} 年的文献...")
                try:
                    cnki_spider(selected_topic, start_year, end_year, st=st)  # 传递st对象
                    st.success("文献爬取完成！")
                    time.sleep(1.5)
                    st.rerun()
                except NoResultsFoundException as e:
                    st.warning(str(e))
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"爬取过程中出现错误: {str(e)}")
            else:
                st.error("起始年份必须小于或等于结束年份")

if __name__ == "__main__":
    topic_management_page()