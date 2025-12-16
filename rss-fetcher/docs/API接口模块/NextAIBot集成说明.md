## 目标

为 Next.js App Router 新增 `aibot` 模块，复用本仓库图书检索 API 的纯文本上下文，并使用兼容 OpenAI 的大模型（可自定义 `baseURL`、`apiKey`、`model` 等参数）。本文档提供端到端集成流程，便于复制到 Next.js 项目继续讨论与实现。

## 环境变量与依赖

1. 安装 AI SDK 及 OpenAI 兼容适配器
   ```bash
   npm install ai @ai-sdk/openai
   ```
2. 在 Next.js 项目根目录 `.env.local` 中新增
   ```
   AIBOT_LLM_BASE_URL=https://api.openai.com/v1
   AIBOT_LLM_API_KEY=sk-*****
   AIBOT_LLM_MODEL=gpt-4o-mini
   BOOK_API_BASE_URL=http://127.0.0.1:8000
   ```
   通过修改上述值即可自由切换至自建的 OpenAI 兼容服务。

## 服务器端：Route Handler

`app/api/aibot/route.ts`

```typescript
import { openai } from '@ai-sdk/openai'
import { streamText, StreamingTextResponse } from 'ai'

const bookApiBase = process.env.BOOK_API_BASE_URL!
const model = openai(process.env.AIBOT_LLM_MODEL!, {
  baseURL: process.env.AIBOT_LLM_BASE_URL,
  apiKey: process.env.AIBOT_LLM_API_KEY,
})

async function fetchContext(body: unknown) {
  const resp = await fetch(`${bookApiBase}/api/books/multi-query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...body,
      response_format: 'plain_text',
      plain_text_template: '【{title}】{highlights} - {rating}分',
    }),
  })
  if (!resp.ok) throw new Error(`Book API failed: ${resp.status}`)
  return resp.headers.get('content-type') === 'text/plain'
    ? await resp.text()
    : (await resp.json()).context_plain_text
}

export async function POST(req: Request) {
  const { messages, searchPayload } = await req.json()
  const context = await fetchContext(searchPayload)
  const systemPrompt =
    '你是图书推荐助手，请结合以下检索结果进行回答：\n' + context

  const result = await streamText({
    model,
    messages: [
      { role: 'system', content: systemPrompt },
      ...messages,
    ],
  })
  return new StreamingTextResponse(result.toAIStream())
}
```

- `searchPayload` 可选择 `text-search` 或 `multi-query` 输入结构，保持与 API 文档一致。
- `response_format=plain_text` 复用前文新增的纯文本能力，免去前端解析。
- 设置 `model = openai(..., { baseURL, apiKey })` 即可动态替换任意兼容实现。

## 客户端：`useChat` Hook

`app/aibot/chat-panel.tsx`

```tsx
'use client'

import { useChat } from 'ai/react'

export default function ChatPanel() {
  const { messages, input, handleInputChange, handleSubmit } = useChat({
    api: '/api/aibot',
    body: {
      searchPayload: {
        markdown_text: '## 主题\nAI 伦理',
        per_query_top_k: 8,
      },
    },
  })

  return (
    <form onSubmit={handleSubmit}>
      <div>
        {messages.map((m) => (
          <p key={m.id}>
            <strong>{m.role}:</strong> {m.content}
          </p>
        ))}
      </div>
      <input value={input} onChange={handleInputChange} />
      <button type="submit">发送</button>
    </form>
  )
}
```

- `useChat` 将用户问题连同预设的 `searchPayload` 一起提交到 `/api/aibot`。
- 如需根据对话上下文动态调整检索请求，可在客户端 `onSubmit` 时重新组装 `body.searchPayload`。

## 调用流程

1. Next.js 客户端将用户输入与选定主题打包发送到 `/api/aibot`。
2. Route Handler 请求图书检索 API，选择 `plain_text` 模式以获取 LLM 友好的上下文。
3. Handler 将纯文本上下文拼接进 `system` 消息，并调用 `streamText`。
4. 客户端通过 `useChat` 接收流式响应，实时渲染。

## 复用 `llm_hint`

若图书检索 API 响应 `metadata.llm_hint`，Route Handler 可读取该字段并在运行时覆写 `AIBOT_LLM_*` 配置，实现“一次请求切换一个 LLM 配置”的效果；默认保持 `.env.local` 中的基线配置即可。
