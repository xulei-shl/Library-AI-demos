"""
响应模型
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BookResult(BaseModel):
    """单本书籍的检索结果"""

    book_id: int = Field(..., description="书籍ID")
    title: str = Field(..., description="书名")
    author: str = Field(..., description="作者")
    call_no: str = Field(..., description="索书号")
    vector_score: Optional[float] = Field(default=None, description="向量检索分数")
    bm25_score: Optional[float] = Field(default=None, description="BM25检索分数")
    rrf_score: Optional[float] = Field(default=None, description="RRF融合分数")
    sources: List[str] = Field(default_factory=list, description="结果来源：vector/bm25")
    tags_json: Optional[str] = Field(default=None, description="文学标签JSON")


class RetrievalStats(BaseModel):
    """检索统计信息"""

    vector_count: int = Field(..., description="向量检索召回数量")
    bm25_count: int = Field(..., description="BM25检索召回数量")
    final_count: int = Field(..., description="最终返回数量")


class SearchMetadata(BaseModel):
    """检索元数据"""

    total_count: int = Field(..., description="返回结果总数")
    filter_conditions_applied: Optional[List[Dict[str, Any]]] = Field(default=None, description="应用的过滤条件")
    retrieval_stats: Optional[RetrievalStats] = Field(default=None, description="检索统计信息")


class SearchResponse(BaseModel):
    """检索响应"""

    results: List[BookResult] = Field(..., description="检索结果列表")
    metadata: SearchMetadata = Field(..., description="检索元数据")


class BatchSearchResponse(BaseModel):
    """批量检索响应"""

    results: List[List[BookResult]] = Field(..., description="每个查询的检索结果列表")
    metadata_list: List[SearchMetadata] = Field(..., description="每个查询的元数据")
