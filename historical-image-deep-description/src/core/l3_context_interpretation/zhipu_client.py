"""
智谱AI搜索客户端

提供对智谱AI Web搜索API的封装，支持基于实体标签的网络搜索功能。
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ...utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ZhipuSearchResponse:
    """智谱AI搜索响应数据类"""
    success: bool
    results: List[Dict[str, Any]]
    total_count: int
    query: str
    error: Optional[str] = None
    
    
class ZhipuClient:
    """
    智谱AI搜索客户端
    
    负责与智谱AI Web搜索API的交互，提供简单的搜索功能封装。
    """
    
    def __init__(self, api_key: str, search_config: Dict[str, Any]):
        """
        初始化智谱AI客户端
        
        Args:
            api_key: 智谱AI API密钥
            search_config: 搜索配置参数
        """
        self.api_key = api_key
        self.search_config = search_config
        self._client = None
        
        logger.info(f"初始化智谱AI客户端 engine={search_config.get('search_engine', 'search_pro')}")
    
    def _get_client(self):
        """懒加载智谱AI客户端"""
        if self._client is None:
            try:
                from zai import ZhipuAiClient
                self._client = ZhipuAiClient(api_key=self.api_key)
                logger.debug("智谱AI客户端初始化成功")
            except ImportError:
                logger.error("智谱AI SDK未安装，请运行: pip install zai")
                raise
            except Exception as e:
                logger.error(f"智谱AI客户端初始化失败: {e}")
                raise
        return self._client
    
    def search_entity(self, label: str) -> ZhipuSearchResponse:
        """
        搜索实体相关信息
        
        Args:
            label: 实体标签，直接作为搜索查询词
            
        Returns:
            ZhipuSearchResponse: 搜索响应结果
        """
        try:
            client = self._get_client()
            
            # 构建搜索参数
            search_params = {
                "search_engine": self.search_config.get("search_engine", "search_pro"),
                "search_query": label,
                "count": self.search_config.get("count", 15),
                "search_recency_filter": self.search_config.get("search_recency_filter", "noLimit"),
                "content_size": self.search_config.get("content_size", "high")
            }
            
            logger.info(f"开始智谱AI搜索 query='{label}' count={search_params['count']}")
            
            # 调用搜索API
            response = client.web_search.web_search(**search_params)
            
            # 解析响应
            if hasattr(response, 'search_result') and response.search_result:
                results = response.search_result if isinstance(response.search_result, list) else [response.search_result]
                total_count = len(results)
                
                logger.info(f"智谱AI搜索成功 query='{label}' results_count={total_count}")
                
                # 将搜索结果转换为字典格式，便于后续处理
                formatted_results = []
                for result in results:
                    if hasattr(result, '__dict__'):
                        # 将SearchResultResp对象转换为字典
                        result_dict = {
                            'title': getattr(result, 'title', ''),
                            'content': getattr(result, 'content', ''),
                            'link': getattr(result, 'link', ''),
                            'media': getattr(result, 'media', ''),
                            'publish_date': getattr(result, 'publish_date', ''),
                            'refer': getattr(result, 'refer', '')
                        }
                        formatted_results.append(result_dict)
                    else:
                        formatted_results.append(result)
                
                return ZhipuSearchResponse(
                    success=True,
                    results=formatted_results,
                    total_count=total_count,
                    query=label
                )
            else:
                logger.warning(f"智谱AI搜索无结果 query='{label}'")
                return ZhipuSearchResponse(
                    success=True,
                    results=[],
                    total_count=0,
                    query=label
                )
                
        except Exception as e:
            error_msg = f"智谱AI搜索异常: {str(e)}"
            logger.error(f"智谱AI搜索失败 query='{label}' error={error_msg}")
            
            return ZhipuSearchResponse(
                success=False,
                results=[],
                total_count=0,
                query=label,
                error=error_msg
            )
    
    def _add_search_delay(self):
        """添加搜索延迟（如果配置了）"""
        delay_ms = self.search_config.get("delay_ms", 1000)
        if delay_ms > 0:
            try:
                time.sleep(delay_ms / 1000.0)
            except Exception:
                pass