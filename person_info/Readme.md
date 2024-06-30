# 结构化数据提取：作者信息提取

利用 Langchain-Extract，从采访数据的作者描述文本中提取作者结构化信息。

提取的字段信息，可修改源码中的 `class Person(BaseModel)`部分

规范性操作可以参考上图人名本体词表进行信息提取。此处demo仅作可行性测试

## TODO

- [numind/NuExtract-large · Hugging Face](https://huggingface.co/numind/NuExtract-large)，本地微调模型测试