"""
作品API响应解析器

该模块专门处理work_api的响应格式，适配其特殊的响应结构：
- 数据存储在 'resultList' 字段而非标准的 'data' 字段
- 包含分页信息：pager.pageCount, pager.rowCount 等
- 字段映射：label, creator, note, uri 等

遵循项目的【特殊响应解析处理规范】，为work_api提供独立的解析逻辑。
"""

from typing import Any, Dict, List
from .....utils.logger import get_logger

logger = get_logger(__name__)


class WorkResponseParser:
    """作品API专用响应解析器"""
    
    @staticmethod
    def parse(raw_data: Any, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析work_api的响应数据
        
        Args:
            raw_data: API原始响应数据
            settings: 全局设置
        
        Returns:
            解析后的候选列表
        """
        if not raw_data or not isinstance(raw_data, dict):
            logger.warning("work_api_empty_or_invalid_response")
            return []
        
        # work_api使用 'resultList' 字段存储数据
        result_list = raw_data.get("resultList", [])
        if not isinstance(result_list, list):
            logger.warning("work_api_invalid_resultlist_format")
            return []
        
        # 记录分页信息（用于调试）
        pager = raw_data.get("pager", {})
        if isinstance(pager, dict):
            page_count = pager.get("pageCount", 0)
            row_count = pager.get("rowCount", 0)
            current_page = pager.get("pageth", 1)
            logger.info(f"work_api_pagination_info current_page={current_page} page_count={page_count} row_count={row_count}")
        
        # 获取work_api的字段配置
        work_api_config = settings.get("tools", {}).get("work_api", {})
        fields_config = work_api_config.get("fields", {})
        fields_to_extract = fields_config.get("extract", ["label", "uri", "note", "creator"])
        field_mapping = fields_config.get("mapping", {})
        
        results = []
        for item in result_list:
            if not isinstance(item, dict):
                continue
            
            parsed_item = {}
            
            # 提取并映射字段
            for field in fields_to_extract:
                if field in item:
                    mapped_field = field_mapping.get(field, field)
                    parsed_item[mapped_field] = item[field]
            
            # 确保必要字段存在
            if "label" not in parsed_item and "label" in item:
                parsed_item["label"] = item["label"]
            
            if "uri" not in parsed_item and "uri" in item:
                parsed_item["uri"] = item["uri"]
            
            # 添加原始数据以备后查
            parsed_item["_raw"] = item
            
            results.append(parsed_item)
        
        logger.info(f"work_api_parse_result count={len(results)}")
        return results
    
    @staticmethod
    def extract_pagination_info(raw_data: Any) -> Dict[str, Any]:
        """
        提取分页信息
        
        Args:
            raw_data: API原始响应数据
        
        Returns:
            分页信息字典
        """
        if not raw_data or not isinstance(raw_data, dict):
            return {}
        
        pager = raw_data.get("pager")
        if not pager or not isinstance(pager, dict):
            return {}
        
        return {
            "current_page": pager.get("pageth", 1),
            "page_count": pager.get("pageCount", 0),
            "page_size": pager.get("pageSize", 10),
            "row_count": pager.get("rowCount", 0),
            "has_next_page": pager.get("pageth", 1) < pager.get("pageCount", 0)
        }