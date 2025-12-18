#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FastAPI 图书检索接口。
uvicorn scripts.api.book_retrieval_api:app --reload
"""

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from scripts.api.services import RetrieverService
from src.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="图书检索 API",
    version="1.0.0",
    description="封装文本相似度与多子查询检索能力，供本地应用调用。",
)

service = RetrieverService()


class BaseSearchRequest(BaseModel):
    """通用请求字段。"""

    response_format: str = Field(
        default="json", description="响应格式，可选 json/plain_text"
    )
    plain_text_template: Optional[str] = Field(
        default=None, description="plain_text 模式下的格式模版"
    )
    llm_hint: Optional[Dict[str, Any]] = Field(
        default=None, description="透传给前端的 LLM 提示信息"
    )
    save_to_file: bool = Field(default=False, description="是否落盘输出")

    @model_validator(mode="after")
    def validate_response_format(self) -> "BaseSearchRequest":
        """确保响应格式合法。"""
        fmt = (self.response_format or "json").lower()
        if fmt not in {"json", "plain_text"}:
            raise ValueError("response_format 仅支持 json 或 plain_text")
        self.response_format = fmt
        return self


class TextSearchRequest(BaseSearchRequest):
    """文本检索请求。"""

    query: str = Field(..., min_length=1, description="检索文本")
    top_k: Optional[int] = Field(default=None, gt=0, description="返回数量")
    min_rating: Optional[float] = Field(default=None, description="评分过滤")


class MultiQueryRequest(BaseSearchRequest):
    """多子查询检索请求。"""

    markdown_text: str = Field(..., min_length=1, description="交叉分析 Markdown 文本")
    per_query_top_k: Optional[int] = Field(default=None, gt=0, description="单子查询候选")
    final_top_k: Optional[int] = Field(default=None, gt=0, description="最终返回数量")
    min_rating: Optional[float] = Field(default=None, description="评分过滤")
    enable_rerank: bool = Field(default=False, description="是否启用 Rerank")
    disable_exact_match: bool = Field(default=False, description="禁用精确匹配")


@app.post("/api/books/text-search")
async def text_search(request: TextSearchRequest) -> Dict[str, Any]:
    """文本相似度检索端点。"""
    try:
        logger.info("收到文本检索请求: top_k=%s", request.top_k)
        return service.text_search(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("文本检索失败: %s", exc)
        raise HTTPException(status_code=500, detail="检索失败，请稍后再试") from exc


@app.post("/api/books/multi-query")
async def multi_query(request: MultiQueryRequest) -> Dict[str, Any]:
    """多子查询检索端点。"""
    try:
        logger.info(
            "收到多查询请求: per_query_top_k=%s, final_top_k=%s",
            request.per_query_top_k,
            request.final_top_k,
        )
        return service.multi_query_search(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("多查询检索失败: %s", exc)
        raise HTTPException(status_code=500, detail="检索失败，请稍后再试") from exc
