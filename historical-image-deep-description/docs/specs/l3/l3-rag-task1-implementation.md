# L3-RAG任务1技术实现规格

## 状态：Proposal

## 目标摘要

实现 L3 模块的第一个任务：**基于实体标签的 RAG 知识库检索**。该任务从 L2 阶段输出的 JSON 文件中提取实体的 `label`、`type`、`context_hint` 三个字段，调用 Dify 知识库检索接口，并将结果格式化存储回实体节点。

## 详细技术规格

### 数据提取逻辑

#### 实体字段提取
从每个实体节点提取以下三个字段：

```python
def extract_entity_fields(entity: dict, row_id: str, metadata: dict) -> EntityFields:
    """
    提取实体的关键字段用于 RAG 检索
    
    Returns:
        EntityFields: 包含 label, type, context_hint 的数据类
    """
    label = entity.get("label", "")
    entity_type = entity.get("type", "")
    
    # 构建 context_hint：标准化的元数据格式
    context_hint = build_context_hint(row_id, metadata)
    
    return EntityFields(
        label=label,
        type=entity_type, 
        context_hint=context_hint
    )

def build_context_hint(row_id: str, metadata: dict) -> str:
    """
    构建标准化的 context_hint 字符串
    格式与现有样例保持一致
    """
    title = metadata.get("title", "")
    desc = metadata.get("desc", "")
    persons = metadata.get("persons", "")
    topic = metadata.get("topic", "")
    
    return f"""[元数据]
- 编号: {row_id}
- 题名: {title}
- 说明: {desc}
- 相关人物: {persons}
- 所属专题: {topic}"""
```

#### 任务执行状态检查
```python
def should_skip_entity(entity: dict, task_name: str) -> bool:
    """
    检查实体是否已执行过指定的 RAG 任务
    
    Args:
        entity: 实体节点数据
        task_name: 任务名称，如 "entity_label_retrieval"
        
    Returns:
        bool: True 表示应跳过，False 表示需要执行
    """
    rag_field = f"l3_rag_{task_name}"
    if rag_field in entity:
        executed_meta = entity[rag_field].get("meta", {})
        if executed_meta.get("executed_at"):
            logger.info(f"实体已执行过任务 entity={entity.get('label')} task={task_name}")
            return True
    return False
```

### Dify API 集成

#### API 客户端设计
```python
class DifyClient:
    """Dify 知识库检索客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.dify.ai/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = self._create_session()
    
    def query_knowledge_base(self, 
                           label: str, 
                           entity_type: str, 
                           context_hint: str,
                           conversation_id: str = "",
                           user_id: str = "l3_rag_user") -> DifyResponse:
        """
        查询 Dify 知识库
        
        Args:
            label: 实体标签
            entity_type: 实体类型  
            context_hint: 上下文提示
            conversation_id: 对话ID（可选）
            user_id: 用户ID
            
        Returns:
            DifyResponse: 封装的响应对象
        """
        # 构建查询文本：将三个字段原样传递给 Dify
        query_text = f"label: {label}\ntype: {entity_type}\ncontext_hint: {context_hint}"
        
        payload = {
            "inputs": {},
            "query": query_text,
            "response_mode": "blocking",
            "conversation_id": conversation_id,
            "user": user_id
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/chat-messages",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return self._parse_response(response.json())
            
        except requests.exceptions.Timeout:
            return DifyResponse(status="error", error="请求超时")
        except requests.exceptions.RequestException as e:
            return DifyResponse(status="error", error=f"网络错误: {str(e)}")
        except Exception as e:
            return DifyResponse(status="error", error=f"未知错误: {str(e)}")
```

#### 响应状态解析
```python
@dataclass
class DifyResponse:
    """Dify API 响应封装"""
    status: str  # "success" | "not_found" | "not_relevant" | "error"
    content: str = ""
    error: str = ""
    response_id: str = ""
    raw_response: dict = None

def _parse_response(self, response_data: dict) -> DifyResponse:
    """
    解析 Dify 响应并判断状态
    
    根据需求文档，需要识别四种状态：
    1. 没有检索到相关信息
    2. 回答不相关  
    3. 正确返回结果
    4. 未返回等各种异常错误
    """
    try:
        answer = response_data.get("answer", "").strip()
        response_id = response_data.get("id", "")
        
        if not answer:
            return DifyResponse(
                status="not_found",
                error="Dify 返回空响应",
                response_id=response_id,
                raw_response=response_data
            )
        
        # 检查是否为"没有检索到相关信息"的标准回复
        no_info_keywords = ["没有检索到", "未找到相关", "知识库中没有", "无法找到"]
        if any(keyword in answer for keyword in no_info_keywords):
            return DifyResponse(
                status="not_found",
                content=answer,
                response_id=response_id,
                raw_response=response_data
            )
        
        # 检查是否为"回答不相关"的判断
        irrelevant_keywords = ["不相关", "无关", "不匹配", "无法确定相关性"]
        if any(keyword in answer for keyword in irrelevant_keywords):
            return DifyResponse(
                status="not_relevant", 
                content=answer,
                response_id=response_id,
                raw_response=response_data
            )
        
        # 其他情况视为成功检索
        return DifyResponse(
            status="success",
            content=answer,
            response_id=response_id,
            raw_response=response_data
        )
        
    except Exception as e:
        return DifyResponse(
            status="error",
            error=f"响应解析失败: {str(e)}",
            raw_response=response_data
        )
```

### 结果存储格式

#### 存储结构设计
按照需求文档的样例，结果存储到实体节点中：

```python
def format_rag_result(dify_response: DifyResponse, task_name: str) -> dict:
    """
    将 Dify 响应格式化为存储结构
    
    参考 L2 阶段的存储格式，保持一致性
    """
    now = datetime.now(timezone.utc).astimezone()
    
    if dify_response.status == "success":
        return {
            "content": dify_response.content,
            "status": "success",
            "meta": {
                "executed_at": now.isoformat(),
                "task_type": task_name,
                "dify_response_id": dify_response.response_id,
                "error": None
            }
        }
    elif dify_response.status == "not_found":
        return {
            "content": None,
            "status": "not_found", 
            "meta": {
                "executed_at": now.isoformat(),
                "task_type": task_name,
                "dify_response_id": dify_response.response_id,
                "error": "知识库中没有检索到相关信息"
            }
        }
    elif dify_response.status == "not_relevant":
        return {
            "content": dify_response.content,
            "status": "not_relevant",
            "meta": {
                "executed_at": now.isoformat(), 
                "task_type": task_name,
                "dify_response_id": dify_response.response_id,
                "error": "大模型判断回答与实体不相关"
            }
        }
    else:  # error
        return {
            "content": None,
            "status": "error",
            "meta": {
                "executed_at": now.isoformat(),
                "task_type": task_name,
                "dify_response_id": dify_response.response_id,
                "error": dify_response.error
            }
        }

def update_entity_with_rag_result(entity: dict, result: dict, task_name: str) -> None:
    """
    将 RAG 结果更新到实体节点
    
    字段名格式：l3_rag_{task_name}
    """
    field_name = f"l3_rag_{task_name}"
    entity[field_name] = result
```

### 文件处理流程

#### JSON 文件读写
```python
def process_json_file(file_path: str, task_name: str, dify_client: DifyClient) -> ProcessingStats:
    """
    处理单个 JSON 文件中的所有实体
    
    Returns:
        ProcessingStats: 处理统计信息
    """
    stats = ProcessingStats()
    
    # 读取 JSON 文件
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    row_id = data.get("row_id", "")
    entities = data.get("entities", [])
    
    # 从文件路径或内容中获取元数据信息
    metadata = extract_metadata_from_data(data)
    
    modified = False
    for entity in entities:
        # 检查是否需要跳过
        if should_skip_entity(entity, task_name):
            stats.skipped += 1
            continue
            
        try:
            # 提取字段
            fields = extract_entity_fields(entity, row_id, metadata)
            
            # 调用 Dify
            dify_response = dify_client.query_knowledge_base(
                fields.label, fields.type, fields.context_hint
            )
            
            # 格式化结果
            result = format_rag_result(dify_response, task_name)
            
            # 更新实体
            update_entity_with_rag_result(entity, result, task_name)
            
            modified = True
            stats.processed += 1
            
            # 记录成功日志
            logger.info(f"实体处理完成 label={fields.label} status={dify_response.status}")
            
        except Exception as e:
            # 记录错误但不中断整个流程
            logger.error(f"实体处理失败 label={entity.get('label')} error={str(e)}")
            stats.failed += 1
            continue
    
    # 如果有修改，写回文件
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"文件已更新 path={file_path}")
    
    return stats
```

### 配置管理

#### 配置结构
在 `settings.yaml` 中添加 L3 配置：

```yaml
# L3 语境线索层配置
l3_context_interpretation:
  # 全局启用开关
  enabled: true
  
  # RAG 任务配置
  rag_tasks:
    # 任务1：基于实体标签的检索
    entity_label_retrieval:
      enabled: true
      dify_key: "env:DIFY_ENTITY_RETRIEVAL_KEY"
      dify_base_url: "https://api.dify.ai/v1"
      # 速率限制（毫秒）
      rate_limit_ms: 1000
      # 重试配置
      retry_policy:
        max_retries: 3
        delay_seconds: 2
        backoff_factor: 2.0
```

#### 配置加载
```python
class L3ConfigManager:
    """L3 配置管理器"""
    
    def __init__(self, settings: dict):
        self.settings = settings
        self.l3_config = settings.get("l3_context_interpretation", {})
    
    def is_enabled(self) -> bool:
        """检查 L3 模块是否启用"""
        return self.l3_config.get("enabled", False)
    
    def get_task_config(self, task_name: str) -> dict:
        """获取指定任务的配置"""
        tasks = self.l3_config.get("rag_tasks", {})
        return tasks.get(task_name, {})
    
    def is_task_enabled(self, task_name: str) -> bool:
        """检查指定任务是否启用"""
        task_config = self.get_task_config(task_name)
        return task_config.get("enabled", False)
    
    def get_dify_config(self, task_name: str) -> DifyConfig:
        """获取 Dify 配置"""
        task_config = self.get_task_config(task_name)
        return DifyConfig(
            api_key=_resolve_env(task_config.get("dify_key", "")),
            base_url=task_config.get("dify_base_url", "https://api.dify.ai/v1"),
            rate_limit_ms=task_config.get("rate_limit_ms", 1000),
            retry_policy=task_config.get("retry_policy", {})
        )
```

### 主流程集成

#### main.py 修改
```python
# 在 _parse_tasks 函数中新增 L3 支持
def _parse_tasks(raw: Optional[str]) -> Tuple[List[str], bool, List[str], bool, List[str], bool, List[str]]:
    """
    解析任务字符串，增加 L3 支持
    
    Returns:
        - l0_tasks: L0 任务列表
        - l1_enabled: L1 是否启用
        - unknown: 未识别项  
        - l2_enabled: L2 是否启用
        - l2_phases: L2 阶段列表
        - l3_enabled: L3 是否启用  
        - l3_phases: L3 阶段列表
    """
    # ... 现有逻辑 ...
    
    l3_enabled = False
    l3_phases: List[str] = []
    
    # 在解析循环中添加 L3 支持
    elif mod == "l3":
        name_key = name_key.lower()
        # 阶段识别：rag/retrieval/interpretation
        if name_key in {"rag", "retrieval", "interpretation"}:
            if name_key not in l3_phases:
                l3_phases.append(name_key)
            l3_enabled = True
        # 整体开关
        elif name_key in {"context_interpretation", "l3"}:
            l3_enabled = True
        else:
            unknown.append(item)

# 在 main 函数中添加 L3 执行逻辑
def main():
    # ... 现有逻辑 ...
    
    if l3_enabled:
        if l3_phases:
            logger.info(f"pipeline_l3_enabled true phases={l3_phases}")
        else:
            logger.info("pipeline_l3_enabled true")
        from src.core.l3_context_interpretation.main import run_l3
        run_l3(excel_path=None, images_dir=None, limit=args.limit, tasks=(l3_phases if l3_phases else None))
    else:
        logger.info("pipeline_l3_skipped reason=not_selected")
```

### 错误处理与日志

#### 日志记录策略
```python
# 在每个关键步骤记录详细日志
logger.info(f"L3_RAG_开始处理 file={file_path} task={task_name}")
logger.info(f"实体字段提取 label={label} type={type} context_len={len(context_hint)}")
logger.info(f"Dify_API_调用 query_len={len(query)} api_key_prefix={api_key[:10]}...")
logger.info(f"Dify_响应解析 status={status} content_len={len(content)} response_id={response_id}")
logger.info(f"实体结果存储 field_name={field_name} status={result_status}")

# 错误日志包含足够的上下文信息
logger.error(f"实体处理失败 file={file_path} entity_label={label} error={str(e)}")
logger.warning(f"Dify_API_异常 status_code={response.status_code} response={response.text[:200]}")
```

### 测试策略

#### 单元测试
```python
# 测试 Dify 客户端
def test_dify_client_success_response()
def test_dify_client_not_found_response() 
def test_dify_client_not_relevant_response()
def test_dify_client_error_response()

# 测试实体字段提取
def test_extract_entity_fields()
def test_build_context_hint()
def test_should_skip_entity()

# 测试结果格式化
def test_format_rag_result_success()
def test_format_rag_result_error()
def test_update_entity_with_rag_result()
```

#### 集成测试
```python
# 测试完整流程
def test_process_single_entity_end_to_end()
def test_process_json_file_with_multiple_entities()
def test_skip_already_processed_entities()
```

## 实施检查清单

### 开发阶段
- [ ] 创建 L3 模块目录结构
- [ ] 实现 DifyClient 类和 API 集成
- [ ] 实现实体字段提取逻辑  
- [ ] 实现结果格式化和存储
- [ ] 实现主流程协调器
- [ ] 配置管理和验证
- [ ] 错误处理和日志记录

### 测试阶段
- [ ] 单元测试覆盖所有核心函数
- [ ] 模拟 Dify API 响应测试
- [ ] 真实环境集成测试
- [ ] 错误场景和边界条件测试
- [ ] 性能和并发测试

### 部署阶段
- [ ] 配置文档和示例
- [ ] 环境变量设置指南
- [ ] 与现有流水线集成验证
- [ ] 错误监控和报警设置

---

**文档版本**: v1.0  
**创建时间**: 2025-10-07  
**状态**: Proposal（等待用户审批）