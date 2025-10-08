"""
机构API响应解析器

专门处理机构API特殊的返回格式：
1. name字段为数组，包含多语言版本（@en, @chs, @cht），需要特殊提取
2. place字段需要只提取city信息
3. description和creator字段为数组格式，需要特殊处理
4. created字段为简单字符串字段
"""

from typing import Any, Dict, List, Optional
from .....utils.logger import get_logger

logger = get_logger(__name__)


class OrganizationResponseParser:
    """机构API专用响应解析器"""
    
    @staticmethod
    def parse(raw_data: Any, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析机构API响应数据
        
        Args:
            raw_data: 原始API响应数据
            settings: 系统配置
            
        Returns:
            解析后的标准化数据列表
        """
        if not raw_data or not isinstance(raw_data, dict):
            return []
        
        # 检查返回结果状态
        if raw_data.get("result") != "0":
            logger.warning(f"organization_api_error_response result={raw_data.get('result')}")
            return []
        
        # 提取数据项
        data_items = raw_data.get("data", [])
        if not isinstance(data_items, list):
            logger.warning("organization_api_invalid_data_format")
            return []
        
        results = []
        for item in data_items:
            if not isinstance(item, dict):
                continue
            
            try:
                parsed_item = OrganizationResponseParser._parse_single_item(item)
                if parsed_item:
                    # 添加原始数据以备后查
                    parsed_item["_raw"] = item
                    results.append(parsed_item)
            except Exception as e:
                logger.warning(f"organization_api_parse_item_failed item={item} err={e}")
                continue
        
        logger.info(f"organization_api_parsed count={len(results)}")
        return results
    
    @staticmethod
    def _parse_single_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析单个机构数据项
        
        Args:
            item: 单个机构数据项
            
        Returns:
            解析后的标准化数据，如果解析失败返回None
        """
        parsed = {}
        
        # 解析name字段（数组格式，包含多语言版本）
        name_labels = OrganizationResponseParser._parse_name_array(item.get("name", []))
        if name_labels:
            parsed.update(name_labels)
        
        # 解析URI
        if "uri" in item:
            parsed["uri"] = item["uri"]
        
        # 解析类型
        if "type" in item:
            parsed["type"] = item["type"]
        
        # 解析place字段（只提取city信息）
        place_info = OrganizationResponseParser._parse_place_object(item.get("place", {}))
        if place_info:
            parsed.update(place_info)
        
        # 解析description字段（处理数组格式）
        if "description" in item:
            desc_data = item["description"]
            if isinstance(desc_data, list) and desc_data:
                # 如果是数组，取第一个元素
                parsed["description"] = desc_data[0]
            elif isinstance(desc_data, str):
                # 如果是字符串，直接使用
                parsed["description"] = desc_data
        
        # 解析creator字段（处理数组格式）
        if "creator" in item:
            creator_data = item["creator"]
            if isinstance(creator_data, list):
                # 如果是数组，转换为逗号分隔的字符串
                parsed["creator"] = ", ".join(str(c) for c in creator_data if c)
            elif isinstance(creator_data, str):
                # 如果是字符串，直接使用
                parsed["creator"] = creator_data
        
        # 解析created字段
        if "created" in item:
            parsed["created"] = item["created"]
        
        # 如果没有解析出任何有效字段，返回None
        if not parsed:
            return None
        
        return parsed
    
    @staticmethod
    def _parse_name_array(name_array: List[str]) -> Dict[str, str]:
        """
        解析name数组，提取@chs和@cht后缀的值
        
        Args:
            name_array: name数组，包含不同语言版本的名称
            
        Returns:
            包含label和label_cht的字典
        """
        labels = {}
        
        if not isinstance(name_array, list):
            return labels
        
        for name_item in name_array:
            if not isinstance(name_item, str):
                continue
            
            # 检查@chs后缀（简体中文）
            if name_item.endswith("@chs"):
                clean_name = name_item.replace("@chs", "").strip()
                if clean_name:
                    labels["label"] = clean_name
            
            # 检查@cht后缀（繁体中文）
            elif name_item.endswith("@cht"):
                clean_name = name_item.replace("@cht", "").strip()
                if clean_name:
                    labels["label_cht"] = clean_name
        
        return labels
    
    @staticmethod
    def _parse_place_object(place_data: Dict[str, Any]) -> Dict[str, str]:
        """
        解析place对象，只提取city信息
        
        Args:
            place_data: place对象数据
            
        Returns:
            包含place和place_uri的字典
        """
        place_info = {}
        
        if not isinstance(place_data, dict):
            return place_info
        
        # 提取city信息作为place
        if "city" in place_data:
            place_info["place"] = place_data["city"]
        
        # 提取placeUri
        if "placeUri" in place_data:
            place_info["place_uri"] = place_data["placeUri"]
        
        return place_info