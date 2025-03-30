## 示例：Langfuse 提示管理用于 OpenAI 函数（Python）

Langfuse [提示管理](https://langfuse.com/docs/prompts) 帮助在一个地方进行版本控制和协作管理提示。本示例展示了如何使用 Langfuse 提示中的灵活 `config` 对象来存储函数调用选项和模型参数。

## 设置

```
%pip install langfuse openai --upgrade
```

```
import os
 
# 获取你的项目密钥
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""
os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com"
 
# OpenAI 密钥
os.environ["OPENAI_API_KEY"] = ""
```

```
from langfuse import Langfuse
langfuse = Langfuse()
 
# 可选，验证 Langfuse 是否配置正确
langfuse.auth_check()
```

```
True
```

## 将提示添加到 Langfuse 提示管理

我们通过 SDK 添加本示例中使用的提示。或者，您也可以在 Langfuse UI 中编辑和版本化提示。

- 在 Langfuse 提示管理中标识提示的 `名称`
- 带有 `json_schema` 变量的提示
- 包括 `model_name`、`temperature` 和 `json_schema` 的配置
- 包含 `production` 的 `labels`，以立即将提示用作默认值

```
langfuse.create_prompt(
    name="story_summarization",
    prompt="从这段文本中提取关键信息，并以 JSON 格式返回。使用以下模式：{{json_schema}}",
    config={
        "model":"gpt-3.5-turbo-1106",
        "temperature": 0,
        "json_schema":{
            "main_character": "string (主角的名字)",
            "key_content": "string (一句话)",
            "keywords": "array of strings",
            "genre": "string (故事的类型)",
            "critic_review_comment": "string (类似纽约时报评论家的评论)",
            "critic_score": "number (介于0差到10优秀之间)"
        }
    },
    labels=["production"]
);
```

Langfuse UI 中的提示

![Langfuse 提示管理](https://langfuse.com/images/docs/prompt-management-with-config-for-openai-functions.png)

## 示例应用

### 从 Langfuse 获取当前提示版本

```
prompt = langfuse.get_prompt("story_summarization")
```

我们现在可以使用提示来编译我们的系统消息

```
prompt.compile(json_schema="测试模式")
```

```
'从这段文本中提取关键信息，并以 JSON 格式返回。使用以下模式：测试模式'
```

并且它包括配置对象

```
prompt.config
```

```
{'model': 'gpt-3.5-turbo-1106',
 'json_schema': {'genre': 'string (故事的类型)',
  'keywords': 'array of strings',
  'key_content': 'string (一句话)',
  'critic_score': 'number (介于0差到10优秀之间)',
  'main_character': 'string (主角的名字)',
  'critic_review_comment': 'string (类似纽约时报评论家的评论)'},
 'temperature': 0}
```

### 创建示例函数

在本示例中，我们通过从 `langfuse.openai` 导入，使用原生的 [Langfuse OpenAI 集成](https://langfuse.com/docs/integrations/openai)。这启用了 Langfuse 中的 [追踪](https://langfuse.com/docs/tracing)，并且对于使用 Langfuse 提示管理不是必需的。

```
from langfuse.openai import OpenAI
client = OpenAI()
```

使用 Langfuse 提示构建 `summarize_story` 示例函数。

**注意：** 您可以通过将 `langfuse_prompt` 参数传递给 `create` 方法，将 Langfuse 追踪中的生成链接到提示版本。请查看我们的 [提示管理文档](https://langfuse.com/docs/prompts/get-started#link-with-langfuse-tracing-optional) 了解如何将提示和生成与其他集成和 SDK 链接。

```
import json
 
def summarize_story(story):
  # 将 JSON 模式字符串化
  json_schema_str = ', '.join([f"'{key}': {value}" for key, value in prompt.config["json_schema"].items()])
 
  # 使用字符串化的 JSON 模式编译提示
  system_message = prompt.compile(json_schema=json_schema_str)
 
  # 格式化为 OpenAI 消息
  messages = [
      {"role":"system","content": system_message},
      {"role":"user","content":story}
  ]
 
  # 获取额外配置
  model = prompt.config["model"]
  temperature = prompt.config["temperature"]
 
  # 执行 LLM 调用
  res = client.chat.completions.create(
    model = model,
    temperature = temperature,
    messages = messages,
    response_format = { "type": "json_object" },
    langfuse_prompt = prompt # 在追踪中捕获使用的提示版本
  )
 
  # 将响应解析为 JSON
  res = json.loads(res.choices[0].message.content)
 
  return res
```

### 执行它

```
# 感谢 ChatGPT 提供的故事
STORY = """
在一个充满活力的城市里，夜晚闪烁着霓虹灯光，喧嚣从未平息，住着一只名叫 Whisper 的孤独猫咪。喧闹声中，Whisper 有一天发现了一顶被遗弃的帽子。对她来说，这不是普通的配饰；它具有让她对任何旁观者都隐形的奇特力量。
现在拥有这种奇特力量的 Whisper，开始了一段意想不到的旅程。她成为了对不幸者——那些与她同样在寒冷夜晚中度过的无家可归者——的仁慈灵魂。曾经荒芜的夜晚变成了奇迹，因为那些最需要的人神秘地得到了温暖的餐食。没有人能看见她，但她的行动却说明了一切，使她成为了城市隐秘角落中的无名英雄。
随着她继续进行这神秘的善举，她发现了一个意想不到的奖励。她的心中开始燃起喜悦，这不是来自于隐形，而是来自于她的行动结果；那些她悄悄帮助的人脸上逐渐增多的笑容。Whisper 可能对世界来说仍然未被注意到，但在她的秘密善举中，她发现了真正的幸福。
"""
```

```
summary = summarize_story(STORY)
```

```
{'genre': '幻想',
 'keywords': ['孤独的猫',
  '隐形',
  '仁慈的灵魂',
  '无名英雄',
  '神秘的善举',
  '真正的幸福'],
 'key_content': '在一个充满活力的城市里，一只名叫 Whisper 的孤独猫咪发现了一顶被遗弃的帽子，这顶帽子具有使她隐形的力量，引导她成为对不幸者的仁慈灵魂和无名英雄。',
 'critic_score': 9,
 'main_character': 'Whisper',
 'critic_review_comment': "Whisper 从孤独到自我发现的旅程通过善举展开，这是一个温馨而迷人的故事，以其魔法元素和关于真正幸福的深刻信息吸引读者。"}
```

## 在 Langfuse 中查看追踪

由于我们使用了与 OpenAI SDK 的原生 Langfuse 集成，我们可以在 Langfuse 中查看追踪。

![在 Langfuse 中查看 OpenAI 函数的追踪](https://langfuse.com/images/docs/openai-functions-trace-with-prompt-management.png)

## 在 Langfuse 中迭代提示

我们现在可以在 Langfuse UI 中迭代提示，包括模型参数和函数调用选项，而无需更改代码或重新部署应用程序。

最后更新于 [入门](https://langfuse.com/docs/prompts/get-started "入门") [示例 Langchain (Py)](https://langfuse.com/docs/prompts/example-langchain "示例 Langchain (Py)")