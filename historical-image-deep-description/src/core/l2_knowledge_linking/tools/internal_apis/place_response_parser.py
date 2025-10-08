"""
地点API响应解析器

目标：
- 仅提取简体中文(chs)的 label/country 值
- 兼容两种返回格式：
  1) 直接返回地点对象（官方文档 docs/tools/地点-地名API.md）
  2) 包裹在 {"result": {"data": "<json字符串>"}} 的变体
- 输出字段遵循 tools.place_api.fields.mapping（label, city, country, province, county, uri）
"""

from typing import Any, Dict, List, Optional
import json
from .....utils.logger import get_logger

logger = get_logger(__name__)


class PlaceResponseParser:
    """地点API专用响应解析器"""

    @staticmethod
    def parse(raw_data: Any, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析地点API响应数据

        返回：
            List[Dict[str, Any]]: 标准化候选列表，其中每个元素包含：
                - label: 简体中文地名（chs）
                - city: 城市
                - country: 简体中文国家名（chs）
                - province: 省份
                - county: 县/区
                - uri: @id 映射
                - _raw: 原始对象
        """
        if not raw_data:
            return []

        # 兼容变体：{"result": {"data": "<json字符串>"}} 或 {"result": {"data": {...}}}
        try:
            if isinstance(raw_data, dict) and "result" in raw_data:
                res = raw_data.get("result")
                if isinstance(res, dict) and "data" in res:
                    data_obj = res.get("data")
                    if isinstance(data_obj, str):
                        try:
                            raw_data = json.loads(data_obj)
                        except Exception as e:
                            logger.warning(f"place_api_json_string_parse_failed err={e}")
                            return []
                    elif isinstance(data_obj, dict):
                        raw_data = data_obj
        except Exception as e:
            logger.warning(f"place_api_result_wrapper_parse_failed err={e}")
            return []

        if not isinstance(raw_data, dict):
            logger.warning("place_api_invalid_root_type")
            return []

        try:
            parsed: Dict[str, Any] = {}

            # label: list of {"@language": "...", "@value": "..."}
            labels = raw_data.get("label")
            if isinstance(labels, list):
                chs_label = PlaceResponseParser._pick_lang_value(labels, "chs")
                if chs_label:
                    parsed["label"] = chs_label

            # country: list of {"@language": "...", "@value": "..."}
            countries = raw_data.get("country")
            if isinstance(countries, list):
                chs_country = PlaceResponseParser._pick_lang_value(countries, "chs")
                if chs_country:
                    parsed["country"] = chs_country

            # 直接拷贝简单字面字段
            for k in ("city", "province", "county"):
                v = raw_data.get(k)
                if isinstance(v, str) and v:
                    parsed[k] = v

            # @id -> uri
            at_id = raw_data.get("@id")
            if isinstance(at_id, str) and at_id:
                parsed["uri"] = at_id

            if not parsed:
                return []

            # 附带原始
            parsed["_raw"] = raw_data
            return [parsed]
        except Exception as e:
            logger.warning(f"place_api_parse_failed err={e}")
            return []

    @staticmethod
    def _pick_lang_value(arr: List[Dict[str, Any]], lang: str = "chs") -> Optional[str]:
        """
        从形如 [{"@language": "chs", "@value": "上海"}, ...] 的数组中挑选指定语言的值
        """
        if not isinstance(arr, list):
            return None
        for it in arr:
            if not isinstance(it, dict):
                continue
            if it.get("@language") == lang:
                val = it.get("@value")
                if isinstance(val, str) and val.strip():
                    return val.strip()
        return None