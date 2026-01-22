"""
请求模型
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class FilterCondition(BaseModel):
    """过滤条件"""

    field: str = Field(..., description="字段名：reading_context/reading_load/text_texture/spatial_atmosphere/emotional_tone")
    values: List[str] = Field(..., min_items=1, description="字段值列表")
    operator: str = Field(..., description="操作符：MUST/SHOULD/MUST_NOT")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        """验证操作符"""
        valid_operators = {"MUST", "SHOULD", "MUST_NOT"}
        if v not in valid_operators:
            raise ValueError(f"operator 必须是 {valid_operators} 之一")
        return v

    @field_validator("field")
    @classmethod
    def validate_field(cls, v: str) -> str:
        """验证字段名"""
        valid_fields = {
            "reading_context",
            "reading_load",
            "text_texture",
            "spatial_atmosphere",
            "emotional_tone"
        }
        if v not in valid_fields:
            raise ValueError(f"field 必须是 {valid_fields} 之一")
        return v


class SearchRequest(BaseModel):
    """单主题检索请求"""

    filter_conditions: List[FilterCondition] = Field(default_factory=list, description="结构化过滤条件")
    search_keywords: List[str] = Field(..., min_items=1, description="BM25检索关键词")
    synthetic_query: str = Field(..., min_length=1, description="向量检索的合成查询词")
    top_k: int = Field(default=30, gt=0, description="返回结果数量")
    min_confidence: float = Field(default=0.75, ge=0, le=1, description="最小置信度阈值")
    response_detail: str = Field(default="standard", description="响应详细程度：basic/standard/rich")
    enable_rerank: bool = Field(default=False, description="是否启用重排序")
    bm25_randomness: float = Field(default=0.15, ge=0, le=1, description="BM25随机性因子")

    @field_validator("response_detail")
    @classmethod
    def validate_response_detail(cls, v: str) -> str:
        """验证响应详细程度"""
        valid_levels = {"basic", "standard", "rich"}
        if v not in valid_levels:
            raise ValueError(f"response_detail 必须是 {valid_levels} 之一")
        return v


class QueryItem(BaseModel):
    """批量检索中的单个查询项"""

    filter_conditions: List[FilterCondition] = Field(default_factory=list, description="结构化过滤条件")
    search_keywords: List[str] = Field(..., min_items=1, description="BM25检索关键词")
    synthetic_query: str = Field(..., min_length=1, description="向量检索的合成查询词")


class BatchSearchRequest(BaseModel):
    """批量主题检索请求"""

    queries: List[QueryItem] = Field(..., min_items=1, description="查询列表")
    top_k: int = Field(default=30, gt=0, description="每个查询返回结果数量")
    response_detail: str = Field(default="standard", description="响应详细程度：basic/standard/rich")
    enable_rerank: bool = Field(default=False, description="是否启用重排序")

    @field_validator("response_detail")
    @classmethod
    def validate_response_detail(cls, v: str) -> str:
        """验证响应详细程度"""
        valid_levels = {"basic", "standard", "rich"}
        if v not in valid_levels:
            raise ValueError(f"response_detail 必须是 {valid_levels} 之一")
        return v
