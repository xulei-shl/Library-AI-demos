## 大模型基础

1. 赵鑫, 李军毅, 周昆, 唐天一, 文继荣. 大语言模型，https://llmbook-zh.github.io/，2024.
2. Huang K, Mo F, Li H, et al. A Survey on Large Language Models with Multilingualism: Recent Advances and New Frontiers[J]. arXiv, 2024.

## 提示词
1. Pranab Sahoo, Ayush Kumar Singh, Sriparna Saha, Vinija Jain, Samrat Mondal, Aman Chadha (2024).A Systematic Survey of Prompt Engineering in Large Language Models: Techniques and Applications


## RAG
1. Gao Y, Xiong Y, Gao X, et al. Retrieval-augmented generation for large language models: A survey[J]. arXiv:2312.10997, 2023.

2. Zhao P, Zhang H, Yu Q, et al. Retrieval-Augmented Generation for AI-Generated Content: A Survey[J]. arXiv, 2024.
  - https://github.com/PKU-DAIR/RAG-Survey

## 智能体
1. Huang X, Liu W, Chen X, et al. Understanding the planning of LLM agents: A survey[J]. arXiv:2402.02716, 2024.

## 微调

## 实践案例

1. ChatGPT for Classification: Evaluation of an Automated Course Mapping Method in Academic Libraries
   - 研究展示了如何利用GPT-4的提提示词工程，结合图书馆参考数据，实现对本科课程描述的自动化分类
   - 解决方案中核心的方法/步骤/策略：
	- 使用GPT-4的插件功能，向模型提供课程描述和可能的参考书目，以支持其推理过程。
	- 设计了包含链式思考的提示，以引导GPT-4逐步进行推理。
	- 使用Library of Congress分类PDF数据来提高GPT-4的输出质量。
  
2. Zeng Z, Watson W, Cho N, et al. FlowMind: Automatic Workflow Generation with LLMs[M]. arXiv, 2024.
   - FlowMind利用大语言模型的能力，可以自动生成工作流程来处理自发的任务。它将可用的API函数"讲授"给语言模型，然后语言模型根据用户需求，自主编写工作流程代码，调用这些API函数来完成任务，并可以与用户交互优化工作流。
   - 首先通过"讲座"提示来教育语言模型，为其提供上下文信息、可用API的描述以及编写工作流代码的要求。
   - LLM根据"讲座"中的信息，利用提供的API自动生成工作流代码。生成的代码是模块化的，能够恰当地调用API完成任务。
   - 将生成的工作流代码提供给用户审阅，并允许用户给出反馈意见。LLM根据用户反馈对代码进行优化和调整。
   - 优化后的工作流代码可以执行以可靠地完成用户要求的任务，并给出结果。
3. 

## Cookbook

### 图书
1. 大模型应用开发极简入门-基于 GPT-4 和ChatGPT | 【比】奥利维耶·卡埃朗【法】玛丽-艾丽斯·布莱特；何文斯 译
  1. 入门级教程，推荐。全书示例代码见：malywut/gpt_examples
  2. GPT基础知识介绍
  3. 的AI应用（LLM API调用）开发极简代码示例
  4. 提示词、微调、 LangChain应用示例
   
2. 大模型应用开发 动手做AI Agent (豆瓣)
3. ChatGPT 原理与应用开发 | 郝少春；黄玉琳；易华挥
4. LangChain 入门指南：构建高可复用、可扩展的 LLM 应用程序 (豆瓣)