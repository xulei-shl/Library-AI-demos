from typing import Any, Dict, List, Optional
import time
import httpx
from abc import ABC, abstractmethod

from .....utils.logger import get_logger
from .....utils.llm_api import load_settings, _resolve_env

logger = get_logger(__name__)

class InternalAPIClient(ABC):
    """内部API客户端基类"""
    
    def __init__(self, api_name: str, settings: Dict[str, Any]):
        self.api_name = api_name
        self.settings = settings
        self.api_config = settings.get("tools", {}).get(api_name, {})
    
    @abstractmethod
    def search(self, entity_label: str, lang: str = "zh", type_hint: Optional[str] = None) -> Any:
        """搜索实体，子类需要实现此方法"""
        pass
    
    def _make_request(self, url: str, params: Dict[str, Any]) -> Any:
        """发起HTTP请求的通用方法"""
        try:
            # 设置必要的HTTP请求头
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
            
            # 使用httpx客户端，设置超时、请求头和跟随重定向
            with httpx.Client(timeout=httpx.Timeout(15.0), headers=headers, follow_redirects=True) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning(f"http_request_failed url={url} err={e}")
            return None

class ResponseParser:
    """响应解析器"""
    
    @staticmethod
    def parse(api_name: str, raw_data: Any, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析API响应数据"""
        # 机构API使用专用解析器
        if api_name == "organization_api":
            from .organization_response_parser import OrganizationResponseParser
            return OrganizationResponseParser.parse(raw_data, settings)
        
        # work_api使用专用解析器
        if api_name == "work_api":
            from .work_response_parser import WorkResponseParser
            return WorkResponseParser.parse(raw_data, settings)
        
        # event_api使用专用解析器
        if api_name == "event_api":
            from .event_response_parser import EventResponseParser
            return EventResponseParser.parse(raw_data, settings)

        # place_api使用专用解析器（仅取 chs 的 label/country，兼容 result.data 字符串包裹）
        if api_name == "place_api":
            from .place_response_parser import PlaceResponseParser
            return PlaceResponseParser.parse(raw_data, settings)
        
        # 其他API使用通用解析逻辑
        # 获取API的字段配置 - 从新的统一配置结构中读取
        api_config = settings.get("tools", {}).get(api_name, {})
        fields_config = api_config.get("fields", {})
        fields_to_extract = fields_config.get("extract", [])
        field_mapping = fields_config.get("mapping", {})
        
        # 提取数据项（根据不同API的数据结构）
        items = ResponseParser._extract_items(api_name, raw_data)
        
        # 解析每个数据项
        results = []
        for item in items:
            if not isinstance(item, dict):
                continue
                
            parsed_item = {}
            # 提取并映射字段
            for field in fields_to_extract:
                if field in item:
                    mapped_field = field_mapping.get(field, field)
                    parsed_item[mapped_field] = item[field]
            
            # 添加原始数据以备后查
            parsed_item["_raw"] = item
            results.append(parsed_item)
        
        return results
    
    @staticmethod
    def _extract_items(api_name: str, raw_data: Any) -> List[Dict[str, Any]]:
        """根据API类型提取数据项"""
        if not raw_data:
            return []
        
        if api_name == "person_api":
            return raw_data.get("data", [])
        elif api_name == "place_api":
            return [raw_data] if isinstance(raw_data, dict) else []
        elif api_name in ["organization_api", "event_api", "work_api", "architecture_api"]:
            return raw_data.get("data", [])
        else:
            # 默认通用逻辑：尝试从'data'字段提取，如果没有则直接返回数据
            if isinstance(raw_data, dict):
                if "data" in raw_data:
                    data = raw_data["data"]
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        return [data]
                else:
                    # 如果没有data字段，把整个对象作为一个数据项
                    return [raw_data]
            elif isinstance(raw_data, list):
                return raw_data
            return []

class InternalAPIRouter:
    """内部API路由器，根据实体类型选择对应的API接口"""
    
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        # 构建实体类型到API的映射关系，从新的配置结构中读取
        self.type_mapping = self._build_type_mapping(settings)
    
    def _build_type_mapping(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """从tools配置构建实体类型到API的映射关系"""
        type_mapping = {}
        tools_config = settings.get("tools", {})
        
        for api_name, api_config in tools_config.items():
            if api_name.endswith("_api") and isinstance(api_config, dict):
                entity_types = api_config.get("entity_types", [])
                for entity_type in entity_types:
                    type_mapping[entity_type] = api_name
        
        return type_mapping
    
    def get_api_name(self, entity_type: str) -> Optional[str]:
        """根据实体类型获取对应的API名称"""
        return self.type_mapping.get(entity_type)
    
    def route_to_api(self, entity_type: str, entity_label: str, lang: str = "zh", type_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """路由到对应的API并返回结果"""
        api_name = self.get_api_name(entity_type)
        if not api_name:
            logger.warning(f"no_api_mapping_for_type type={entity_type}")
            return []
        
        # 检查API是否启用
        api_enabled = self.settings.get("tools", {}).get(api_name, {}).get("enabled", True)
        if not api_enabled:
            logger.info(f"api_disabled api={api_name} type={entity_type} label={entity_label}")
            return []
        
        # 从注册表获取API客户端
        from . import InternalAPIRegistry
        api_client = InternalAPIRegistry.get_client(api_name)
        if not api_client:
            logger.warning(f"api_client_not_found api={api_name}")
            return []
        
        # 检查是否启用分页搜索
        pagination_config = self.settings.get("tools", {}).get(api_name, {}).get("pagination", {})
        if pagination_config.get("enabled", False):
            logger.info(f"using_paginated_search api={api_name} label={entity_label}")
            # 使用分页搜索器
            try:
                from .paginated_searcher import PaginatedAPISearcher
                searcher = PaginatedAPISearcher(api_client, pagination_config, self.settings)
                # 返回单纯的候选列表，不进行LLM判断（由上层调用者处理）
                result = searcher.search_with_llm_judgment(entity_label, entity_type, "", lang, type_hint)
                
                # 将分页搜索结果转换为标准格式
                if result.get("matched") and result.get("selected"):
                    selected = result["selected"]
                    # 为候选注入API名称
                    if isinstance(selected, dict):
                        selected["__api_name"] = api_name
                    return [selected]
                else:
                    return []
                    
            except Exception as e:
                logger.error(f"paginated_search_error api={api_name} label={entity_label} error={e}")
                # 失败时回退到原有逻辑
                pass
        
        # 使用原有的单页搜索逻辑
        try:
            raw_data = api_client.search(entity_label, lang, type_hint)
            if not raw_data:
                return []
            parsed_data = ResponseParser.parse(api_name, raw_data, self.settings)
            # 为每条候选注入来源 api_name，便于后续按 API 配置输出字段
            try:
                for _it in parsed_data:
                    if isinstance(_it, dict):
                        _it["__api_name"] = api_name
            except Exception:
                pass
            logger.info(f"api_search_ok api={api_name} label={entity_label} count={len(parsed_data)}")
            return parsed_data
        except Exception as e:
            logger.error(f"api_call_failed api={api_name} label={entity_label} err={e}")
            return []
    
    def route_to_api_with_aliases(
        self,
        entity_type: str,
        entity_label: str,
        lang: str = "zh",
        type_hint: Optional[str] = None,
        context_hint: str = "",
        wikipedia_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        路由到对应的API并返回结果，支持别名检索备份机制
        - 先尝试原始标签检索并用 LLM 判定
        - 不匹配或无候选时，基于 Wikipedia 描述触发别名循环检索
        返回统一结构：
        {
            "matched": bool,
            "selected": dict | None,
            "confidence": float,
            "reason": str,
            "alias_used": str | None,
            "alias_attempts": int,
            "model": str | None
        }
        """
        # 1) 原始检索
        original_candidates = self.route_to_api(entity_type, entity_label, lang, type_hint)
        if original_candidates:
            try:
                from ...entity_matcher import judge_best_match
                judge = judge_best_match(
                    label=entity_label,
                    ent_type=entity_type,
                    context_hint=context_hint,
                    source="internal_api",
                    candidates=original_candidates,
                    settings=self.settings,
                )
                if judge.get("matched"):
                    return {
                        "matched": True,
                        "selected": judge.get("selected"),
                        "confidence": judge.get("confidence"),
                        "reason": judge.get("reason"),
                        "alias_used": None,
                        "alias_attempts": 0,
                        "model": judge.get("model"),
                    }
            except Exception as e:
                logger.warning(f"internal_api_llm_judge_failed type={entity_type} label={entity_label} err={e}")
                # 继续进入别名检索作为备份
        
        # 2) 别名检索（基于 Wikipedia 描述）
        try:
            from .alias_search_manager import AliasSearchManager
            alias_manager = AliasSearchManager(self.settings)
            return alias_manager.search_with_aliases(
                entity_label=entity_label,
                entity_type=entity_type,
                context_hint=context_hint,
                wikipedia_data=wikipedia_data,
                api_router=self,
                original_candidates=original_candidates or [],
            )
        except Exception as e:
            logger.error(f"alias_search_integration_failed type={entity_type} label={entity_label} err={e}")
            return {
                "matched": False,
                "selected": None,
                "confidence": 0.0,
                "reason": f"别名检索失败: {e}",
                "alias_used": None,
                "alias_attempts": 0,
                "model": None,
            }