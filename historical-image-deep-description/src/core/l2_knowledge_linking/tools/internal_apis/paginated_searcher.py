"""
通用分页搜索器 - 为内部API提供分页搜索和智能LLM匹配判断能力

该模块实现了通用的分页搜索功能，支持：
1. 循环调用API的不同页面
2. 每页结果立即进行LLM匹配判断
3. 找到高置信度匹配时立即停止（早停机制）
4. 完整的错误处理和重试逻辑
5. 详细的日志记录和性能监控
"""

import time
from typing import Any, Dict, List, Optional, Protocol
from .....utils.logger import get_logger
from .base import ResponseParser

logger = get_logger(__name__)


class APIClientProtocol(Protocol):
    """API客户端协议，定义分页搜索所需的接口"""
    
    def search(self, entity_label: str, lang: str = "zh", type_hint: Optional[str] = None) -> Any:
        """标准搜索方法"""
        ...
    
    def _make_request(self, url: str, params: Dict[str, Any]) -> Any:
        """HTTP请求方法"""
        ...
    
    @property
    def api_name(self) -> str:
        """API名称"""
        ...
    
    @property
    def api_config(self) -> Dict[str, Any]:
        """API配置"""
        ...
    
    @property
    def settings(self) -> Dict[str, Any]:
        """全局设置"""
        ...


class PaginatedAPISearcher:
    """通用分页搜索器"""
    
    def __init__(self, api_client: APIClientProtocol, pagination_config: Dict[str, Any], settings: Dict[str, Any]):
        """
        初始化分页搜索器
        
        Args:
            api_client: API客户端实例
            pagination_config: 分页配置
            settings: 全局设置
        """
        self.api_client = api_client
        self.pagination_config = pagination_config
        self.settings = settings
        
        # 提取分页配置参数
        self.page_size = int(pagination_config.get("page_size", 50))
        self.max_pages = int(pagination_config.get("max_pages", 10))
        self.early_stop = pagination_config.get("early_stop", True)
        self.min_confidence = float(pagination_config.get("min_confidence", 0.7))
        self.rate_limit_ms = int(pagination_config.get("rate_limit_ms", 1000))
        
        logger.info(f"paginated_searcher_initialized api={api_client.api_name} page_size={self.page_size} max_pages={self.max_pages} early_stop={self.early_stop}")
    
    def search_with_llm_judgment(
        self,
        entity_label: str,
        entity_type: str,
        context_hint: str = "",
        lang: str = "zh",
        type_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行分页搜索并进行LLM匹配判断
        
        Args:
            entity_label: 实体标签
            entity_type: 实体类型
            context_hint: 上下文提示
            lang: 语言
            type_hint: 类型提示
        
        Returns:
            匹配结果字典，格式：
            {
                "matched": bool,
                "selected": dict | None,
                "confidence": float,
                "reason": str,
                "page_found": int | None,
                "total_pages_searched": int,
                "total_candidates": int,
                "model": str | None
            }
        """
        api_name = self.api_client.api_name
        start_time = time.time()
        total_candidates = 0
        
        logger.info(f"paginated_search_start api={api_name} label={entity_label} type={entity_type} max_pages={self.max_pages}")
        
        for page in range(1, self.max_pages + 1):
            try:
                # 搜索当前页
                page_candidates = self._search_single_page(entity_label, page, lang, type_hint)
                if not page_candidates:
                    logger.info(f"paginated_search_empty_page api={api_name} label={entity_label} page={page}")
                    # 空页面通常意味着没有更多数据，可以提前终止
                    break
                
                total_candidates += len(page_candidates)
                logger.info(f"paginated_search_page_result api={api_name} label={entity_label} page={page} candidates_count={len(page_candidates)}")
                
                # 如果启用早停，立即进行LLM判断
                if self.early_stop:
                    judgment = self._judge_candidates(page_candidates, entity_label, entity_type, context_hint)
                    
                    if judgment.get("matched", False) and judgment.get("confidence", 0) >= self.min_confidence:
                        # 找到高置信度匹配，立即返回
                        elapsed = time.time() - start_time
                        result = {
                            "matched": True,
                            "selected": judgment.get("selected"),
                            "confidence": judgment.get("confidence"),
                            "reason": judgment.get("reason"),
                            "page_found": page,
                            "total_pages_searched": page,
                            "total_candidates": total_candidates,
                            "model": judgment.get("model"),
                            "search_time_ms": int(elapsed * 1000)
                        }
                        logger.info(f"paginated_search_early_stop api={api_name} label={entity_label} page={page} confidence={judgment.get('confidence')} time_ms={int(elapsed * 1000)}")
                        return result
                
                # 页面间延时，避免API速率限制
                if page < self.max_pages and self.rate_limit_ms > 0:
                    time.sleep(self.rate_limit_ms / 1000.0)
                    
            except Exception as e:
                logger.error(f"paginated_search_page_error api={api_name} label={entity_label} page={page} error={e}")
                # 单页失败不影响后续页面搜索
                continue
        
        # 所有页面搜索完毕，如果未启用早停或未找到匹配，则对所有候选进行最终判断
        if not self.early_stop and total_candidates > 0:
            # 收集所有页面的候选（重新搜索，实际应用中可考虑缓存优化）
            all_candidates = []
            for page in range(1, min(self.max_pages + 1, 11)):  # 限制重新搜索的页数
                try:
                    page_candidates = self._search_single_page(entity_label, page, lang, type_hint)
                    if not page_candidates:
                        break
                    all_candidates.extend(page_candidates)
                except Exception:
                    continue
            
            if all_candidates:
                judgment = self._judge_candidates(all_candidates, entity_label, entity_type, context_hint)
                elapsed = time.time() - start_time
                result = {
                    "matched": judgment.get("matched", False),
                    "selected": judgment.get("selected"),
                    "confidence": judgment.get("confidence", 0.0),
                    "reason": judgment.get("reason", ""),
                    "page_found": None,
                    "total_pages_searched": self.max_pages,
                    "total_candidates": len(all_candidates),
                    "model": judgment.get("model"),
                    "search_time_ms": int(elapsed * 1000)
                }
                logger.info(f"paginated_search_final_judgment api={api_name} label={entity_label} matched={judgment.get('matched')} confidence={judgment.get('confidence')} time_ms={int(elapsed * 1000)}")
                return result
        
        # 未找到任何匹配
        elapsed = time.time() - start_time
        result = {
            "matched": False,
            "selected": None,
            "confidence": 0.0,
            "reason": "在所有页面中未找到匹配的候选",
            "page_found": None,
            "total_pages_searched": self.max_pages,
            "total_candidates": total_candidates,
            "model": None,
            "search_time_ms": int(elapsed * 1000)
        }
        logger.info(f"paginated_search_no_match api={api_name} label={entity_label} pages_searched={self.max_pages} total_candidates={total_candidates} time_ms={int(elapsed * 1000)}")
        return result
    
    def _search_single_page(self, entity_label: str, page: int, lang: str, type_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索指定页面
        
        Args:
            entity_label: 实体标签
            page: 页码
            lang: 语言
            type_hint: 类型提示
        
        Returns:
            该页的候选列表
        """
        try:
            # 构建分页请求参数
            api_url = self.api_client.api_config.get("url")
            api_key = self.api_client.api_config.get("key", "")
            
            # 处理环境变量引用
            from .....utils.llm_api import _resolve_env
            api_key = _resolve_env(api_key)
            
            if not api_url or not api_key:
                logger.warning(f"paginated_search_missing_config api={self.api_client.api_name}")
                return []
            
            # 根据API类型构建参数
            params = self._build_api_params(entity_label, page, api_key)
            
            # 发起请求
            raw_data = self.api_client._make_request(api_url, params)
            if not raw_data:
                return []
            
            # 解析响应
            parsed_data = ResponseParser.parse(self.api_client.api_name, raw_data, self.settings)
            
            # 为每条候选注入API名称
            for item in parsed_data:
                if isinstance(item, dict):
                    item["__api_name"] = self.api_client.api_name
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"paginated_search_single_page_error api={self.api_client.api_name} page={page} error={e}")
            return []
    
    def _build_api_params(self, entity_label: str, page: int, api_key: str) -> Dict[str, Any]:
        """
        根据API类型构建请求参数
        
        Args:
            entity_label: 实体标签
            page: 页码
            api_key: API密钥
        
        Returns:
            请求参数字典
        """
        api_name = self.api_client.api_name
        
        base_params = {
            "key": api_key,
            "pageSize": self.page_size,
            "pageth": page
        }
        
        # 根据不同API类型设置搜索参数
        if api_name == "person_api":
            base_params["name"] = entity_label
        elif api_name == "work_api":
            base_params["title"] = entity_label  # 修正：使用title而非freetext
        elif api_name in ["organization_api", "architecture_api"]:
            base_params["freetext"] = entity_label
        else:
            # 默认使用freetext参数
            base_params["freetext"] = entity_label
        
        return base_params
    
    def _judge_candidates(self, candidates: List[Dict[str, Any]], entity_label: str, entity_type: str, context_hint: str) -> Dict[str, Any]:
        """
        使用LLM判断候选匹配
        
        Args:
            candidates: 候选列表
            entity_label: 实体标签
            entity_type: 实体类型
            context_hint: 上下文提示
        
        Returns:
            LLM判断结果
        """
        try:
            from ...entity_matcher import judge_best_match
            
            judgment = judge_best_match(
                label=entity_label,
                ent_type=entity_type,
                context_hint=context_hint,
                source="internal_api",
                candidates=candidates,
                settings=self.settings
            )
            
            return judgment
            
        except Exception as e:
            logger.error(f"paginated_search_llm_judgment_error api={self.api_client.api_name} label={entity_label} error={e}")
            return {
                "matched": False,
                "selected": None,
                "confidence": 0.0,
                "reason": f"LLM判断失败: {e}",
                "model": None
            }