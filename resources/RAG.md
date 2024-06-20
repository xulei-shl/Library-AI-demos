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

3. 