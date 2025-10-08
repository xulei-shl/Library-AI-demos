from typing import Any, Dict, List, Optional
from .base import InternalAPIClient
from .....utils.llm_api import _resolve_env
from .....utils.logger import get_logger

logger = get_logger(__name__)

class EventAPIClient(InternalAPIClient):
    """事件API客户端"""
    
    def search(self, entity_label: str, lang: str = "zh", type_hint: Optional[str] = None) -> Any:
        """搜索事件信息"""
        api_url = self.api_config.get("url")
        api_key = _resolve_env(self.api_config.get("key", ""))
        limit = int(self.api_config.get("limit", 5))
        
        if not api_url or not api_key:
            logger.warning("event_api_missing_config")
            return None
        
        params = {
            "eventFreeText": entity_label,
            "key": api_key,
            "pageSize": limit,
            "pageth": 1
        }
        
        return self._make_request(api_url, params)