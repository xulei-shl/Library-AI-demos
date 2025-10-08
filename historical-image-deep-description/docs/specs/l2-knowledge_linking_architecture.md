## L2 知识关联模块技术文档

### 1. 模块概述

L2（第二层）知识关联模块的核心目标是将从文本中提取出的实体（如人名、地名、组织机构等），与外部权威知识库（如维基百科、维基数据）进行链接。该过程通过实体消歧（Disambiguation）实现，即从多个潜在的匹配项中，利用上下文信息和大型语言模型（LLM）的判断力，选择最正确的一个。

最终，模块会将链接成功的知识库URI和相关描述信息写回到指定的Excel列中，从而丰富原始数据。

### 2. 核心逻辑与执行流程

本模块采用分阶段（Phased Execution）的设计，通过 `main.py` 作为总入口进行统一编排。每个阶段都可以通过命令行参数独立或组合触发。

**数据流转路径:**

`Excel元数据` -> **[Phase 1: build]** -> `runtime/outputs/*.json` -> **[Phase 2: classify]** -> `runtime/outputs/*.json` (原地更新) -> **[Phase 3: link]** -> `runtime/outputs/*.json` (原地更新) -> **[Phase 4: write]** -> `Excel元数据`

**核心阶段说明:**

1.  **`build` (任务构建 - `task_builder.py`)**
    *   **输入**: Excel 文件中已有的 "关键词JSON" 和 "L1结构化JSON" 列。
    *   **处理**:
        *   从这两列中，根据 `config/settings.yaml` 的配置 (`l1_entity_fields`, `keywords_entity_fields`) 抽取实体（`label`）及其初步类型（`type`）。
        *   对实体进行去重和聚合，记录每个实体出现的行号（`rows`）和来源（`sources`）。
        *   为每一行数据生成一个独立的JSON文件（如 `2202_001.json`），存放在 `runtime/outputs/` 目录下。此文件包含了该行提取出的所有实体及其上下文提示（`context_hint`）。
    *   **输出**: `runtime/outputs/` 目录下的多个行级实体JSON文件。

2.  **`classify` (类型分类 - `type_classifier.py`)**
    *   **输入**: `runtime/outputs/` 下的行级JSON文件。
    *   **处理**:
        *   遍历每个JSON文件中的实体。
        *   无论实体有无 `type` 字段，都调用LLM（通过 `utils.llm_api.invoke_model`）根据实体的 `label` 和 `context_hint` 对其进行类型分类。
        *   将LLM返回的类型（如 `person`, `location`, `organization`）和置信度等元信息，原地更新到JSON文件中。
    *   **输出**: 更新了 `type` 字段的行级JSON文件。

3.  **`link` (知识链接 - `entity_processor.py`)**
    *   **输入**: `runtime/outputs/` 下经过 `classify` 阶段的行级JSON文件。
    *   **处理**:
        *   遍历每个JSON文件中的每个实体。
        *   根据 `config/settings.yaml` 中 `tools` 的配置，判断需要为该实体启用哪些外部知识库检索工具（如 `wikipedia`, `wikidata`）。
        *   通过 `tools.registry.get_tool()` 获取已注册的工具函数。
        *   调用工具函数（如 `search_wikipedia`, `search_wikidata`）进行检索，获取候选列表。
        *   将候选列表交由 `entity_matcher.judge_best_match()` 处理，该函数会再次调用LLM进行实体消歧，选出最佳匹配项。
        *   将匹配成功的结果（如 `wikipedia_uri`, `wikidata_uri`）或失败状态（`not_found`, `not_matched`）原地更新到JSON文件中。
    *   **输出**: 更新了知识链接信息的行级JSON文件。

4.  **`write` (结果写回 - `result_writer.py`)**
    *   **输入**: `runtime/outputs/` 下最终处理完成的行级JSON文件。
    *   **处理**:
        *   读取所有行级JSON文件。
        *   将每个实体及其关联的知识库链接，根据其来源行号（`row_id`）进行聚合。
        *   将聚合后的JSON字符串写回到原始Excel文件对应的 "L2知识关联JSON" 列中。
    *   **输出**: 更新了 "L2知识关联JSON" 列的Excel文件。

### 3. 公共函数调用 (`src/utils/`)

L2模块高度依赖 `src/utils/` 下的公共函数库，以确保代码的统一性和健壮性。

*   **`utils.llm_api.py`**:
    *   **核心函数**: `invoke_model()`
    *   **作用**: 所有与LLM的交互都必须通过此函数。它封装了API提供商选择（主/备）、密钥管理、请求重试、速率限制和标准化的日志记录。开发者无需关心底层的 `httpx` 或 `openai` SDK 调用细节。
*   **`utils.excel_io.py`**:
    *   **核心类**: `ExcelIO`
    *   **作用**: 提供了对Excel文件的稳定读写接口。它能处理文件备份、动态增删表头、按列名读写单元格等，避免了直接操作 `openpyxl` 的复杂性。
*   **`utils.logger.py`**:
    *   **核心函数**: `get_logger()`
    *   **作用**: 提供全局统一的日志记录器，支持控制台和文件输出，并采用结构化的 `key=value` 格式，便于后续分析。
*   **`utils.metadata_context.py`**:
    *   **核心函数**: `build_metadata_context()`
    *   **作用**: 根据配置从Excel的一行中提取多个元数据字段，并将其格式化为一个文本块。这个文本块作为重要的上下文提示（`context_hint`）被用于 `classify` 和 `link` 阶段的LLM调用中，以提高准确性。

### 4. 如何添加新的API检索工具（最佳实践）

遵循现有设计模式，可以轻松地添加一个新的外部API检索工具。下面我们以集成一个内部的“人物API”为例，展示详细步骤和最佳实践。

**目标**: 添加一个名为 `person_api` 的新工具，用于根据人名检索内部数据库。

**步骤如下:**

#### 第 1 步：创建工具实现文件

在 `src/core/l2_knowledge_linking/tools/` 目录下创建一个新的Python文件，命名为 `person_api_tool.py`。

#### 第 2 步：实现搜索函数

在新文件中，编写核心的搜索函数。该函数必须遵循**“工具契约”**，并采纳以下最佳实践：

*   **函数签名**: 必须符合 `def search_...(entity_label: str, lang: str, type_hint: Optional[str]) -> List[Dict[str, Any]]:` 的格式。
*   **配置驱动**: **严禁**在代码中硬编码URL、API密钥或任何敏感信息。所有配置都应通过 `load_settings()` 从 `config/settings.yaml` 文件加载。
*   **环境变量支持**: 对于API密钥这类敏感值，应支持从环境变量中解析，例如使用 `_resolve_env(tool_cfg.get("key"))`。
*   **标准化输出**: 函数应返回一个候选字典的列表 (`List[Dict]`)。即使API返回的数据结构各异，也应在工具内部将其转换为一个相对统一、干净的格式，方便下游的LLM消费。为每个候选结果提供 `id`, `label`, `description` 等关键字段是一个好习惯。
*   **健壮的错误处理与日志**: 使用 `try...except` 块捕获API请求或数据解析中可能出现的异常，并通过 `logger` 记录有意义的日志，包括成功和失败的状态。

**示例 (`person_api_tool.py`):**
```python
from typing import Any, Dict, List, Optional
import time
import httpx

# 导入公共库
from ....utils.logger import get_logger
from ....utils.llm_api import load_settings, _resolve_env

logger = get_logger(__name__)

def search_person_api(entity_label: str, lang: str = "zh", type_hint: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    调用内部的人物API检索实体。
    - 从 config/settings.yaml 读取 API URL 和 Key。
    - Key 支持环境变量引用（例如 `env:SHL_API_KEY`）。
    - 返回一个标准化的候选列表。
    """
    t0 = time.time()
    
    # 1. 加载配置 (最佳实践)
    try:
        settings = load_settings()
        tool_cfg = settings.get("tools", {}).get("person_api", {})
        api_url = tool_cfg.get("url")
        api_key = _resolve_env(tool_cfg.get("key", "")) # 解析环境变量
        limit = int(tool_cfg.get("limit", 5))
    except Exception as e:
        logger.error(f"person_api_tool_config_error err={e}")
        return []

    if not api_url or not api_key:
        logger.warning("person_api_tool_missing_config url_or_key_is_empty")
        return []

    # 2. 准备请求参数
    params = {"fname": entity_label, "key": api_key, "pageSize": limit}
    
    # 3. 发起HTTP请求 (最佳实践)
    try:
        with httpx.Client(timeout=httpx.Timeout(15.0)) as client:
            resp = client.get(api_url, params=params)
            resp.raise_for_status()
            raw_data = resp.json()
    except Exception as e:
        logger.warning(f"person_api_request_failed label={entity_label} err={e}")
        return []

    # 4. 解析并格式化返回结果 (最佳实践)
    items = raw_data.get("data")
    if not isinstance(items, list):
        return []

    results: List[Dict[str, Any]] = []
    for item in items:
        # 将API返回字段映射到我们内部的标准格式
        results.append({
            "id": item.get("uri"),
            "label": item.get("fname"),
            "description": item.get("briefBiography"),
            "speciality": item.get("speciality"),
            "source_url": item.get("uri"),
            "_raw": item # 保留原始数据
        })

    logger.info(f"person_api_search_ok label={entity_label} count={len(results)}")
    return results
```

#### 第 3 步：注册新工具

打开 `src/core/l2_knowledge_linking/tools/registry.py` 文件，导入并注册新的搜索函数。

**示例 (`registry.py`):**
```python
from typing import Callable, Dict, Optional

from .wikidata_tool import search_wikidata
from .wikipedia_tool import search_wikipedia
from .person_api_tool import search_person_api  # <-- 1. 导入新函数

TOOL_REGISTRY: Dict[str, Callable[..., object]] = {
    "wikidata": search_wikidata,
    "wikipedia": search_wikipedia,
    "person_api": search_person_api,  # <-- 2. 添加到字典
}

def get_tool(name: str) -> Optional[Callable[..., object]]:
    """获取工具函数；若未注册则返回 None。"""
    return TOOL_REGISTRY.get(name)
```

#### 第 4 步：更新配置文件

最后，打开 `config/settings.yaml` 文件，在 `tools` 部分为新工具添加配置。这是将代码与实际运行环境连接起来的关键一步。

**示例 (`settings.yaml`):**
```yaml
tools:
  # ... 已有工具

  # 新增人物API工具配置
  person_api:
    enabled: true
    # API的URL地址
    url: http://data1.library.sh.cn/persons/data 
    # API密钥，推荐使用环境变量引用
    key: "env:SHL_API_KEY"
    # 单次查询返回的最大结果数
    limit: 5 
```

同时，请确保在项目根目录的 `.env` 文件中定义了 `SHL_API_KEY`。

**.env 文件示例:**
```
SHL_API_KEY="YOUR_REAL_API_KEY_HERE"
```

完成以上步骤后，`link` 阶段将自动启用 `person_api` 工具。当处理一个实体时，如果 `person_api` 在配置中是启用的，`entity_processor` 就会调用 `search_person_api` 函数，将其返回的候选结果纳入LLM的消歧流程中。整个过程无需修改 `entity_processor` 或 `main` 模块的任何代码，展现了框架良好的扩展性。
