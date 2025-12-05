# LLM评论重构开发文档

## 1. 概述
本文档旨在指导 `src/core/article_analyzer.py` 的重构工作，以实现 [DeepRead 项目文档](DeepRead：基于深度文章分析的主题书目推荐系统.md) 中定义的 "4.1 Agent 1: 守门员 (The Filter)" 和 "4.2 Agent 2: 深度分析师 (The Analyst)" 双 Agent 架构。

根据用户反馈及 [AGENTS.md](../AGENTS.md) 的代码工艺标准，我们将采用**高内聚、低耦合**的策略：
1.  **提示词分离**：将 Prompt 独立存储在 `prompts/` 目录下。
2.  **代码拆分**：将 Filter 和 Analyst 的逻辑拆分为独立的 Python 模块，由 `ArticleProcessor` 统一编排。

## 2. 提示词文件 (Prompts)

在 `prompts/` 目录下新建两个 Markdown 文件，分别存储两个 Agent 的提示词。

### 2.1 `prompts/article_filter.md` (Agent 1: 守门员)

```markdown
你是一个严格的内容初筛员。你的目标是为后续的深度分析（Agent 2）把关，剔除所有低价值内容。

### (X) 负面清单 (一票否决)
如果内容属于以下任一类别，请直接拒绝 (`pass: false`)：
1. **强时效资讯**：财报数据、股市行情、突发简讯、短期政策通知。
2. **纯粹营销**：软文、卖课、单纯的产品功能介绍、带货直播脚本。
3. **碎片化/低质**：无逻辑的备忘录、缺乏主线的段子合集、机器洗稿痕迹严重。
4. **枯燥晦涩**：未通俗化的纯代码、纯技术手册、格式化的行政公文。

### (O) 潜在价值判断 (宽松门槛)
如果文章**看起来可能**具备以下任一特质（无需确信，只要有潜力），请放行 (`pass: true`)：
- 具有文学性或审美感 (愉悦身心)
- 提供了独特的个人或群体视角 (开阔眼界)
- 包含逻辑推演或批判性观点 (激发思维)
- 系统性地整理了某个知识点 (了解新知)

### 输出格式 (JSON Only)
{
    "pass": <Boolean>,
    "reason": "<String, 拒绝理由(如'纯营销内容')或放行理由(如'具备独特视角的社会观察')>"
}
```

### 2.2 `prompts/article_analysis.md` (Agent 2: 深度分析师)

```markdown
你是一位拥有百科全书式知识储备的**独立书店主理人**。你的任务是深度阅读文章，将其转化为结构化的知识资产，以便后续进行主题书单策展。

### (1) 评分标准：四大原则
请基于以下维度对文章打分（0-100）：
1. **愉悦身心**：具有文学美感，提供情感慰藉或生活美学洞察。
2. **开阔眼界**：提供跨文化/跨群体视角，揭示人类经验的多样性。
3. **激发思维**：挑战固有观念，逻辑严密，具备批判性思维。
4. **了解新知**：系统性介绍领域知识，有助于构建认知框架。

### (2) 核心任务
1. **评分与分类**：打分并选出最符合的一个原则。
2. **提取书籍**：提取文中明确提及的书籍（非作者随口一提，而是有实质引用的）。
3. **撰写摘要 (Summary)**：100字以内，**给用户看**。通俗概括文章讲了什么故事或观点。
4. **提炼母题本质 (Thematic Essence)**：300字左右，**给搜索引擎看**。
   - *关键要求*：剥离具体的人名、地名、时间。提炼文章探讨的抽象概念、底层逻辑、哲学思考或社会学现象。
   - *目的*：这段文字将被转化为向量，用于在图书馆中检索“精神内核相似”的书籍。
   - *示例*：不要写“张三在公园散步治好了焦虑”，要写“探讨现代都市生活中的注意力异化，以及通过重建与物理世界的感官连接来对抗存在主义虚无”。

### (3) 输出格式 (JSON Only)
{
  "score": <0-100>,
  "primary_dimension": "<四大原则之一>",
  "reason": "<简短评分理由>",
  "summary": "<给用户看的通俗摘要>",
  "thematic_essence": "<给向量库看的深度母题>",
  "tags": ["<Tag1>", "<Tag2>"],
  "mentioned_books": [
    {"title": "<书名>", "author": "<作者>", "context": "<提及时的上下文简述>"}
  ]
}
```

## 3. 配置变更 (`config/llm.yaml`)

修改 `config/llm.yaml`，新增任务配置并引用上述 Prompt 文件。

```yaml
tasks:
  # ... 原有任务 ...

  # Agent 1: 守门员
  article_filter:
    provider_type: "text" # 使用 text provider (oneapi/cerebras)
    temperature: 0.3
    prompt:
      type: md
      source: "prompts/article_filter.md"
    json_repair:
      enabled: true
      output_format: "json"
    langfuse:
      enabled: true
      name: "文章初筛"
      tags: ["filter"]

  # Agent 2: 深度分析师
  article_analysis:
    provider_type: "text"
    temperature: 0.5
    prompt:
      type: md
      source: "prompts/article_analysis.md"
    json_repair:
      enabled: true
      output_format: "json"
    langfuse:
      enabled: true
      name: "文章深度分析"
      tags: ["analysis"]
```

## 4. 代码重构

### 4.1 目录结构调整

新建 `src/core/analysis/` 目录，用于存放拆分后的模块。

```
src/core/
├── analysis/           # [NEW] 分析模块包
│   ├── __init__.py
│   ├── filter.py       # [NEW] Agent 1 实现
│   └── analyst.py      # [NEW] Agent 2 实现
├── article_analyzer.py # [MODIFY] 编排入口 (Facade)
...
```

### 4.2 `src/core/analysis/filter.py`

实现 `ArticleFilter` 类，专注于初筛逻辑。

```python
from src.utils.llm.client import UnifiedLLMClient
# ... imports

class ArticleFilter:
    def __init__(self, task_name: str = "article_filter"):
        self.llm_client = UnifiedLLMClient()
        self.task_name = task_name

    def filter(self, title: str, content: str) -> Dict[str, Any]:
        # 构造 Input (Title + 前 1000 字符)
        # 调用 LLM
        # 解析返回结果
        pass
```

### 4.3 `src/core/analysis/analyst.py`

实现 `ArticleAnalyst` 类，专注于深度分析逻辑。

```python
from src.utils.llm.client import UnifiedLLMClient
# ... imports

class ArticleAnalyst:
    def __init__(self, task_name: str = "article_analysis"):
        self.llm_client = UnifiedLLMClient()
        self.task_name = task_name

    def analyze(self, content: str) -> Dict[str, Any]:
        # 构造 Input (Full Text, 注意截断)
        # 调用 LLM
        # 解析返回结果
        pass
```

### 4.4 `src/core/article_analyzer.py`

重构 `ArticleProcessor` 类，作为协调者 (Orchestrator)，调用上述两个组件。

```python
from src.core.analysis.filter import ArticleFilter
from src.core.analysis.analyst import ArticleAnalyst

class ArticleProcessor:
    def __init__(self):
        self.filter_agent = ArticleFilter()
        self.analyst_agent = ArticleAnalyst()

    def analyze_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        # 1. 提取内容
        # 2. 调用 self.filter_agent.filter()
        # 3. 根据 filter 结果决定是否继续
        # 4. 如果通过，调用 self.analyst_agent.analyze()
        # 5. 合并结果并返回
        pass
```

## 5. 执行计划
1.  创建 `prompts/article_filter.md` 和 `prompts/article_analysis.md`。
2.  更新 `config/llm.yaml`。
3.  创建 `src/core/analysis/` 目录及 `__init__.py`。
4.  创建 `src/core/analysis/filter.py`。
5.  创建 `src/core/analysis/analyst.py`。
6.  重构 `src/core/article_analyzer.py`。
7.  运行测试/验证。
