"""
事件API响应解析器

该模块专门处理event_api的响应格式，适配其响应结构：
- 数据存储在标准的 'data' 字段
- 包含分页信息：pager.pageCount, pager.rowCount 等
- 字段映射：title, description, begin, end, uri, dateLabel 等

遵循项目的【特殊响应解析处理规范】，为event_api提供独立的解析逻辑。
"""

from typing import Any, Dict, List
from .....utils.logger import get_logger

logger = get_logger(__name__)


class EventResponseParser:
    """事件API专用响应解析器"""
    
    @staticmethod
    def parse(raw_data: Any, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析event_api的响应数据
        
        Args:
            raw_data: API原始响应数据
            settings: 全局设置
        
        Returns:
            解析后的候选列表
        """
        if not raw_data or not isinstance(raw_data, dict):
            logger.warning("event_api_empty_or_invalid_response")
            return []
        
        # event_api使用标准的 'data' 字段存储数据
        data_list = raw_data.get("data", [])
        if not isinstance(data_list, list):
            logger.warning("event_api_invalid_data_format")
            return []
        
        # 记录分页信息（用于调试）
        pager = raw_data.get("pager", {})
        if isinstance(pager, dict):
            page_count = pager.get("pageCount", 0)
            row_count = pager.get("rowCount", 0)
            current_page = pager.get("pageth", 1)
            page_size = pager.get("pageSize", 10)
            logger.info(f"event_api_pagination_info current_page={current_page} page_count={page_count} row_count={row_count} page_size={page_size}")
        
        # 获取event_api的字段配置
        event_api_config = settings.get("tools", {}).get("event_api", {})
        fields_config = event_api_config.get("fields", {})
        fields_to_extract = fields_config.get("extract", ["title", "description", "begin", "end", "uri", "dateLabel"])
        field_mapping = fields_config.get("mapping", {})
        
        results = []
        for item in data_list:
            if not isinstance(item, dict):
                continue
            
            parsed_item = {}
            
            # 提取并映射字段
            for field in fields_to_extract:
                if field in item:
                    mapped_field = field_mapping.get(field, field)
                    # 处理空值和None值
                    value = item[field]
                    if value is not None and str(value).strip():
                        parsed_item[mapped_field] = value
            
            # 确保必要字段存在 - title作为主要标识字段
            if "label" not in parsed_item and "title" in item:
                title_value = item["title"]
                if title_value is not None and str(title_value).strip():
                    parsed_item["label"] = title_value
            
            # 确保URI字段存在
            if "uri" not in parsed_item and "uri" in item:
                uri_value = item["uri"]
                if uri_value is not None and str(uri_value).strip():
                    parsed_item["uri"] = uri_value
            
            # 添加原始数据以备后查
            parsed_item["_raw"] = item
            
            # 只有包含有效标题的事件才加入结果
            if parsed_item.get("label") and str(parsed_item.get("label")).strip():
                results.append(parsed_item)
        
        logger.info(f"event_api_parse_result count={len(results)}")
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