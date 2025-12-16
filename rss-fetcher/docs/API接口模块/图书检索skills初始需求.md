### 1. 架构设计：Skill 如何与本地环境交互

Claude Skill 本质上是一套“指令 + 脚本”。在这个场景下，Skill 充当**编排者（Orchestrator）**的角色。

*   **服务端 (Server)**: 你之前设计的 `FastAPI` (运行在 `localhost:8000`)。
*   **工具层 (Tools)**:
    *   `api_client.py` (Skill自带脚本): 用于向本地 API 发送 HTTP 请求。
    *   `DuckDuckGo MCP`: 用于联网获取外部书评/背景信息。
*   **大脑 (Skill.md)**: 定义何时用简单检索，何时用深度检索，以及如何处理“人在环中（Human-in-the-loop）”的交互。

---

### 1. 增强型目录结构

```text
local-book-researcher/
├── Skill.md                 # 核心逻辑：定义模式切换与工作流编排
├── scripts/
│   └── book_api_client.py   # 调用本地 FastAPI (text-search & multi-query)
└── resources/               # 存放核心提示词文件
    ├── article_analysis.md        # 对应：单篇文档分析逻辑
    ├── article_cross_analysis.md  # 对应：多文档交叉分析逻辑
    ├── recommendation_intro.md    # 对应：最终推荐导语生成逻辑
    └── simple_search_prompt.md    # 对应：简单检索的回复逻辑
```

---

### 2. 核心定义文件：`Skill.md`

这个文件现在扮演“工作流引擎”的角色，明确规定了不同模式下的 Prompt 调用顺序。

```markdown
---
name: Local Book Researcher
description: 本地智能图书检索专家。支持简单检索模式，以及包含“搜索-分析-草稿-迭代-执行”闭环的深度研究模式。
dependencies: python>=3.8, requests
---

## 模式选择逻辑
当用户输入问题后，Claude 必须首先判断模式：
- **简单检索**：用户询问具体书籍、特定作者或简单的关键词查询。
- **深度研究**：用户问题模糊、涉及跨学科概念、需要最新背景信息或明确要求“深度搜索”。

---

## 模式 A：简单检索 (Simple Search)
1. **API 调用**：调用 `scripts/book_api_client.py simple "{query}"` 获取本地图书数据。
2. **提示词应用**：读取 `resources/simple_search_prompt.md`。
3. **输出**：根据提示词要求，结合 API 返回的 JSON 数据，直接生成回答。

---

## 模式 B：深度研究 (Deep Research Workflow)
必须严格按照以下顺序执行，不得跳过：

### Step 1: 外部信息采集 (DuckDuckGo)
- 使用 `duckduckgo_search` 工具搜索与用户问题相关的最新文章、深度评论或学术背景。
- 至少获取 3-5 个高质量结果的摘要或全文。

### Step 2: 单篇分析 (article_analysis)
- **提示词应用**：针对 Step 1 获取的每一篇文章，读取 `resources/article_analysis.md`。
- **操作**：提取文章中的核心观点、关键书籍提及和研究维度。

### Step 3: 交叉分析与草稿生成 (article_cross_analysis)
- **提示词应用**：读取 `resources/article_cross_analysis.md`。
- **操作**：整合信息，生成一份 **Markdown 格式的“检索草案”**（包含检索主题、核心关键词、背景上下文）。
- **关键动作**：将此草案完整展示给用户。

### Step 4: 人在环交互与迭代 (Iterative Loop)
**此步骤是一个循环节点，直到用户明确“确认”为止。**

根据用户的反馈，执行以下分支逻辑：

#### 分支 A：用户提出修改意见 (Refine)
- **触发条件**：用户说“把关键词 X 换成 Y”、“增加关于 Z 的权重”、“太宽泛了，聚焦在...”。
- **操作**：
    1. 理解用户的修改意图。
    2. 保持 `article_cross_analysis` 定义的结构格式。
    3. **修改草案内容**。
    4. **重新展示**修改后的 Markdown 草案。
    5. **返回** Step 4 开头，继续等待用户确认。

#### 分支 B：用户要求重新调研 (Restart/Re-search)
- **触发条件**：用户说“这个方向不对”、“我想找的是另一个话题”、“重新搜一下...”。
- **操作**：
    1. 清空当前草案上下文。
    2. 根据用户的新指令，**跳转回 Step 1** (外部信息采集)。

#### 分支 C：用户确认 (Confirm)
- **触发条件**：用户说“可以”、“没问题”、“执行”、“开始检索”。
- **操作**：
    1. **锁定**当前版本的 Markdown 草案。
    2. **跳转至 Step 5**。

### Step 5: 本地深度检索 (Execution)
- **前置检查**：确保草案已获得用户（分支 C）的明确确认。
- **API 调用**：调用 `scripts/book_api_client.py deep "{final_markdown_draft}"`。
- **说明**：将最终定稿的 Markdown 文本传给本地 API 进行多路检索。

### Step 6: 最终合成 (recommendation_intro)
- **提示词应用**：读取 `resources/recommendation_intro.md`。
- **操作**：
    1. 获取 API 返回的书籍列表。
    2. 结合 Step 3/4 中积累的调研背景。
    3. 生成深度推荐导语。

---

## 交互注意事项
1. **草稿可见性**：每次修改草案后，必须将完整的 Markdown 内容打印出来，以便用户检查。
2. **拒绝执行**：如果用户未确认草案直接要求推荐书籍，必须礼貌拒绝，并引导其先确认检索方向：“为了保证检索精度，请先确认上述检索草案是否符合您的预期。”
```

---

### 3. 提示词文件示例 (`resources/`)

你需要确保这些文件内容与你的项目逻辑一致。例如：

**`resources/article_cross_analysis.md`**:
> "你现在的任务是整合多篇关于 [主题] 的文章分析。请识别出 3 个最适合用于图书检索的子维度，并以 Markdown 格式输出，包含：#检索主题、##核心关键词、##背景上下文。"

**`resources/recommendation_intro.md`**:
> "你是一个资深书评人。请结合前期的深度调研背景，为以下检索到的图书编写一段引人入胜的推荐导语。导语需体现为什么这些书能解决用户最初提出的 [问题]。"

---

### 4. 脚本适配：`scripts/book_api_client.py`

为了支持两种模式，脚本需要能够处理不同的端点：

```python
import requests
import sys

def call_api(endpoint, payload):
    url = f"http://localhost:8000/api/books/{endpoint}"
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        # 根据 API 定义，优先返回 plain_text 供 LLM 直接读取
        return data.get("context_plain_text") or data
    except Exception as e:
        return f"API Error: {str(e)}"

if __name__ == "__main__":
    mode = sys.argv[1]
    input_text = sys.argv[2]

    if mode == "simple":
        # 调用文本相似度检索
        print(call_api("text-search", {"query": input_text, "response_format": "plain_text"}))
    elif mode == "deep":
        # 调用多子查询检索（接收 Markdown）
        print(call_api("multi-query", {"markdown_text": input_text, "response_format": "plain_text"}))
```

---

### 5. 方案总结与优势

1.  **明确的 SOP**：`Skill.md` 不再只是简单的描述，而是一个严格的 **SOP（标准作业程序）**。Claude 会像执行脚本一样一步步走完：搜索 -> 分析 -> 交叉分析 -> 停顿 -> 检索 -> 总结。
2.  **提示词解耦**：通过 `resources/` 引用，你可以随时修改提示词（Prompt Engineering）而不需要重新打包 Skill 的核心逻辑。
3.  **人在环中（HITL）的强制性**：在 `Skill.md` 中明确了“必须等待用户反馈”，这解决了 AI 容易“自作主张”直接跑完流程的问题。
4.  **接口隔离**：简单检索走 `text-search`（快、直接），深度检索走 `multi-query`（慢、精准、依赖 Markdown），完美适配你的 API 设计。