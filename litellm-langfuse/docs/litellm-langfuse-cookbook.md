## 食谱：使用 OpenAI SDK 监控 DeepSeek 模型与 Langfuse

DeepSeek API 使用与 OpenAI 兼容的 API 格式。通过修改配置，您可以使用 OpenAI SDK 或兼容 OpenAI API 的软件来访问 DeepSeek API。

本食谱展示了如何使用 OpenAI SDK 与 [Langfuse](https://langfuse.com/) 集成来监控 [DeepSeek](https://github.com/deepseek-ai/DeepSeek-V3) 模型。通过利用 Langfuse 的可观测性工具和 OpenAI SDK，您可以有效地调试、监控和评估使用 DeepSeek 模型的应用程序。

本指南将引导您完成设置集成、向 DeepSeek 模型发送请求以及使用 Langfuse 观察交互的过程。

**注意：** Langfuse 还与 [LangChain](https://langfuse.com/docs/integrations/langchain/tracing)、[LlamaIndex](https://langfuse.com/docs/integrations/llama-index/get-started)、[LiteLLM](https://langfuse.com/docs/integrations/litellm/tracing) 和 [其他框架](https://langfuse.com/docs/integrations/overview) 原生集成。这些框架也可以用来追踪 DeepSeek 请求。

## 设置

### 安装所需软件包

要开始，请安装必要的软件包。确保您拥有 `langfuse` 和 `openai` 的最新版本。

```
%pip install langfuse openai --upgrade
```

### 设置环境变量

使用必要的密钥设置您的环境变量。从 [Langfuse Cloud](https://cloud.langfuse.com/) 获取您的 Langfuse 项目密钥。您还需要从 [DeepSeek](https://platform.deepseek.com/api_keys) 获取访问令牌以访问他们的模型。

```
import os
 
# 从 https://cloud.langfuse.com 获取您的项目密钥
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-..."
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-..."
os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com"  # 🇪🇺 欧盟地区
# os.environ["LANGFUSE_HOST"] = "https://us.cloud.langfuse.com"  # 🇺🇸 美国地区
 
# 您的 DeepSeek API 密钥（从 https://platform.deepseek.com/api_keys 获取）
os.environ["DEEPSEEK_API_KEY"] = "sk-..."  # 用您的 DeepSeek API 密钥替换
```

### 导入必要的模块

不要直接导入 `openai`，而是从 `langfuse.openai` 导入它。还可以导入其他必要的模块。

查看我们的 [OpenAI 集成文档](https://langfuse.com/docs/integrations/openai/python/get-started)，了解如何将此集成与其他 Langfuse [功能](https://langfuse.com/docs/tracing#advanced-usage) 一起使用。

```
# 不要这样做：import openai
from langfuse.openai import OpenAI
from langfuse.decorators import observe
```

### 初始化 OpenAI 客户端以使用 DeepSeek 模型

初始化 OpenAI 客户端，指向 DeepSeek 模型端点。用您自己的模型 URL 和 APP 密钥替换。

```
# 初始化 OpenAI 客户端，指向 DeepSeek 推理 API
client = OpenAI(
    base_url="https://api.deepseek.com",  # 用 DeepSeek 模型端点 URL 替换
    api_key=os.getenv('DEEPSEEK_API_KEY'),  # 用您的 DeepSeek API 密钥替换
)
```

## 示例

### 聊天完成请求

使用 `client` 向 DeepSeek 模型发送聊天完成请求。`model` 参数可以是任何标识符，因为实际的模型在 `base_url` 中指定。

```
completion = client.chat.completions.create(
    model="deepseek-chat", 
    messages=[
        {"role": "system", "content": "您是一个有帮助的助手。"},
        {"role": "user", "content": "为什么 AI 很酷？用 20 个字或更少回答。"}
    ]
)
print(completion.choices[0].message.content)
```

```
AI 很酷，因为它能自动化任务，增强创造力，解决复杂问题，并用智能、高效的解决方案改变行业。
```

![Langfuse 中的示例追踪](https://langfuse.com/images/cookbook/integration_deepseek/deepseek-simple-trace.png)

*[在 Langfuse 中查看示例追踪](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/83702a6c-ae0e-4317-87fa-dc82568a2d89?timestamp=2025-01-09T17%3A06%3A40.848Z)*

### 使用 Langfuse 观察请求

通过使用 `langfuse.openai` 中的 `OpenAI` 客户端，您的请求会自动在 Langfuse 中追踪。您还可以使用 `@observe()` 装饰器将多个生成归入一个追踪。

```
@observe()  # 装饰器自动创建追踪并嵌套生成
def generate_story():
    completion = client.chat.completions.create(
        name="story-generator",
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "您是一个有创意的故事讲述者。"},
            {"role": "user", "content": "告诉我一个关于一个在前往语言模型的途中迷路的代币的短故事。用 100 个字或更少回答。"}
        ],
        metadata={"genre": "adventure"},
    )
    return completion.choices[0].message.content
 
story = generate_story()
print(story)
```

```
曾经，一个名叫 Lex 的小代币出发去加入语言模型的宏伟图书馆。在途中，Lex 被一个闪闪发光的比喻分心，误入了语法迷宫。在悬挂的修饰语和流氓逗号中迷失，Lex 哭着求助。一个友好的表情符号发现了 Lex，并指引它回到正确的道路上。"坚持向量，"表情符号建议道。Lex 最终到达了，变得稍微聪明了一些，并将它的故事低语进了模型的广阔神经网络。从那时起，模型总是暂停以欣赏每个代币的旅程，无论多么小或迷失。
```

![Langfuse 中的示例追踪](https://langfuse.com/images/cookbook/integration_deepseek/deepseek-story-trace.png)

*[在 Langfuse 中查看示例追踪](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/9a0dca39-9fac-4fce-ace9-52b85edfb0d8?timestamp=2025-01-09T17%3A08%3A25.698Z)*

您可以通过添加 `user_id`、`session_id`、`tags` 和 `metadata` 等属性来增强您的追踪。

```
completion_with_attributes = client.chat.completions.create(
    name="math-tutor",  # 追踪名称
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "您是一位数学辅导员。"},
        {"role": "user", "content": "帮助我理解勾股定理。用 100 个字或更少回答。"}
    ],
    temperature=0.7,
    metadata={"subject": "Mathematics"},  # 追踪元数据
    tags=["education", "math"],  # 追踪标签
    user_id="student_001",  # 追踪用户 ID
    session_id="session_abc123",  # 追踪会话 ID
)
print(completion_with_attributes.choices[0].message.content)
```

```
勾股定理是几何中的基本原理，指出在直角三角形中，斜边（与直角相对的边）的平方等于其他两边的平方之和。数学上表示为 \( a^2 + b^2 = c^2 \)，其中 \( c \) 是斜边，\( a \) 和 \( b \) 是其他两边。这个定理用于计算距离，构建形状，并解决涉及直角三角形的各种现实问题。它以古希腊数学家毕达哥拉斯命名，他被认为是其发现者。
```

*[在 Langfuse 中查看示例追踪](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/e18ab6ff-7ad5-491b-87bf-571dd7854923?timestamp=2025-01-09T17%3A09%3A52.866Z)*

### 使用 Langfuse 上下文更新追踪属性

您可以使用 `langfuse_context` 在函数内修改追踪属性。

```
from langfuse.decorators import langfuse_context
 
@observe()
def technical_explanation():
    # 您的主要应用程序逻辑
    response = client.chat.completions.create(
        name="tech-explainer",
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "解释区块链技术是如何工作的。用 30 个字或更少回答。"}
        ],
    ).choices[0].message.content
 
    # 使用额外信息更新当前追踪
    langfuse_context.update_current_trace(
        name="Blockchain Explanation",
        session_id="session_xyz789",
        user_id="user_tech_42",
        tags=["technology", "blockchain"],
        metadata={"topic": "blockchain", "difficulty": "intermediate"},
        release="v1.0.0",
    )
 
    return response
 
result = technical_explanation()
print(result)
```

```
区块链是一种去中心化的数字账本，记录跨计算机网络的交易。每个区块包含数据、时间戳和与前一个区块的加密链接，确保安全性和透明度。
```

*[在 Langfuse 中查看示例追踪](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/06cca972-a885-454f-8303-0fd753dbf5e3?timestamp=2025-01-09T17%3A10%3A39.275Z)*

### 以编程方式添加分数

向追踪添加 [分数](https://langfuse.com/docs/scores) 以记录用户反馈或编程评估。在生产中，分数通常在单独的函数中进行，可以通过传递 `trace_id` 来实现。

```
from langfuse import Langfuse
 
langfuse = Langfuse()
 
@observe()
def generate_and_score():
    # 获取当前追踪的 trace_id
    trace_id = langfuse_context.get_current_trace_id()
  
    # 生成内容
    content = client.chat.completions.create(
        name="content-generator",
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "什么是量子计算？用 50 个字或更少回答。"}
        ],
    ).choices[0].message.content
  
    # 评估内容（占位符函数）
    score_value = evaluate_content(content)
  
    # 向 Langfuse 添加分数
    langfuse.score(
        trace_id=trace_id,
        name="content_quality",
        value=score_value,
    )
  
    return content
 
def evaluate_content(content):
    # 占位符评估函数（例如，内容长度或关键词存在）
    return 9.0  # 10 分制中的分数
 
output = generate_and_score()
print(output)
```

```
量子计算利用量子力学处理信息，使用量子比特，可以同时存在多种状态。这使其能够比经典计算机更快地解决复杂问题，特别是在密码学、优化和模拟方面，通过利用叠加、纠缠和量子干涉。
```

*[在 Langfuse 中查看示例追踪](https://cloud.langfuse.com/project/cloramnkj0002jz088vzn1ja4/traces/44616768-253d-41fd-b336-8611899a2fad?timestamp=2025-01-09T17%3A11%3A01.665Z)*