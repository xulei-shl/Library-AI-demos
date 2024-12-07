## 论文

1. Gao Y, Xiong Y, Gao X, et al. Retrieval-augmented generation for large language models: A survey[J]. arXiv:2312.10997, 2023.

2. Zhao P, Zhang H, Yu Q, et al. Retrieval-Augmented Generation for AI-Generated Content: A Survey[J]. arXiv, 2024.
  - https://github.com/PKU-DAIR/RAG-Survey


## 网络文本

1. [LLM From the Trenches: 10 Lessons Learned Operationalizing Models at GoDaddy - GoDaddy Blog](https://www.godaddy.com/resources/news/llm-from-the-trenches-10-lessons-learned-operationalizing-models-at-godaddy#h-1-sometimes-one-prompt-isn-t-enough)

2. [一文详谈 RAG 优化方案与实践 | BestBlogs](https://www.bestblogs.dev/article/8f14c3)
   
   - 知识加工生成实现策略
     - 知识切片优化。句子语义切分
     - 索引优化。HyDE、索引降噪、多级索引
   - query改写的实现策略
     - RAG-Fusion
     - Step-Back Prompting
     - 用户 query 降噪
   - 数据召回的实现策略
     - 向量召回
     - 分词召回
     - 图谱召回
     - 多路召回
   - 后置处理的实现策略
     - 文档合并去重
     - Rerank 精排

3. [LLM应用架构 -- AI 工程化](https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzA5MTIxNTY4MQ==&action=getalbum&album_id=3070790072247058439&subscene=&sessionid=svr_eabbfae5579&enterid=1718693540&from_msgid=2461141557&from_itemidx=1&count=3&nolastread=1#wechat_redirect)
4. [15 Advanced RAG Techniques | WillowTree](https://www.willowtreeapps.com/guides/advanced-rag-techniques)
  - 预检索和数据索引技术：
      - 使用 LLM 增加信息密度
      - 应用分层索引检索
      - 使用假设问题索引改善检索对称性
      - 使用 LLM 删除数据索引中的重复信息
      - 测试和优化分块策略
  - 检索技术
    - 使用 LLM 优化搜索查询
    - 使用假设文档嵌入 (HyDE) 解决查询-文档不对称问题
    - 实现查询路由或 RAG 决策模式
  - 检索后技术
    - 使用 reranking 优先处理搜索结果
    - 使用上下文提示压缩优化搜索结果
    - 使用校正 RAG 对检索到的文档进行评分和过滤
  - 生成技术
     - 使用思维链提示调整噪音
     - 使用 Self-RAG 使系统具有自反性
     - 通过微调忽略不相关上下文
     - 使用自然语言推理使 LLM 对不相关上下文具有鲁棒性
  - 其他潜在改进
    - 微调嵌入模型：通过调整嵌入模型来优化性能
    - 使用 GraphRAG：将知识图谱引入 RAG 系统
    - 使用长上下文 LLM：如 Gemini 1.5 或 GPT-4 128k，以替代传统的分块和检索方法
5. [Advanced RAG: Architecture, Techniques, Applications and Use Cases and Development](https://www.leewayhertz.com/advanced-rag/)
  - RAG 的重要性:
    - RAG 通过结合外部知识源来增强 LLM 的性能
    - 据 Databricks 统计，60% 的企业 LLM 应用使用 RAG
    - RAG 可以使 LLM 的响应准确性提高近 43%
  - 高级 RAG 的发展:
    - 从基础/朴素 RAG 发展到高级 RAG，解决了复杂查询处理、上下文理解等问题
    - 多模态 RAG 和知识图谱是重要发展方向

  - 高级 RAG 架构和技术:
    - 主要组件包括数据准备、用户输入处理、检索系统、信息处理和生成、反馈和持续改进等
    - 高级技术包括多阶段检索、查询重写、子查询分解、假设文档嵌入 (HyDE) 等

  -知识图谱在 RAG 中的应用:
    - 知识图谱提供结构化的知识表示，增强了上下文理解和推理能力
    - GraphRAG 结合了知识图谱和向量数据库,提高了准确性和可解释性

   - 多模态 RAG:
     - 整合文本、图像、音频、视频等多种数据类型
     - 通过统一的嵌入空间和跨模态注意力机制来管理不同模态的信息

   - 应用场景:
     - 高级 RAG 在市场研究、客户支持、合规风控、产品开发、金融分析等多个领域有广泛应用
     - 多模态 RAG 在医疗保健、教育、金融服务等行业有潜在应用
6. [NisaarAgharia/Advanced_RAG: Advanced Retrieval-Augmented Generation (RAG) through practical notebooks, using the power of the Langchain, OpenAI GPTs ,META LLAMA3 ,Agents.](https://github.com/NisaarAgharia/Advanced_RAG)
   1. 基础和高级RAG示例代码：多查询检索、自反射 RAG、Agentic RAG、自适应代理RAG、纠正代理RAG
7. [Augment your LLMs using RAG | Databricks](https://www.databricks.com/resources/ebook/train-llms-your-data)
   1. RAG 的关键组成:
      - LLM 和提示工程
      - 向量搜索和嵌入模型
      - 向量数据库

    2. RAG 的核心步骤:
      - 数据准备
      ·- 解析输入文档
      ·- 将文档分割成 smaller chunks
      ·- 使用嵌入模型将文本块转换为向量
      ·- 在向量数据库中存储和索引嵌入向量
      ·- 记录元数据

    3. 检索
      ·- 将用户查询转换为向量
      ·- 在向量数据库中搜索相似记录
      ·- 选择最相关的结果

    4. 增强
      ·- 将检索到的相关文本与用户原始提示组合
      ·- 构建包含上下文和使用说明的新提示

    5. 生成
      ·- 将增强后的提示发送给 LLM
      ·- LLM 生成响应
      ·- 对输出进行后处理 (如有必要)

    6. RAG 实施的关键考虑:
      - 文档分块大小
      ·- 太小可能缺乏足够上下文
      ·- 太大可能导致 LLM 无法提取相关细节
      ·- 需要根据源文档、LLM 和应用目标进行调整

    7. 检索结果数量
      ·- 检索太少可能遗漏相关信息
      ·- 检索太多可能稀释相关信息
      ·- 需要平衡相关性和信息量

    8. 上下文窗口大小
      ·- 需要确保所有检索文本和用户提示适合 LLM 的上下文窗口
      ·- 考虑 "lost in the middle" 现象，LLM 可能更关注长文本的开头和结尾

    9. 提示工程和后处理
      ·- 设计有效的提示模板以指导 LLM 如何使用上下文
      ·- 考虑对 LLM 输出进行后处理以确保格式一致性或添加额外信息

    10. 评估方法
      ·- 单独评估检索和生成步骤
      ·- 考虑使用其他 LLM 来评判响应质量
      ·- 评估响应与提供上下文的 "忠实度"

    11. 对话历史管理
      ·- 决定是否实现多轮对话功能
      ·- 如果实现，需要考虑如何有效管理对话历史和上下文长度

    12. RAG 的优势:
      - 可以纳入专有数据和最新信息
      - 提高 LLM 响应的准确性
      - 实现细粒度的数据访问控制

    13. RAG 与其他 LLM 定制方法的比较:
      - 提示工程: 最简单但表达能力有限
      - 微调: 可以改变模型行为但更新信息不便
      - 预训练: 最高成本但控制力最强
      - RAG: 在成本、复杂性和表达能力间取得平衡
8. [bRAGAI/bRAG-langchain: Everything you need to know to build your own RAG application](https://github.com/bRAGAI/bRAG-langchain)
  - 提供了构建自己的基于 RAG 的应用程序的全面指南，包括从基础到高级实现的详细教程和示例。这些指南涵盖了环境搭建、数据预处理、嵌入生成、向量存储、RAG 管道构建、多查询技术、自定义 RAG 流程、高级检索和重排等方面

## 视频教程
1. [Advanced RAG: Dynamic Chunk/Document Retrieval (with LlamaCloud) - YouTube](https://www.youtube.com/watch?v=uFWHweuTCGE)
   1. 动态分块
2. 
   
## 案例

1. [emarco177/langgaph-course](https://github.com/emarco177/langgaph-course)
   
   - 使用 LangGraph 实现高级 RAG 控制流
   - Corrective-RAG (CRAG)：在检索到的文档上进行自我评分，并在需要时使用网络搜索作为备选方案
   - Self-RAG：在生成内容上进行自我评分，以识别和减少幻觉
   - Adaptive RAG：根据查询的复杂性来路由查询
  
2. [NirDiamant/RAG_Techniques: This repository showcases various advanced techniques for Retrieval-Augmented Generation (RAG) systems. RAG systems combine information retrieval with generative models to provide accurate and contextually rich responses.](https://github.com/NirDiamant/RAG_Techniques)
   1. 专注于展示和提供多种高级的检索增强生成（RAG）技术。详细介绍了二十多种 RAG 技术，包括简单 RAG、语境丰富技术、多方面过滤、融合检索、智能重新排名等。每种技术都有其概述和实施步骤
3. [cohere-ai/notebooks: Code examples and jupyter notebooks for the Cohere Platform](https://github.com/cohere-ai/notebooks)