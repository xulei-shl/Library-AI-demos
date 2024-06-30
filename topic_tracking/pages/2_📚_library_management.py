import streamlit as st
import time
import os
import pandas as pd
from tools.CNKI_spider import cnki_spider
from tools.exceptions import NoResultsFoundException
from tools.topic_path import load_topics, get_file_path
from tools.csv_duplicate_check import check_duplicates


def literature_management_page():

    st.title("📚 文献库管理")

    if 'topics_df' not in st.session_state:
        st.session_state.topics_df = load_topics()

    selected_topic = st.selectbox("选择主题词", st.session_state.topics_df['topic'].tolist())

    st.markdown("---")
    st.markdown("### 📄 爬取文献 ")

    with st.form(key='knowledge_base_form'):

        
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
    
    st.markdown("---")
    st.markdown("### 🕷️ 爬取日志 ")

    folder_path = get_file_path(selected_topic)
    log_file_name = '爬取日志.xlsx'
    log_file_path = os.path.join(folder_path, log_file_name)

    # 读取Excel文件
    if os.path.exists(log_file_path):
        df = pd.read_excel(log_file_path)
        st.dataframe(df)  # 使用st.dataframe显示数据
    else:
        st.error("日志文件不存在")

    # csv重复数据检索
    st.markdown("---")
    st.markdown("### 🚫 重复数据检查 ")

    check_duplicates_button = st.button("检查重复数据")

    if check_duplicates_button:
        duplicates = check_duplicates(selected_topic)
        if duplicates.empty:
            st.info("没有重复数据")
        else:
            st.dataframe(duplicates)
            st.info(f"文件夹路径: {folder_path}")


if __name__ == "__main__":
    literature_management_page()                