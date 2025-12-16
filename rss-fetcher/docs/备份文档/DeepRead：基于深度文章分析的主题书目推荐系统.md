# DeepRead：基于深度文章分析的主题书目推荐系统
**项目设计文档 (v1.0)**

## 1. 项目概述
本项目旨在构建一个自动化的内容策展系统。通过每日追踪特定 RSS 源，利用大语言模型（LLM）对高质量长文进行多阶段分析（初筛、深读、提取），并将非结构化的文章转化为结构化的“知识卡片”。

最终目标不是为了囤积文章，而是通过**周期性聚合分析**，识别出近期文章背后的共同“母题 (Mother Topics)”。**通过将这些母题与本地图书数据库进行语义关联，系统定期生成具有深层互文性的主题书单，实现**“从一篇好文，发现一本好书”**的价值闭环。

## 2. 系统架构与数据流 (Pipeline)

## 2. 系统架构与技术栈

### 2.1 技术栈
*   **开发语言**: Python 3.10+
*   **数据存储**: SQLite (存储元数据)
*   **向量检索**: ChromaDB
*   **LLM 接口**: OpenAI API
*   **RSS 解析**: `feedparser`
*   **向量化模型**: `text-embedding-3-small` 或 `bge-m3`

### 2.2 数据流架构 (Pipeline)

系统分为三个独立的执行阶段：

1.  **Ingest & Filter (每日运行)**：获取 RSS -> 清洗 -> **Agent 1 (初筛)** 。
2.  **Analyze & Extract (每日运行)**：读取初筛通过文章 -> **Agent 2 (深评)** -> 生成结构化 JSON -> 存入 SQLite。
3.  **Curate & Recommend (每周/月运行)**：提取本周 JSON -> **Agent 3 (聚合)** -> 识别母题 -> **混合检索 (Vector+SQL)** -> 生成书单。

---

## 3. 数据库设计 (SQLite Schema)

### 3.1 `books` 表 (基础书库)
*预处理阶段需将你的图书数据导入此表，并同步生成向量存入向量库。*

| 字段名         | 类型       | 说明                     |
| :------------- | :--------- | :----------------------- |
| `id`           | INTEGER PK | 自增主键                 |
| `isbn`         | TEXT       | 唯一标识                 |
| `title`        | TEXT       | 书名                     |
| `author`       | TEXT       | 作者                     |
| `summary`      | TEXT       | 内容简介                 |
| `toc`          | TEXT       | 目录 (Table of Contents) |
| `embedding_id` | TEXT       | 关联向量库的ID           |

### 3.2 `articles` 表 (文章仓库)
*存储 Agent 2 分析后的结果。*

| 字段名             | 类型       | 说明                                                      |
| :----------------- | :--------- | :-------------------------------------------------------- |
| `id`               | INTEGER PK | 自增主键                                                  |
| `url`              | TEXT       | 原始链接 (Unique)                                         |
| `title`            | TEXT       | 标题                                                      |
| `publish_date`     | DATETIME   | 发布时间                                                  |
| `status`           | TEXT       | `pending`(待初筛), `analyzed`(已分析), `rejected`(已拒绝) |
| `score`            | INTEGER    | Agent 2 打分 (0-100)                                      |
| `thematic_essence` | TEXT       | **关键字段**：用于聚合的母题本质描述 (Agent 2 生成)       |
| `json_data`        | JSON       | 存储完整的分析结果 (包含 tags, mentioned_books 等)        |

### 3.3 `curations` 表 (策展记录)
| 字段名         | 类型       | 说明                   |
| :------------- | :--------- | :--------------------- |
| `id`           | INTEGER PK | 自增主键               |
| `date_range`   | TEXT       | 例如 "2023-10-Week4"   |
| `mother_topic` | TEXT       | 识别出的母题           |
| `book_list`    | JSON       | 最终生成的书单及推荐语 |

---

## 4. 核心 Agent 提示词设计

### 4.1 Agent 1: 守门员 (The Filter)
*   **模型**: gpt-4o-mini
*   **输入**: 文章标题 + 开头 1000 字
*   **任务**: 快速剔除负面清单内容。

```python
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

### 4.2 Agent 2: 深度分析师 (The Analyst)
*   **模型**: gemini-2.5-pro
*   **输入**: 文章全文
*   **任务**: 评分、提取实体、生成“母题本质”。

```python
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

### 4.3 Agent 3: 策展人 (The Curator)
*   **模型**: gemini-2.5-pro
*   **输入**: 聚合后的 `thematic_essence` 列表 + 检索到的候选图书信息
*   **任务**: 聚类母题 -> 筛选图书 -> 生成推荐语。

*(注：此 Prompt 分为两步，先聚类，后推荐，详见下文逻辑)*

---

## 5. 核心业务逻辑 (Python 实现细节)

### 5.1 图书向量化预处理 (Pre-process)
在使用系统前，必须先建立图书的向量索引。

1.  遍历 SQLite `books` 表。
2.  构建 Embedding 文本：`text = f"书名: {title}\n作者: {author}\n简介: {summary}\n目录: {toc}"`
3.  调用 Embedding API 获取向量。
4.  存入 ChromaDB，Metadata 记录 `book_id`。

### 5.2 阶段三：聚合与推荐 (The Aggregation Workflow)

这是系统最复杂也是最有价值的部分，Python 伪代码逻辑如下：

```python
def run_weekly_curation():
    # 1. 获取本周高分文章的“母题本质”
    articles = db.query("SELECT thematic_essence FROM articles WHERE score > 80 AND date > last_week")
    essence_list = [a.thematic_essence for a in articles]
    
    # 2. LLM 聚类：识别核心母题
    # Prompt: "分析以下多段文本，归纳出共性的 1-2 个核心讨论母题。"
    mother_topic_desc = llm_cluster_themes(essence_list) 
    # 假设输出: "在技术加速时代重新寻找身体的感知力"
    
    # 3. 混合检索 (Hybrid Retrieval) 候选书目
    candidate_books = []
    
    # 3.1 路径 A: 向量检索 (语义关联)
    # 将 mother_topic_desc 转为向量，去 ChromaDB 搜 Top 10
    vector_results = vector_db.similarity_search(mother_topic_desc, k=10)
    candidate_books.extend(vector_results)
    
    # 3.2 路径 B: 显性引用 (从文章中直接提取)
    # 查询本周 articles 中 mentioned_books 字段出现频率最高的书
    direct_mentions = db.get_frequent_books(articles, limit=5)
    candidate_books.extend(direct_mentions)
    
    # 4. LLM 最终策展 (Rerank & Write)
    final_booklist = llm_curate_booklist(
        topic=mother_topic_desc,
        candidates=candidate_books # 包含书名、作者、简介
    )
    
    return final_booklist
```

### 5.3 Agent 3 的最终策展 Prompt (用于 Step 4)

```python
你是一位品味极佳的**资深阅读策展人**。
你正在策划一期主题书单，该书单基于对近期深度文章的分析而生成。

### 输入上下文
1. **核心母题 (Mother Topic)**：{mother_topic}
   *这是本期书单的灵魂，所有推荐语必须围绕此主题展开。*
2. **主导维度 (Tone)**：{primary_dimension}
   *请根据此维度调整行文风格（如：'愉悦身心'需感性优美，'激发思维'需犀利深刻）。*
3. **馆藏候选书目**：{candidate_books_json}
   *注意：列表中的书籍均已确认在我们的图书馆/书店中有库存。包含来源标记（文章提及或语义联想）。*

### 你的任务
请从提供的【馆藏候选书目】中精选 3-5 本质量最高、最能与“核心母题”形成深层对话的书籍，生成书单。
**严禁**推荐候选列表之外的书籍，因为我们没有库存。

### 撰写要求 (关键)
1. **筛选逻辑**：优先选择那些能对母题进行**延伸、反驳或深化**的书籍。
2. **推荐语 (Recommendation)**：
   - **不要**只写通用的书籍简介。
   - **必须**解释“为什么在探讨【{mother_topic}】时，这本书值得一读？”。强调它与母题的内在共鸣。
   - *示例*：如果母题是“消费主义”，推荐《工作、消费、新穷人》时，不要只说它是鲍曼的书，要说“本书从社会学角度，为我们刚才在文章中读到的‘买买买’焦虑提供了残酷的底层注脚……”

### 输出格式 (JSON Only)
{
    "curation_title": "<String, 书单标题>",
    "curation_intro": "<String, 导语>",
    "selected_books": [
        {
            "title": "<书名>",
            "author": "<作者>",
            "recommendation": "<String, 推荐语>"
        }
    ]
}
```

## 6. 关键优化点总结

1.  **成本控制**：通过 Agent 1 拦截垃圾信息；通过 Agent 2 将长文压缩为 `thematic_essence`，使得 Agent 3 的上下文开销极低。
2.  **语义检索**：引入向量数据库，解决了“文章讨论虚无主义”但“书名不含虚无主义”导致的检索失败问题。
3.  **数据闭环**：`thematic_essence` 既是 AI 理解文章的摘要，也是向量检索的 Query，实现了从非结构化文本到结构化检索的桥梁。
4.  **混合推荐**：既包含了文章作者显性推荐的书（可信度高），也包含了系统通过语义联想到的书（惊喜度高）。