# 结构化数据提取：作者信息提取

利用 Langchain-Extract，从采访数据的作者描述文本中提取作者结构化信息。

提取的字段信息，可修改源码中的 `class Person(BaseModel)`部分

规范性操作可以参考上图人名本体词表进行信息提取。此处demo仅作可行性测试

## TODO

1. 本地微调模型测试
   - [numind/NuExtract-large · Hugging Face](https://huggingface.co/numind/NuExtract-large)
   - [wenge-research/YAYI-UIE: 雅意信息抽取大模型)](https://github.com/wenge-research/YAYI-UIE)

## 相关研究

1. [Automatic extraction of FAIR data from publications using LLM](https://chemrxiv.org/engage/chemrxiv/article-details/656c34ab29a13c4d478b2a12)
   -  研究 ChatGPT 自动提取化学实验数据的方法，以提高科学数据的可查询性（FAIR），并讨论了该方法的实施、效率和成本效益
   -  方法基于 ChatGPT，通过精心设计的提示（prompt）指令，能够从文献的实验部分中自动识别和解析结构化数据，如化合物的名称、产率、外观、熔点、NMR 和质谱数据等
   -  比较了YAML和 JSON两种 格式在提供结构化数据输的效率与成本。YAML优于 JSON

2. Prompt Patterns for Structured Data Extraction from Unstructured Text
   - 通过提示模式（prompt patterns）从非结构化文本中提取结构化数据，并提供了一系列可重用的模板和方法论，以提高数据提取的有效性和可重复性
   - 语义提取器、动态属性提取器、模式匹配器、上下文传递器和关键词触发提取器
3. 