## 提示管理

使用 Langfuse 有效地**管理**和**版本化**您的提示。Langfuse 提示管理是一个**提示内容管理系统**（CMS）。

## 什么是提示管理？

**提示管理是在 LLM 应用程序中存储、版本化和检索提示的系统化方法。** 提示管理的关键方面包括版本控制、将提示与代码分离、监控、记录和优化提示，以及将提示与您的应用程序和其他工具集成。

## 为什么使用提示管理？

> 我不能直接在我的应用程序中硬编码我的提示并在 Git 中跟踪它们吗？是的，嗯……你可以，我们都这样做过。

使用 CMS 的典型好处在这里也适用：

- 分离：无需重新部署应用程序即可部署新提示。
- 非技术用户可以通过 Langfuse 控制台创建和更新提示。
- 快速回滚到提示的先前版本。
- 并排比较不同的提示版本。

平台优势：

- 在 [Langfuse 跟踪](https://langfuse.com/docs/tracing) 中跟踪提示版本的性能。

与其他实现相比的性能优势：

- 由于客户端缓存和异步缓存刷新，在首次使用提示后不会影响延迟。
- 支持文本和聊天提示。
- 通过 UI、SDK 或 API 进行编辑/管理。

## 提示工程常见问题解答

## Langfuse 提示对象

在 Langfuse 中带有自定义配置的示例提示
```
{
  "name": "movie-critic",
  "type": "text",
  "prompt": "作为一个 {{criticLevel}} 电影评论家，你喜欢 {{movie}} 吗？",
  "config": {
    "model": "gpt-3.5-turbo",
    "temperature": 0.5,
    "supported_languages": ["en", "fr"]
  },
  "version": 1,
  "labels": ["production", "staging", "latest"],
  "tags": ["movies"]
}
```

- `name`：在 Langfuse 项目中提示的唯一名称。
- `type`：提示内容的类型（`text` 或 `chat`）。默认值为 `text`。
- `prompt`：带有变量的文本模板（例如 `这是一个带有 {{variable}} 的提示`）。对于聊天提示，这是一个包含 `role` 和 `content` 的聊天消息列表。
- `config`：可选的 JSON 对象，用于存储任何参数（例如模型参数或模型工具）。
- `version`：整数，用于指示提示的版本。在创建新提示版本时，版本会自动递增。
- `labels`：[标签](https://langfuse.com/docs/prompts/#labels)，可用于在 SDK 中获取特定提示版本。
	- 在不指定标签的情况下使用提示时，Langfuse 将提供带有 `production` 标签的版本。
	- `latest` 指向最近创建的版本。
	- 您可以创建任何其他标签，例如用于不同环境（`staging`, `production`）或租户（`tenant-1`, `tenant-2`）。

## 工作原理

### 创建/更新提示

如果您已经有一个相同 `name` 的提示，则该提示将作为新版本添加。

### 使用提示

在运行时，您可以从 Langfuse 获取最新的生产版本。

### 与 Langfuse 跟踪链接（可选）

在 SDK 中将提示对象添加到 `generation` 调用中，以将 [Langfuse 跟踪](https://langfuse.com/docs/tracing) 中的生成链接到提示版本。此链接使您能够在 Langfuse UI 中直接按提示版本和名称（例如“movie-critic”）跟踪指标。每个提示版本的分数等指标可以提供有关提示修改如何影响生成质量的见解。如果使用了[回退提示](https://langfuse.com/docs/prompts/#fallback)，则不会创建链接。

目前在使用 LlamaIndex 集成时不可用。

### 回滚（可选）

当提示具有 `production` 标签时，SDK 将默认提供该版本。您可以通过在 Langfuse UI 中将 `production` 标签设置为先前版本来快速回滚到先前版本。

## 端到端示例

以下示例笔记本包括提示管理的端到端示例：

[示例 OpenAI 函数](https://langfuse.com/docs/prompts/example-openai-functions) [示例 Langchain (Python)](https://langfuse.com/docs/prompts/example-langchain) [示例 Langchain (JS/TS)](https://langfuse.com/docs/prompts/example-langchain-js)

我们还为我们的文档问答聊天机器人使用了提示管理，并使用 Langfuse 进行了跟踪。您可以通过注册[公共演示](https://langfuse.com/docs/demo)来获取项目的只读访问权限。

## 提示部署标签

标签可用于在 SDK 中获取特定提示版本。在[使用提示](https://langfuse.com/docs/prompts/#use-prompt)时不指定标签，Langfuse 将提供带有 `production` 标签的版本。`latest` 标签指向最近创建的版本。您可以创建任何其他标签，例如用于不同环境（`staging`, `production`）、租户（`tenant-1`, `tenant-2`）或实验（`prod-a`, `prod-b`）。

**如何为提示分配标签：**

## 提示组合性

<video src="https://customer-xnej9vqjtgxpafyk.cloudflarestream.com/6e9c25ba3d4c72363680af5dfb6a9bd2/manifest/video.m3u8"></video>

您可以在提示中使用简单的标签格式引用其他**文本**提示：

```
@@@langfusePrompt:name=PromptName|version=1@@@
```

或者使用标签而不是特定版本进行动态解析：

```
@@@langfusePrompt:name=PromptName|label=production@@@
```

在通过 Langfuse UI 创建提示时，您可以使用“添加提示引用”按钮将提示引用标签插入到您的提示中。

通过 SDK / API 获取时，这些标签会自动替换为引用的提示内容，使您能够：

- 创建可在多个提示中重用的模块化提示组件
- 在一个地方维护常见的指令、示例或上下文
- 当基础提示发生变化时，自动更新依赖提示

## 客户端 SDK 中的缓存

Langfuse 提示在 SDK 中从客户端缓存中提供。因此，**当从之前的使用中可用的缓存提示时，Langfuse 提示管理不会给您的应用程序增加任何延迟**。您可以选择在应用程序启动时预先获取提示，以确保缓存已填充（如下例所示）。

### 可选：在应用程序启动时预先获取提示

**为了确保您的应用程序在运行时永远不会遇到空缓存**（从而避免首次获取提示的初始延迟），您可以在应用程序启动时预先获取提示。这种预先获取将填充缓存，并确保在需要时提示随时可用。

*示例实现：*

### 可选：自定义缓存持续时间（TTL）

如果您希望减少 Langfuse 客户端的网络开销，可以配置缓存持续时间。默认缓存 TTL 为 60 秒。TTL 到期后，SDK 将在后台重新获取提示并更新缓存。重新获取是异步进行的，不会阻塞应用程序。

### 可选：禁用缓存

您可以通过将 `cacheTtlSeconds` 设置为 `0` 来禁用缓存。这将确保每次调用时都从 Langfuse API 获取提示。这建议用于非生产用例，您希望确保提示始终与 Langfuse 中的最新版本保持同步。

### 初始获取的性能测量（客户端缓存为空）

我们测量了以下代码段的执行时间，缓存完全禁用。

```
prompt = langfuse.get_prompt("perf-test")
prompt.compile(input="test")
```

在本地 jupyter 笔记本中使用 Langfuse 云进行 1000 次连续执行的结果（包括网络延迟）：

![性能图表](https://langfuse.com/_next/image?url=%2F_next%2Fstatic%2Fmedia%2Fprompt-performance-chart.3c3545c4.png&w=1200&q=75)

```
count  1000.000000
mean      0.178465 秒
std       0.058125 秒
min       0.137314 秒
25%       0.161333 秒
50%       0.165919 秒
75%       0.171736 秒
max       0.687994 秒
```

## 可选：保证可用性

💡

通常不需要实现这一点，因为它会增加应用程序的复杂性，而且 Langfuse API 的可用性很高。但是，如果您需要 100% 的可用性，可以使用以下选项。

Langfuse API 具有高可用性，并且提示在 SDK 中本地缓存，以防止网络问题影响您的应用程序。

但是，`get_prompt()` / `getPrompt()` 将在以下情况下抛出异常：

1. 没有可用的本地（新鲜或过期）缓存提示 -> 新应用程序实例首次获取提示
2. *并且* 网络请求失败 -> 网络或 Langfuse API 问题（重试后）

为了保证 100% 的可用性，有两个选项：

1. 在应用程序启动时预先获取提示，如果提示不可用则退出应用程序。
2. 提供一个 `fallback` 提示，在这些情况下使用。

### 选项 1：在应用程序启动时预先获取提示，如果不可用则退出

### 选项 2：回退

## 其他功能

- [提示管理 MCP 服务器](https://langfuse.com/docs/prompts/mcp-server)
- [提示 A/B 测试](https://langfuse.com/docs/prompts/a-b-testing)

## 常见问题解答

- [在 Langfuse 中将提示管理与跟踪链接](https://langfuse.com/faq/all/link-prompt-management-with-tracing)
[新建](https://github.com/orgs/langfuse/discussions/new/choose)