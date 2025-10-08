from typing import Dict, Any, Optional
from dataclasses import dataclass

from ...utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class EntityFields:
    """实体提取的关键字段"""
    label: str
    type: str
    context_hint: str

class EntityExtractor:
    """实体信息提取器，从 JSON 文件中提取目标字段"""
    
    def __init__(self):
        logger.debug("EntityExtractor初始化完成")
    
    def extract_entity_fields(self, entity: Dict[str, Any], row_id: str, metadata: Dict[str, Any]) -> EntityFields:
        """
        提取实体的关键字段用于 RAG 检索
        
        Args:
            entity: 实体节点数据
            row_id: 行ID（编号）
            metadata: 元数据信息
            
        Returns:
            EntityFields: 包含 label, type, context_hint 的数据类
        """
        label = entity.get("label", "")
        entity_type = entity.get("type", "")
        
        # 直接使用JSON中现有的context_hint字段，不进行任何处理
        context_hint = entity.get("context_hint", "")
        
        logger.debug(f"实体字段提取完成 label={label} type={entity_type} context_hint_len={len(context_hint)}")
        
        return EntityFields(
            label=label,
            type=entity_type, 
            context_hint=context_hint
        )
    
    def _build_context_hint(self, row_id: str, metadata: Dict[str, Any]) -> str:
        """
        构建标准化的 context_hint 字符串
        格式与现有样例保持一致
        
        Args:
            row_id: 行ID
            metadata: 元数据字典
            
        Returns:
            str: 格式化的context_hint字符串
        """
        title = metadata.get("title", "")
        desc = metadata.get("desc", "")
        persons = metadata.get("persons", "")
        topic = metadata.get("topic", "")
        
        # 按照样例格式构建context_hint
        context_hint = f"""[元数据]
- 编号: {row_id}
- 题名: {title}
- 说明: {desc}
- 相关人物: {persons}
- 所属专题: {topic}"""
        
        return context_hint
    
    def should_skip_entity(self, entity: Dict[str, Any], task_name: str) -> bool:
        """
        检查实体是否已执行过指定的 RAG 任务
        
        兼容L2阶段的异常处理模式：
        - 检查实体字段是否有成功结果
        - 检查metadata中是否有异常状态记录
        
        Args:
            entity: 实体节点数据
            task_name: 任务名称，如 "entity_label_retrieval"
            
        Returns:
            bool: True 表示应跳过，False 表示需要执行
        """
        rag_field = f"l3_rag_{task_name}"
        
        # 检查实体字段是否存在且有成功结果
        if rag_field in entity and entity[rag_field] is not None:
            # 检查是否有执行时间戳（表示已完成）
            executed_meta = entity[rag_field].get("meta", {})
            executed_at = executed_meta.get("executed_at")
            
            if executed_at:
                entity_label = entity.get("label", "")
                logger.info(f"实体已执行过任务，跳过处理 entity={entity_label} task={task_name} executed_at={executed_at}")
                return True
        
        # 检查metadata中是否有异常状态记录
        metadata = entity.get("metadata", {})
        if rag_field in metadata:
            executed_at = metadata[rag_field].get("executed_at")
            status = metadata[rag_field].get("status")
            
            if executed_at and status:
                entity_label = entity.get("label", "")
                logger.info(f"实体已执行过任务（metadata记录），跳过处理 entity={entity_label} task={task_name} status={status} executed_at={executed_at}")
                return True
        
        return False
    
    def extract_metadata_from_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从JSON数据中提取元数据信息
        
        Args:
            data: JSON文件的完整数据
            
        Returns:
            Dict[str, Any]: 元数据字典
        """
        # 这里可能需要根据实际JSON结构调整
        # 暂时返回空字典，实际使用时需要从外部传入或从文件路径推断
        return {
            "title": "",
            "desc": "",
            "persons": "", 
            "topic": ""
        }