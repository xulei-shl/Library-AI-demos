
## 处理流程 

![](https://xulei-pic-1258542021.cos.ap-shanghai.myqcloud.com/mdpic/%E8%8A%82%E7%9B%AE%E5%8D%95LLM%E5%AE%9E%E4%BD%93%E6%8F%90%E5%8F%96.png)

## 预警

1. OCR 识别后是长文本，信息抽取按照实体类型分步骤多次调用LLM（一条数据调用多的达到几十次），Token消耗较大，运行时间较长。
   
2. 部分实体抽取与分类有出错概率。后续可以考虑用多模型组成链式多智能体，或者MoA混合智能体对较容易出错的实体抽取环节进行优化。
   1. [MoA示例项目代码](https://github.com/Shubhamsaboo/awesome-llm-apps/blob/main/mixture_of_agents/mixture-of-agents.py)
   2. [skapadia3214/groq-moa: Mixture of Agents using Groq](https://github.com/skapadia3214/groq-moa)
3. [Let Me Speak Freely? A Study on the Impact of Format Restrictions on Performance of Large Language Models](https://arxiv.org/abs/2408.02442)研究表明在某些情况下，输出格式限制会降低大模型的推理能力，而且JSON最严重。后续，某些环节是否可以先用 CoT 等提示技术让大模型用自然语言返回结果，然后再用小模型进行结构化数据抽取。