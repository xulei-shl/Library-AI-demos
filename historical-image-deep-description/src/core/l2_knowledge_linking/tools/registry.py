from typing import Any, Callable, Dict, Optional

from .wikidata_tool import search_wikidata
from .wikipedia_tool import search_wikipedia
from .internal_apis import InternalAPIRegistry, InternalAPIRouter

TOOL_REGISTRY: Dict[str, Callable[..., object]] = {
    "wikidata": search_wikidata,
    "wikipedia": search_wikipedia,
}

def get_tool(name: str) -> Optional[Callable[..., object]]:
    """
    获取工具函数；若未注册则返回 None。
    """
    return TOOL_REGISTRY.get(name)

def initialize_internal_apis(settings: Dict[str, Any]) -> None:
    """初始化内部API"""
    InternalAPIRegistry.initialize_from_settings(settings)

def get_internal_api_router(settings: Dict[str, Any]) -> InternalAPIRouter:
    """获取内部API路由器"""
    return InternalAPIRouter(settings)