import streamlit as st

def homepage():
    st.set_page_config(page_title='学术定题追踪与 AI 问答', layout='wide')
    
    # 直接显示主页

    st.title('📚 学术定题追踪与 AI 问答')
    st.markdown("""
        ### 主要功能包括:

        1. 主题词管理:
            - 用户可以管理感兴趣的论文主题关键词
            - 系统会根据关键词从CNKI核心期刊数据库中爬取相关论文元数据

        2. 文献库管理:
            - 系统会将爬取的论文元数据(标题、作者、摘要等)进行存储和管理
            - 用户可以查看、筛选和导出文献信息

        3. 知识库管理:
            - 系统会对文献元数据进行向量化处理，构建知识库

        4. AI问答机器人:
            - 基于构建的知识库，提供智能问答服务

    """)

if __name__ == '__main__':
    homepage()
