from typing import Any, Dict, List, Optional
from .base import InternalAPIClient
from .....utils.llm_api import _resolve_env
from .....utils.logger import get_logger
from urllib.parse import quote

logger = get_logger(__name__)

class PlaceAPIClient(InternalAPIClient):
    """地点API客户端"""
    
    def search(self, entity_label: str, lang: str = "zh", type_hint: Optional[str] = None) -> Any:
        """搜索地点信息"""
        api_url_template = self.api_config.get("url_template", "http://data1.library.sh.cn/place/{place}?key={key}")
        api_key = _resolve_env(self.api_config.get("key", ""))
        
        if not api_key:
            logger.warning("place_api_missing_config")
            return None
        
        # 路径参数需要URL编码以兼容中文（如“杞县”）
        encoded_place = quote(entity_label, safe="")
        api_url = api_url_template.format(place=encoded_place, key=api_key)
        return self._make_request(api_url, {})