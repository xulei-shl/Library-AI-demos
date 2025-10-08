from typing import Any, Dict
from .base import InternalAPIRouter, ResponseParser
from .person_api import PersonAPIClient
from .place_api import PlaceAPIClient
from .organization_api import OrganizationAPIClient
from .event_api import EventAPIClient
from .work_api import WorkAPIClient
from .architecture_api import TheaterAPIClient

class InternalAPIRegistry:
    """内部API注册表"""
    
    _clients: Dict[str, Any] = {}
    _initialized = False
    
    @classmethod
    def register(cls, api_name: str, client) -> None:
        """注册API客户端"""
        cls._clients[api_name] = client
    
    @classmethod
    def get_client(cls, api_name: str):
        """获取API客户端"""
        return cls._clients.get(api_name)
    
    @classmethod
    def initialize_from_settings(cls, settings: Dict[str, Any]) -> None:
        """从配置初始化所有API客户端"""
        if cls._initialized:
            return
            
        # 从新的统一配置结构中获取所有启用的内部API
        tools_config = settings.get("tools", {})
        
        for api_name, api_config in tools_config.items():
            if api_name.endswith("_api") and isinstance(api_config, dict):
                # 只初始化启用的API
                if api_config.get("enabled", False):
                    if api_name == "person_api":
                        cls.register(api_name, PersonAPIClient(api_name, settings))
                    elif api_name == "place_api":
                        cls.register(api_name, PlaceAPIClient(api_name, settings))
                    elif api_name == "organization_api":
                        cls.register(api_name, OrganizationAPIClient(api_name, settings))
                    elif api_name == "event_api":
                        cls.register(api_name, EventAPIClient(api_name, settings))
                    elif api_name == "work_api":
                        cls.register(api_name, WorkAPIClient(api_name, settings))
                    elif api_name == "architecture_api":
                        cls.register(api_name, TheaterAPIClient(api_name, settings))
        
        cls._initialized = True

__all__ = [
    'InternalAPIRouter',
    'ResponseParser',
    'InternalAPIRegistry',
    'PersonAPIClient',
    'PlaceAPIClient',
    'OrganizationAPIClient',
    'EventAPIClient',
    'WorkAPIClient',
    'TheaterAPIClient'
]