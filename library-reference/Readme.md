# 参考咨询问答自动分类与回复

## 场景与功能
1. 参考咨询读者问题，分类后自动调用不同的API接口、或代码函数执行，生成回复内容
   
## 工具
1. 大模型接口
- 智谱API
  - glm-4-air，用于情感分析和问题分类
- gpt-4o API
  - 问题分类评估
- Grop API
  - Mixtral-8x7b-32768，馆藏咨询中的信息抽取
- 零一万物API
  - yi-large，除了上述外的其他处理
2. 低代码平台
- FastGPT
  - RAG，馆所知识库
- Coze
  - 联网搜索Agent
3. 其他
- Google Books API
- FOLIO 典藏数据库
  
## 效果
1. 现阶段分类处理了：读者投诉、常规业务咨询、数据库咨询、馆藏图书咨询
- 读者投诉
  - 首先进行情感分类，负面时，直接调用读者投诉的处理逻辑
  - 调用馆所知识库（FastGPT），和回复模板生成回答
- 常规业务咨询
  - 调用馆所知识库（FastGPT）模板生成回答
- 数据库咨询
  - 调用馆所知识库（FastGPT）或联网检索（coze）模板生成回答
- 馆藏图书咨询
  - 信息抽取后，调用Google books API（也可执行FOLIO SQL查询）返回结果
  - 如果没有抽取成功，直接调用海螺AI的网络检索回答
- 学术文献咨询
  - 首先利用 crewAI 构建关键词提取与优化的 Agents，从读者提交问题中抽取检索关键词
  - 然后，检索CNKI爬取数据
  - CNKI失败，则检索 Google Scholar
  - 根据检索到的文献和读者问题，利用 GLM 生成回答
  - 最终返回答案和检索文献列表


## 致谢

1. [JessyTsu1/google_scholar_spider: 谷歌学术爬虫，根据搜索词汇总信息表格并保存](https://github.com/JessyTsu1/google_scholar_spider)
2. [Dramwig/CNKI-spider: 基于selenium包，爬取知网关键字检索的论文信息的Python脚本](https://github.com/Dramwig/CNKI-spider)


## TODO参考

1. [Building a multi-agent concierge system — LlamaIndex, Data Framework for LLM Applications](https://www.llamaindex.ai/blog/building-a-multi-agent-concierge-system)
   
   - 提出了一个由多个智能体组成的系统，每个智能体负责处理特定的任务，同时还有一个 “前台” 智能体用于引导用户到正确的智能体。该系统包括四个基础的 “任务” 智能体和三个 “元” 智能体。基础智能体包括股票查询、用户认证、账户余额查询和资金转账。元智能体包括前台智能体、编排智能体和继续智能体。编排智能体负责根据用户当前的任务选择下一个应该运行的智能体，而继续智能体则负责在任务完成后链接智能体，以便在没有进一步用户输入的情况下完成任务。全局状态用于跟踪用户和当前状态，并在所有智能体之间共享。


## 其他补充

1. 类似demo项目：[Claude Customer Support Agent](https://github.com/anthropics/anthropic-quickstarts/tree/main/customer-support-agent)