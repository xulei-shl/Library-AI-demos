#!/usr/bin/env python3
"""
WorldCat Entity Search API 示例代码

文档: https://developer.api.oclc.org/entity-search
API Base: https://entities.api.oclc.org/v1/search
"""

import requests
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


class WorldCatEntitySearch:
    """WorldCat 实体搜索 API 客户端"""

    BASE_URL = "https://entities.api.oclc.org/v1/search"

    def __init__(self, api_key: str, api_secret: str):
        """
        初始化客户端

        Args:
            api_key: OCLC API Key
            api_secret: OCLC API Secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self._access_token: Optional[str] = None

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json"
        })

    def _get_access_token(self) -> str:
        """获取 OAuth2 access token"""
        if self._access_token:
            return self._access_token

        response = requests.post(
            "https://oauth.oclc.org/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret,
                "scope": "entity-search"
            }
        )
        response.raise_for_status()
        self._access_token = response.json()["access_token"]
        return self._access_token

    def _request(
        self,
        method: str = "GET",
        endpoint: str = "",
        **kwargs
    ) -> requests.Response:
        """发送请求（带认证）"""
        token = self._get_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers

        url = f"{self.BASE_URL}/{endpoint}".rstrip("/")
        return self.session.request(method, url, **kwargs)

    def search(
        self,
        query: str,
        offset: int = 0,
        limit: int = 10,
        order_by: str = "relevancy",
        facets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        搜索实体

        Args:
            query: 查询关键词，支持 Lucene 语法
            offset: 起始位置（0-based），默认 0
            limit: 返回数量，最大 500，默认 10
            order_by: 排序方式，默认 relevancy
            facets: 分面筛选，如 ["type-25"]

        Returns:
            API 响应字典
        """
        params = {
            "q": query,
            "offset": offset,
            "limit": min(limit, 500),  # 最大 500
            "orderBy": order_by
        }
        if facets:
            params["facets"] = facets

        response = self._request(params=params)
        response.raise_for_status()
        return response.json()

    def search_person(self, name: str, limit: int = 10) -> Dict[str, Any]:
        """
        搜索人物实体

        Args:
            name: 人物名称
            limit: 返回数量

        Returns:
            API 响应字典
        """
        return self.search(f'type:Person AND {name}', limit=limit)

    def search_work(self, title: str, limit: int = 10) -> Dict[str, Any]:
        """
        搜索作品实体

        Args:
            title: 作品标题
            limit: 返回数量

        Returns:
            API 响应字典
        """
        return self.search(f'type:Work AND {title}', limit=limit)


@dataclass
class EntityResult:
    """实体结果数据类"""
    id: str
    types: List[str]
    pref_label: str
    description: Optional[str] = None
    timestamp: Optional[str] = None
    lastrevid: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityResult":
        """从 API 响应创建实体"""
        return cls(
            id=data.get("id", ""),
            types=data.get("type", []),
            pref_label=data.get("prefLabel", {}).get("en", ""),
            description=data.get("description", {}).get("en"),
            timestamp=data.get("timestamp"),
            lastrevid=data.get("lastrevid")
        )


def parse_result(response: Dict[str, Any]) -> List[EntityResult]:
    """解析 API 响应为 EntityResult 列表"""
    return [EntityResult.from_dict(r) for r in response.get("results", [])]


class WorldCatEntityPublic:
    """WorldCat 实体公开访问 API (无需 API Key)

    文档: https://help.oclc.org/Metadata_Services/WorldCat_Entities/WorldCat_Entity_Data/WorldCat_Entities_data

    访问级别: 任何人/未认证 - 有限的实体属性和数据访问
    """

    BASE_URL = "https://id.oclc.org/worldcat/entity"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/ld+json"
        })

    def get_entity(self, entity_id: str) -> Dict[str, Any]:
        """
        获取实体详情 (无需认证)

        Args:
            entity_id: 实体 ID，如 "E39PBJymGv6xMdcX3dQdb48KVC"

        Returns:
            实体数据字典 (JSON-LD 格式)
        """
        url = f"{self.BASE_URL}/{entity_id}.jsonld"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_pref_label(self, entity_id: str, lang: str = "en") -> str:
        """
        获取实体首选标签

        Args:
            entity_id: 实体 ID
            lang: 语言代码，默认 en

        Returns:
            实体标签
        """
        data = self.get_entity(entity_id)
        labels = data.get("prefLabel", {})
        return labels.get(lang, "") or labels.get("en", "")

    def get_description(self, entity_id: str, lang: str = "en") -> Optional[str]:
        """
        获取实体描述

        Args:
            entity_id: 实体 ID
            lang: 语言代码，默认 en

        Returns:
            实体描述
        """
        data = self.get_entity(entity_id)
        descriptions = data.get("description", {})
        return descriptions.get(lang) or descriptions.get("en")


def main_public():
    """公开 API 使用示例 (无需 API Key)"""
    client = WorldCatEntityPublic()

    # 示例: 获取 Ken Burns 的实体信息
    entity_id = "E39PBJymGv6xMdcX3dQdb48KVC"

    print("=" * 50)
    print("公开 API 示例 (无需 API Key)")
    print("=" * 50)

    data = client.get_entity(entity_id)
    print(f"ID: {data.get('id', '')}")
    print(f"标签: {client.get_pref_label(entity_id)}")
    print(f"描述: {client.get_description(entity_id)}")
    print(f"类型: {data.get('type', [])}")


def main():
    """使用示例"""
    # 从环境变量获取认证信息
    API_KEY = "YOUR_API_KEY"
    API_SECRET = "YOUR_API_SECRET"

    client = WorldCatEntitySearch(API_KEY, API_SECRET)

    # 示例 1: 基本搜索
    print("=" * 50)
    print("示例 1: 搜索 'Harry Potter'")
    result = client.search("Harry Potter", limit=3)
    print(f"找到 {result.get('total', 0)} 条记录")
    for entity in parse_result(result):
        print(f"  - {entity.pref_label} ({', '.join(entity.types)})")

    # 示例 2: 使用 Lucene 语法搜索人物
    print("\n" + "=" * 50)
    print("示例 2: 搜索人物 'Jacqueline Woodson'")
    result = client.search_person("Jacqueline Woodson", limit=5)
    print(f"找到 {result.get('total', 0)} 条记录")
    for entity in parse_result(result):
        print(f"  - {entity.pref_label}")
        if entity.description:
            print(f"    描述: {entity.description}")

    # 示例 3: 搜索作品并排序
    print("\n" + "=" * 50)
    print("示例 3: 搜索作品 'Python' 并按标签排序")
    result = client.search_work("Python", limit=5, order_by="labelAsc")
    print(f"找到 {result.get('total', 0)} 条记录")
    for entity in parse_result(result):
        print(f"  - {entity.pref_label}")

    # 示例 4: 带分面搜索
    print("\n" + "=" * 50)
    print("示例 4: 带分面统计搜索")
    result = client.search("Java", limit=10, facets=["type-25"])
    print(f"找到 {result.get('total', 0)} 条记录")
    facets = result.get("facets", {}).get("type_facet", [])
    if facets:
        print("  类型分布:")
        for f in facets:
            for key, value in f.items():
                print(f"    {key}: {value}")


if __name__ == "__main__":
    main()

