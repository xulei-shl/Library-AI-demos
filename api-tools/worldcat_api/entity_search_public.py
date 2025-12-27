#!/usr/bin/env python3
"""
WorldCat Entity Search API 示例代码

文档: https://developer.api.oclc.org/entity-search
API Base: https://entities.api.oclc.org/v1/search

可以通过wikidata获取到的实体ID。
"""

import requests
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


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


def main():
    """公开 API 使用示例 (无需 API Key)"""
    client = WorldCatEntityPublic()

    entity_id = "E39PBJyxcBcMRqT6cwvv6WWhpP"

    print("=" * 50)
    print("公开 API 示例 (无需 API Key)")
    print("=" * 50)
    data = client.get_entity(entity_id)
    print("=" * 50)
    print(data)
    print("=" * 50)

    print(f"ID: {data.get('id', '')}")
    print(f"标签: {client.get_pref_label(entity_id)}")
    print(f"描述: {client.get_description(entity_id)}")
    print(f"类型: {data.get('type', [])}")

if __name__ == "__main__":
    main()

