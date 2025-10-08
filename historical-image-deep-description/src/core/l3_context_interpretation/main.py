import os
import glob
from typing import List, Optional, Dict, Any, Tuple, Union

from .rag_processor import RagProcessor, ProcessingStats
from .unified_enhanced_rag_processor import UnifiedEnhancedRAGProcessor
from .enhanced_web_retrieval import EnhancedWebRetrieval
from .web_search_processor import WebSearchProcessor
from ...utils.logger import get_logger
from ...utils.llm_api import load_settings
from ...utils.excel_io import ExcelIO, ExcelConfig
from ..l2_knowledge_linking.task_builder import _safe_filename

logger = get_logger(__name__)

def _resolve_id_header(settings: dict) -> str:
    """
    解析编号列显示名（复用L2逻辑）：
    - 优先 data.excel.columns.id_col
    - 其次 data.excel.columns.metadata.id
    - 回退默认"编号"
    """
    excel_cfg = settings.get("data", {}).get("excel", {})
    cols = excel_cfg.get("columns", {}) or {}
    id_col = cols.get("id_col")
    if isinstance(id_col, str) and id_col.strip():
        return id_col.strip()
    meta = cols.get("metadata") or {}
    meta_id = meta.get("id")
    if isinstance(meta_id, str) and meta_id.strip():
        return meta_id.strip()
    return "编号"

def _extract_metadata_from_excel_row(xio: ExcelIO, row_cells: Dict[str, Any], row_id: str) -> Dict[str, Any]:
    """
    从Excel行提取元数据（基于实际列数据构建）
    
    Args:
        xio: Excel IO对象
        row_cells: Excel行数据
        row_id: 行编号
        
    Returns:
        Dict[str, Any]: 元数据字典
    """
    # 尝试获取常见的元数据字段
    title = xio.get_value(row_cells, "题名") or ""
    desc = xio.get_value(row_cells, "内容描述") or ""
    persons = xio.get_value(row_cells, "人物") or ""
    topic = xio.get_value(row_cells, "主题") or ""
    
    return {
        "row_id": row_id,
        "title": str(title).strip() if title else "",
        "desc": str(desc).strip() if desc else "",
        "persons": str(persons).strip() if persons else "",
        "topic": str(topic).strip() if topic else ""
    }

def _process_single_json_file(json_file_path: str,
                             task_list: List[str],
                             processor: RagProcessor,
                             enhanced_rag_processor: UnifiedEnhancedRAGProcessor,
                             enhanced_web_processor: EnhancedWebRetrieval,
                             web_search_processor: WebSearchProcessor,
                             settings: Dict[str, Any],
                             metadata: Dict[str, Any]) -> None:
    """
    处理单个JSON文件的所有L3任务
    
    Args:
        json_file_path: JSON文件路径
        task_list: 要执行的任务列表
        processor: RAG处理器
        enhanced_rag_processor: 统一增强RAG检索处理器
        enhanced_web_processor: 增强Web检索处理器
        web_search_processor: Web搜索处理器
        settings: 全局配置
        metadata: 元数据
    """
    try:
        # 读取JSON文件
        import json
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        file_modified = False
        row_id = metadata.get("row_id", "")
        
        # 处理每个任务
        for task_name in task_list:
            if task_name == "unified_enhanced_rag_retrieval":
                # 统一增强RAG检索处理器会处理所有启用的实体类型
                if _execute_unified_enhanced_rag_on_file(enhanced_rag_processor, data, row_id, metadata):
                    file_modified = True
            elif task_name == "enhanced_web_retrieval":
                if _execute_enhanced_web_retrieval_on_file(enhanced_web_processor, data, row_id, metadata):
                    file_modified = True
            elif task_name == "web_search":
                if _execute_web_search_on_file(web_search_processor, data, row_id):
                    file_modified = True
            else:
                # RAG任务
                file_stats = processor.process_json_file(json_file_path, task_name, metadata)
                if file_stats.processed > 0 or file_stats.failed > 0:
                    file_modified = True
        
        # 如果有修改，写回文件
        if file_modified:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"文件已更新 path={json_file_path}")
            
    except Exception as e:
        logger.error(f"文件处理失败 file={json_file_path} error={str(e)}")
        raise

def _execute_unified_enhanced_rag_on_file(enhanced_processor,
                                         data: Dict[str, Any],
                                         row_id: str,
                                         metadata: Dict[str, Any]) -> bool:
    """
    在单个文件上执行统一增强RAG检索任务
    
    Args:
        enhanced_processor: 统一增强RAG检索处理器
        data: JSON数据
        row_id: 行ID
        metadata: 元数据
        
    Returns:
        bool: 是否有修改文件
    """
    entities = data.get("entities", [])
    file_modified = False
    
    for entity in entities:
        entity_type = entity.get("type", "")
        entity_label = entity.get("label", "")
        
        # 检查是否启用
        if not enhanced_processor.is_enabled_for_entity(entity_type):
            logger.debug(f"增强RAG检索未对实体类型启用 type={entity_type} label={entity_label}")
            continue
        
        # 检查是否已处理
        if enhanced_processor.should_skip_entity(entity, enhanced_processor.get_task_name()):
            logger.debug(f"实体已处理过增强RAG检索，跳过 label={entity_label}")
            continue
        
        # 处理实体
        success = enhanced_processor.process_entity(entity, row_id, metadata)
        
        if success:
            file_modified = True
            logger.info(f"增强RAG检索完成 type={entity_type} label={entity_label}")
        else:
            file_modified = True  # 失败时也会写入失败信息
            logger.warning(f"增强RAG检索失败 type={entity_type} label={entity_label}")
    
    return file_modified

def _execute_enhanced_web_retrieval_on_file(enhanced_web_processor,
                                          data: Dict[str, Any],
                                          row_id: str,
                                          metadata: Dict[str, Any]) -> bool:
    """
    在单个文件上执行增强Web检索任务
    
    Args:
        enhanced_web_processor: 增强Web检索处理器
        data: JSON数据
        row_id: 行ID
        metadata: 元数据
        
    Returns:
        bool: 是否有修改文件
    """
    entities = data.get("entities", [])
    file_modified = False
    
    for entity in entities:
        entity_type = entity.get("type", "")
        entity_label = entity.get("label", "")
        
        # 检查是否启用
        if not enhanced_web_processor.is_enabled_for_entity(entity_type):
            logger.debug(f"增强Web检索未对实体类型启用 type={entity_type} label={entity_label}")
            continue
        
        # 检查是否已处理
        if enhanced_web_processor.should_skip_entity(entity, enhanced_web_processor.get_task_name()):
            logger.debug(f"实体已处理过增强Web检索，跳过 label={entity_label}")
            continue
        
        # 处理实体
        success = enhanced_web_processor.process_entity(entity, row_id, metadata)
        
        if success:
            file_modified = True
            logger.info(f"增强Web检索完成 label={entity_label}")
        else:
            file_modified = True  # 失败时也会写入失败信息
            logger.warning(f"增强Web检索失败 label={entity_label}")
    
    return file_modified

def _execute_web_search_on_file(web_processor: WebSearchProcessor,
                               data: Dict[str, Any],
                               row_id: str) -> bool:
    """
    在单个文件上执行Web搜索任务
    
    Returns:
        bool: 是否有修改文件
    """
    entities = data.get("entities", [])
    file_modified = False
    
    for entity in entities:
        entity_label = entity.get("label", "")
        entity_type = entity.get("type", "")
        
        # 检查是否为该实体类型启用Web搜索
        if not web_processor.is_enabled_for_entity_type(entity_type):
            logger.info(f"Web搜索未对实体类型启用，跳过处理 type={entity_type} label={entity_label}")
            continue
        
        # 检查是否已处理
        if web_processor.should_skip_entity(entity):
            logger.debug(f"实体已处理过Web搜索，跳过 label={entity_label}")
            continue
        
        # 处理实体
        success = web_processor.process_entity_web_search(entity, row_id)
        
        if success:
            file_modified = True
            logger.info(f"Web搜索完成 label={entity_label}")
        else:
            file_modified = True  # 失败时也会写入失败信息
            logger.warning(f"Web搜索失败 label={entity_label}")
    
    return file_modified

def run_l3(excel_path: Optional[str] = None, 
          images_dir: Optional[str] = None, 
          limit: Optional[int] = None, 
          tasks: Optional[List[str]] = None) -> None:
    """
    L3 语境线索层主入口函数
    
    Args:
        excel_path: Excel文件路径（可选，从配置获取）
        images_dir: 图片目录路径（可选，从配置获取）  
        limit: 处理条数限制（可选）
        tasks: 要执行的L3任务列表（可选，默认执行所有启用的任务）
    """
    try:
        logger.info("=" * 50)
        logger.info("L3 语境线索层开始执行")
        logger.info("=" * 50)
        
        # 加载配置
        settings = load_settings()
        
        # 检查L3模块是否启用
        l3_config = settings.get("l3_context_interpretation", {})
        if not l3_config.get("enabled", False):
            logger.warning("L3模块未启用，跳过执行")
            return
        
        # 确定要执行的任务
        task_list = _determine_tasks(tasks, l3_config)
        if not task_list:
            logger.warning("没有可执行的L3任务")
            return
        
        logger.info(f"将执行L3任务: {task_list}")
        
        # 创建RAG处理器
        processor = RagProcessor(settings)
        
        # 创建统一增强RAG检索处理器
        enhanced_rag_processor = UnifiedEnhancedRAGProcessor(settings)
        
        # 创建增强Web检索处理器
        enhanced_web_processor = EnhancedWebRetrieval(settings)
        
        # 创建Web搜索处理器
        web_search_processor = WebSearchProcessor(settings)
        
        # 设置Excel配置并按行处理（遵循L2模式）
        _process_by_excel_rows(settings, task_list, processor, enhanced_rag_processor, enhanced_web_processor, web_search_processor, excel_path, limit)
        
        logger.info("=" * 50)
        logger.info("L3 语境线索层执行完成")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"L3模块执行失败: {str(e)}", exc_info=True)
        raise

def _process_by_excel_rows(settings: Dict[str, Any], 
                          task_list: List[str],
                          processor: RagProcessor,
                          enhanced_rag_processor: UnifiedEnhancedRAGProcessor,
                          enhanced_web_processor: EnhancedWebRetrieval,
                          web_search_processor: WebSearchProcessor,
                          excel_path: Optional[str] = None,
                          limit: Optional[int] = None) -> None:
    """
    按Excel行驱动L3任务处理（遵循L2模式）
    
    Args:
        settings: 全局配置
        task_list: 要执行的任务列表
        processor: RAG处理器
        enhanced_rag_processor: 统一增强RAG检索处理器
        enhanced_web_processor: 增强Web检索处理器
        web_search_processor: Web搜索处理器
        excel_path: Excel文件路径
        limit: 处理行数限制
    """
    # 获取Excel配置
    data_cfg = settings["data"]
    excel_cfg = data_cfg["excel"]
    cols_cfg = excel_cfg["columns"]
    write_policy = {
        "skip_if_present": settings["write_policy"]["skip_if_present"],
        "create_backup": settings["write_policy"]["create_backup"],
    }
    
    # 获取编号列名（复用L2的逻辑）
    id_header = _resolve_id_header(settings)
    
    # 获取输出目录
    outputs_cfg = settings.get("data", {}).get("outputs", {}) or {}
    out_dir = outputs_cfg.get("outputs_dir") or os.path.join("runtime", "outputs")
    
    # Excel文件路径
    excel_file_path = excel_path or data_cfg["paths"]["metadata_excel"]
    
    # 创建Excel IO
    xio = ExcelIO(
        excel_file_path,
        ExcelConfig(
            sheet_name=excel_cfg.get("sheet_name", ""),
            columns=cols_cfg,
            skip_if_present=write_policy["skip_if_present"],
            create_backup=write_policy["create_backup"],
        )
    )
    
    # 逐行处理
    processed = 0
    for row_data in xio.iter_rows():
        # 确保row_data是正确的格式
        if isinstance(row_data, tuple) and len(row_data) == 2:
            row_idx, row = row_data
        else:
            # 如果不是元组，使用索引作为行号
            row_idx = processed
            row = row_data
            
        # 获取行单元格数据
        if isinstance(row, dict) and "cells" in row:
            row_cells = row["cells"]
        else:
            row_cells = {}
            
        raw_id = xio.get_value(row_cells, id_header)
        
        # 规范化编号
        if isinstance(raw_id, str):
            raw_id = raw_id.strip()
        elif raw_id is not None:
            raw_id = str(raw_id)
        else:
            raw_id = ""
        
        if not raw_id:
            logger.warning(f"L3前置检查跳过（无编号） row={row_idx}")
            continue
            
        if limit is not None and processed >= limit:
            break
            
        # 根据编号构建JSON文件路径
        json_filename = f"{_safe_filename(raw_id)}.json"
        json_file_path = os.path.join(out_dir, json_filename)
        
        if not os.path.exists(json_file_path):
            logger.warning(f"L3跳过处理（JSON文件不存在） id={raw_id} file={json_filename} row={row_idx}")
            continue
            
        logger.info(f"L3开始处理 id={raw_id} row={row_idx} file={json_filename}")
        
        # 从Excel行构建元数据上下文
        metadata = _extract_metadata_from_excel_row(xio, row_cells, raw_id)
        
        # 处理JSON文件
        _process_single_json_file(json_file_path, task_list, processor, enhanced_rag_processor, 
                                 enhanced_web_processor, web_search_processor, settings, metadata)
        
        processed += 1
        logger.info(f"L3行处理完成 id={raw_id} row={row_idx}")
    
    logger.info(f"L3按行处理完成 total_processed={processed}")

def _determine_tasks(tasks: Optional[List[str]], l3_config: Dict[str, Any]) -> List[str]:
    """
    确定要执行的任务列表
    
    Args:
        tasks: 用户指定的任务列表
        l3_config: L3配置
        
    Returns:
        List[str]: 最终的任务列表
    """
    if tasks:
        # 用户指定了任务，过滤出有效的任务
        valid_tasks = []
        for task in tasks:
            # 支持简化的任务名
            if task in ["rag", "retrieval"]:
                task = "entity_label_retrieval"
            elif task == "rag+":  # 统一增强RAG检索触发器
                # 统一的增强RAG检索触发器：添加统一的增强RAG任务
                enhanced_config = l3_config.get("enhanced_rag_retrieval", {})
                if enhanced_config.get("enabled", False):
                    valid_tasks.append("unified_enhanced_rag_retrieval")
                    logger.info(f"rag+触发器自动添加任务: ['unified_enhanced_rag_retrieval']")
                else:
                    logger.warning("rag+触发器：增强RAG检索未在配置中启用")
                continue  # 继续下一个任务
            elif task == "web+":  # 新增web+触发器支持
                # 统一的增强Web检索触发器：根据配置自动添加所有启用的增强Web任务
                enhanced_web_config = l3_config.get("enhanced_web_retrieval", {})
                if enhanced_web_config.get("enabled", False):
                    entity_types_config = enhanced_web_config.get("entity_types", {})
                    # 根据配置中启用的实体类型自动添加对应的增强任务
                    for entity_type, entity_config in entity_types_config.items():
                        if entity_config.get("enabled", False):
                            # 添加增强Web检索任务
                            if "enhanced_web_retrieval" not in valid_tasks:
                                valid_tasks.append("enhanced_web_retrieval")
                    logger.info(f"web+触发器自动添加任务: {[t for t in valid_tasks if 'enhanced_web' in t]}")
                else:
                    logger.warning("web+触发器：增强Web检索未在配置中启用")
                continue  # 继续下一个任务
            elif task in ["web", "web_search"]:
                task = "web_search"
            
            if _is_task_available(task, l3_config):
                valid_tasks.append(task)
            else:
                logger.warning(f"任务不可用或未启用: {task}")
        
        return valid_tasks
    else:
        # 没有指定任务，返回所有启用的任务
        enabled_tasks = []
        
        # 检查RAG任务
        rag_tasks = l3_config.get("rag_tasks", {})
        for task_name, task_config in rag_tasks.items():
            if task_config.get("enabled", False):
                enabled_tasks.append(task_name)
        
        # 检查增强RAG检索任务
        enhanced_config = l3_config.get("enhanced_rag_retrieval", {})
        if enhanced_config.get("enabled", False):
            enabled_tasks.append("unified_enhanced_rag_retrieval")
        
        # 检查增强Web检索任务
        enhanced_web_config = l3_config.get("enhanced_web_retrieval", {})
        if enhanced_web_config.get("enabled", False):
            # 根据配置中启用的实体类型添加对应的增强任务
            entity_types_config = enhanced_web_config.get("entity_types", {})
            for entity_type, entity_config in entity_types_config.items():
                if entity_config.get("enabled", False):
                    enabled_tasks.append("enhanced_web_retrieval")
        
        # 检查Web搜索任务
        web_search_config = l3_config.get("web_search", {})
        if web_search_config.get("enabled", False):
            enabled_tasks.append("web_search")
        
        return enabled_tasks

def _is_task_available(task_name: str, l3_config: Dict[str, Any]) -> bool:
    """检查任务是否在全局和任务级别可用且启用"""
    # 全局启用检查
    if not l3_config.get("enabled", False):
        return False
    
    # 增强RAG检索特殊处理
    if task_name == "unified_enhanced_rag_retrieval":
        enhanced_config = l3_config.get("enhanced_rag_retrieval", {})
        return enhanced_config.get("enabled", False)
    
    # 增强Web检索特殊处理
    if task_name == "enhanced_web_retrieval":
        enhanced_web_config = l3_config.get("enhanced_web_retrieval", {})
        return enhanced_web_config.get("enabled", False)
    
    # Web搜索特殊处理
    if task_name == "web_search":
        web_search_config = l3_config.get("web_search", {})
        return web_search_config.get("enabled", False)
    
    # RAG任务级别启用检查
    rag_tasks = l3_config.get("rag_tasks", {})
    task_config = rag_tasks.get(task_name, {})
    return task_config.get("enabled", False)




# CLI支持（如果直接运行此模块）
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="L3 语境线索层独立执行")
    parser.add_argument("--tasks", type=str, help="要执行的任务，逗号分隔")
    parser.add_argument("--limit", type=int, help="处理文件数量限制")
    
    args = parser.parse_args()
    
    tasks_list = None
    if args.tasks:
        tasks_list = [task.strip() for task in args.tasks.split(",")]
    
    run_l3(tasks=tasks_list, limit=args.limit)