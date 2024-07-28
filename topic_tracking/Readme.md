# 学术定题追踪与 AI 问答

## 主要功能包括:

1. 主题词管理:
    - 用户可以管理感兴趣的论文主题关键词
    - 脚本会根据关键词从 CNKI 爬取核心期刊相关论文元数据

2. 文献库管理:
    - 对爬取的论文元数据(标题、作者、摘要等)进行存储和管理
    - 用户可以查看、检索和导出文献信息（其实都是本地文件存储）

3. 知识库管理:
    - 系统会对文献元数据进行向量化处理，构建知识库

4. AI 问答机器人:
    - 基于构建的知识库，提供智能问答服务

## 下一步

1. 基于知识库的，研究综述撰写 Agents
   
2. RAG 的稍微优化
3. 如果获取到论文 PDF ，可以考虑使用 [whitead/paper-qa](https://github.com/whitead/paper-qa)项目搭建基于本地文档库的 QA 机器人
   - [PaperQA - YouTube](https://www.youtube.com/watch?v=-o5_HMBq5ys)
4. Qdrant 最新的混合算法 [BM42](https://qdrant.tech/articles/bm42/)
5. RSS订阅文章总结
   - [ginobefun/BestBlogs: 基于 Dify Workflow 的文章智能分析实践](https://github.com/ginobefun/BestBlogs/tree/main)
   - [Dify 教程案例分享：RSS 自动摘要 (summary) & 自动发送邮件(Email) Newsletter - YouTube](https://www.youtube.com/watch?v=g8ZHnQxfv4w)
   - RSS订阅与全文都是单独模块处理存储在数据库或者多维表格，然后通过Dify Workflow API触发流程
   - 
   

## 预警

1. RAG 优化超过了本人的能力范围，所以项目只是使用了 Chainlit 基础功能