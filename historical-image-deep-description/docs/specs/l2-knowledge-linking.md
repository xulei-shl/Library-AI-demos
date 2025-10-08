# L2 知识关联 (Knowledge Linking) - 需求规格说明书

**文档版本**: 0.3
**日期**: 2025年10月3日
**撰写人**: Gemini

---

## 1. 概述 (Overview)

`L2 知识关联 (Knowledge Linking)` 模块是历史图像多维深度描述框架的第二层。其核心目标是将 L0 和 L1 阶段从图像和元数据中提取出的非结构化实体（如人名、地名、作品名等），链接到权威知识库（包括外部公共知识库和机构内部数据库）中的精确条目，并获取其唯一的标识符（URI）。

本模块通过一个结构化的处理流程，将零散的文本实体转化为机器可读的知识节点，为后续构建知识图谱和实现深度语境阐释（L3）奠定坚实的数据基础。

## 2. 核心目标 (Core Objectives)

- **处理核心实体类型**：支持对以下类型的实体进行链接：`person`、`place`、`architecture`、`organization`、`work`、`event`。
- **整合外部知识库**：优先集成 Wikidata 和 Wikipedia 作为外部知识源，快速实现端到端的数据关联流程。
- **整合内部 API**：在后续阶段，以“工具调用”模式，集成机构内部的权威数据库 API，实现内部优先的实体锚定。
- **实现智能消歧**：利用 LLM，基于原始元数据上下文，对 API 返回的多个候选结果进行智能判断和选择，确保链接的准确性。
- **结构化数据输出**：将获取到的外部及内部 URI，与原始实体信息一同组织成统一的 JSON 格式，并**将其更新回一个新的 `L2知识关联JSON` 列中**。
- **高效去重**：在处理前对来自多个源的实体进行去重，避免重复的 API 和 LLM 调用。

## 3. 核心架构设计 (Core Architectural Design)

为确保项目具备良好的可扩展性和可维护性，尤其是在未来无缝集成内部 API，我们确立以下核心设计原则：

1.  **数据源客户端模块化 (Modular API Clients)**：
    *   使用低耦合高内聚的插件化架构 (Pluggable Architecture)
    *   在 `src/core/l2_knowledge_linking/api_clients.py` 中，为每一个知识源（如 Wikidata, Wikipedia, 内部 API）实现一个独立的客户端类或一组函数。
    *   所有客户端应遵循统一的接口约定，例如，都包含一个 `search(entity_label: str)` 方法，并返回一个结构一致的候选结果列表。
    *   `entity_processor.py` 模块将不直接调用具体的 API 库，而是通过一个可配置的客户端列表进行迭代。初始阶段，该列表包含 `[WikidataClient, WikipediaClient]`；第四阶段，将轻松扩展为 `[InternalApiClient, WikidataClient, WikipediaClient]`，无需修改核心处理逻辑。
    
2.  **通用消歧提示词 (Generic Disambiguation Prompt)**：
    *   我们将设计一个**单一且通用**的系统提示词 `l2_entity_disambiguation.md`，其核心任务是：“根据上下文，从一组来源各异的候选数据中，为每个来源选择最匹配的一项”。
    *   该提示词是**与数据源无关的**。我们将通过结构化的用户输入，将所有 API（无论是 Wiki 还是内部 API）返回的候选结果动态地注入到用户提示词中。这种方式使得消歧逻辑保持稳定，无论未来接入多少新的数据源。

3.  **原始数据持久化 (Raw Data Persistence)**：
    *   在对实体进行关联处理时，所有从外部或内部 API 获取的**完整、原始的返回结果**都将被保存下来。
    *   这些原始数据将存储在最终输出 JSON 的一个特定保留字段中（如 `_raw_api_responses`），与提炼后的核心 URI 分开。这确保了数据的可追溯性，并为未来可能的需求变更（如需提取更多字段）提供了便利，避免了重复的网络请求。

## 4. 开发计划与工作流 (Development Plan & Workflow)

本模块的开发与执行将严格遵循以下顺序。

---

### **步骤零：行级前置检查 (Step 0: Row-level Pre-check)**

这是处理 Excel 表格中**每一行**的入口和守卫。此步骤在 `main.py` 的主循环中执行。

1.  **检查目标列**：检查当前行是否存在 `L2知识关联JSON` 列。
2.  **检查值**: 如果列存在，检查其单元格是否已有非空值。
3.  **决策**：
    *   如果已有值，则立即记录日志（例如 `INFO: Row X already processed, skipping.`），并**跳过该行的所有后续处理**，直接进入下一行。
    *   如果列不存在或值为空，则继续执行步骤一。

---

### **第一阶段：构建统一实体任务列表 (Step 1: Build Unified Entity Task List)**

此阶段的目标是：从当前行原始的两列 JSON (`关键词JSON`, `L1结构化JSON`) 中采集信息，生成一个去重后的、包含初步类型信息的实体对象列表，作为后续处理的“任务清单”。

1.  **初始化实体映射 (Initialize Entity Map)**：创建一个空的字典（`unique_entity_map`）。
2.  **优先处理 `L1结构化JSON`**：遍历此 JSON，利用其明确的字段来预设实体类型。
3.  **补充处理 `关键词JSON`**：遍历此 JSON，对 `unique_entity_map` 中不存在的实体进行补充，类型设为 `null`。
4.  **生成任务列表 (Generate Task List)**：将 `unique_entity_map` 的所有值转换为一个列表（`task_list`）。

---

### **第二阶段：外部知识关联 (Step 2: External Knowledge Linking)**

此阶段的核心是遍历任务列表，调用已配置的外部知识源客户端（初期为 Wikidata 和 Wikipedia）来丰富实体数据。

对 `task_list` 中的每一个 `entity_obj` 对象，执行以下操作：

1.  **初始化节点 (Initialize Nodes)**：为对象添加待填充的字段：`wikidata_uri: null`, `wikipedia_uri: null`, `status: "PENDING"`, `_raw_api_responses: {}`。
2.  **类型分类 (Type Classification)**：若 `entity_obj["type"]` 为 `null`，调用 LLM 进行分类。
3.  **迭代 API 调用 (Iterative API Invocation)**：
    *   遍历**已配置的 API 客户端列表**（初始为 Wikidata 和 Wikipedia 客户端）。
    *   对每个客户端，调用其 `search()` 方法。
    *   将每个客户端返回的**完整原始结果**存入 `entity_obj["_raw_api_responses"]` 中，以客户端名称为键（例如 `{"wikidata": [...], "wikipedia": {...}}`）。
4.  **统一结果消歧 (Unified Result Disambiguation)**：
    *   将 `_raw_api_responses` 中收集到的所有候选结果，连同原始元数据上下文，一同格式化后提交给**通用的 `l2_entity_disambiguation.md` 提示词**。
    *   LLM 的任务是从每个来源的候选结果中，分别选择最匹配的一项，并返回其核心标识符。
5.  **原地更新 (In-place Update)**：
    *   将 LLM 消歧后返回的 `wikidata_uri` 和 `wikipedia_uri`，以及处理状态 (`SUCCESS_WIKI`, `NOT_FOUND` 等) 更新回当前的 `entity_obj` 对象中。**`_raw_api_responses` 字段保持不变**。

---

### **第三阶段：聚合与写回 (Step 3: Aggregation and Write-back)**

此阶段的目标是将处理完成的数据注入原始 `L1结构化JSON` 并写回到 Excel 的新列中。

1.  **加载原始JSON (Load Original JSON)**：读取并解析当前行 `L1结构化JSON` 列的内容。
2.  **注入关联数据 (Inject Linked Data)**：遍历已丰富的 `task_list`，将每个 `entity_obj` 的信息（包括 `_raw_api_responses`）合并到 `L1结构化JSON` 对象的对应条目中。
3.  **序列化与写回 (Serialize and Write Back)**：将修改后的 `L1结构化JSON` 对象转换回 JSON 字符串，并将其写回到当前行的 `L2知识关联JSON` 列中（若列不存在则新建）。

---

### **第四阶段：集成内部 API (Step 4: Internal API Integration)**

此阶段将充分利用已建立的模块化架构，轻松实现扩展。

1.  **新增客户端**: 在 `api_clients.py` 中实现 `InternalApiClient`，遵循统一接口。
2.  **更新配置**: 在 `entity_processor.py` 的配置中，将 API 客户端列表更新为 `[InternalApiClient, WikidataClient, WikipediaClient]`。
3.  **自动适配**: 核心的调用和消歧流程**无需重大修改**。系统将自动调用新增的内部 API，将其结果存入 `_raw_api_responses`，并一同送入通用的消歧 LLM 进行判断。
4.  **更新输出**: `entity_obj` 中将新增 `shl_uri` 字段，状态也将更丰富。最终写回的 JSON 自然地包含了所有来源的数据。

## 5. 数据结构 (Data Structures)

### 5.1. 中间数据结构：任务列表项 (处理后)

```json
{
  "label": "欧阳予倩",
  "type": "person",
  "shl_uri": "http://data.library.sh.cn/entity/person/c1b5i9m4cdolh5ny",
  "wikidata_uri": "https://www.wikidata.org/wiki/Q10931360",
  "wikipedia_uri": "https://zh.wikipedia.org/wiki/%E6%AC%A7%E9%98%B3%E4%BA%88%E7%BE%BD",
  "status": "SUCCESS_BOTH",
  "_raw_api_responses": {
    "wikidata": [
      {
        "id": "Q619032",
        "label": "Ouyang Yuqian",
        "description": "Chinese playwright...",
        "aliases": ["Ouyang Liyuan"]
      },
      {
        "id": "Q124624128",
        "description": "cultural heritage of China..."
      }
    ],
    "wikipedia": {
      "title": "欧阳予倩",
      "summary": "欧阳予倩（1889年5月12日—1962年9月21日），原名欧阳立袁...",
      "url": "https://zh.wikipedia.org/wiki/%E6%AC%A7%E9%98%B3%E4%BA%88%E7%BE%BD",
      "full_text": "..."
    },
    "internal_api": {
      "id": "c1b5i9m4cdolh5ny",
      "name": "欧阳予倩",
      "bio": "..."
    }
  }
}
```

### 5.2. 输出数据结构：`L2知识关联JSON` (最终示例)

```json
"{
  "location": {
    "label": "上海",
    "type": "place",
    "shl_uri": "http://data.library.sh.cn/entity/place/mock_shanghai_id",
    "wikidata_uri": "https://www.wikidata.org/wiki/Q8686",
    "wikipedia_uri": "https://zh.wikipedia.org/wiki/%E4%B8%8A%E6%B5%B7",
    "status": "SUCCESS_BOTH",
    "_raw_api_responses": { ... }
  },
  "persons": [
    {
      "name": "欧阳予倩",
      "duty": "导演",
      "type": "person",
      "shl_uri": "http://data.library.sh.cn/entity/person/c1b5i9m4cdolh5ny",
      "wikidata_uri": "https://www.wikidata.org/wiki/Q10931360",
      "wikipedia_uri": "https://zh.wikipedia.org/wiki/%E6%AC%A7%E9%98%B3%E4%BA%88%E7%BE%BD",
      "status": "SUCCESS_BOTH",
      "_raw_api_responses": { ... }
    }
  ]
}"
```

## 6. 依赖与实现细节 (Dependencies & Implementation Details)

- **代码复用**:
  - `src/utils/llm_api.py`: 用于所有与 LLM 的交互。
  - `src/utils/excel_io.py`: 用于读写 `metadata.xlsx` 文件。
  - `src/utils/metadata_conlabel.py`: 用于构建初始元数据上下文。
  - `src/utils/logger.py`: 用于记录详细的工作流日志。
- **新增依赖 (New Dependencies)**:
  - `langchain-community`: 用于集成 Wikidata 工具。
  - `wikipedia-api`: 用于直接调用 Wikipedia API。
- **新增提示词 (Prompts)**:
  - `src/prompts/l2_entity_classification.md`: 用于实体类型分类。
  - `src/prompts/l2_entity_disambiguation.md`: **(核心)** 一个通用的、与数据源无关的系统提示词，用于从多个来源的候选结果中进行综合消歧。
- **模块职责 (`src/core/l2_knowledge_linking/`)**:
  - `main.py`: **负责步骤零的行级前置检查**和遍历。
  - `task_builder.py`: 负责步骤一。
  - `entity_processor.py`: 负责步骤二和四的核心处理逻辑，**调用配置好的 API 客户端列表**。
  - `api_clients.py`: **实现模块化的数据源客户端**，每个客户端遵循统一接口。
  - `result_writer.py`: 负责步骤三。
