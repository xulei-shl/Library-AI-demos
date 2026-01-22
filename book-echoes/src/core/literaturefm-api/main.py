#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文学图书检索 API

FastAPI服务，提供基于向量+BM25的混合检索能力

启动命令：
    uvicorn main:app --reload --port 8001
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
# 从 literaturefm-api/main.py 到项目根需要向上5级：
# main.py -> literaturefm-api -> literature_fm -> core -> src -> book-echoes
root_dir = Path(__file__).absolute().parent.parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# 添加当前目录到路径（用于导入models和services）
current_dir = Path(__file__).absolute().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.utils.logger import get_logger
from models.requests import SearchRequest, BatchSearchRequest
from models.responses import SearchResponse, BatchSearchResponse
from services.search_service import LiterarySearchService

logger = get_logger(__name__)

# 全局服务实例
service: LiterarySearchService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    global service
    logger.info("正在初始化文学检索服务...")
    service = LiterarySearchService()
    logger.info("✓ 文学检索服务初始化完成")
    yield
    # 关闭时清理
    logger.info("文学检索服务已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="文学图书检索 API",
    version="1.0.0",
    description="提供基于向量+BM25的混合检索能力，支持结构化过滤条件",
    lifespan=lifespan
)


@app.get("/")
async def root() -> Dict[str, Any]:
    """根路径"""
    return {
        "name": "文学图书检索 API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "单主题检索": "/api/literary/search",
            "批量主题检索": "/api/literary/batch-search",
            "API文档": "/docs"
        }
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    """健康检查"""
    return {"status": "healthy"}


@app.post("/api/literary/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> Dict[str, Any]:
    """
    单主题检索

    执行基于向量+BM25的混合检索，支持结构化过滤条件

    - **filter_conditions**: 结构化过滤条件（MUST/SHOULD/MUST_NOT）
    - **search_keywords**: BM25检索关键词
    - **synthetic_query**: 向量检索的合成查询词
    - **top_k**: 返回结果数量
    - **response_detail**: 响应详细程度（basic/standard/rich）
    - **enable_rerank**: 是否启用重排序
    - **bm25_randomness**: BM25随机性因子（0-1）
    """
    try:
        logger.info(f"收到检索请求: keywords={request.search_keywords[:2]}..., top_k={request.top_k}")
        result = service.search(request)
        return result
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"参数验证失败: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"检索失败: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="检索失败，请稍后再试") from exc


@app.post("/api/literary/batch-search", response_model=BatchSearchResponse)
async def batch_search(request: BatchSearchRequest) -> Dict[str, Any]:
    """
    批量主题检索

    对多个查询执行批量检索，返回每个查询的结果

    - **queries**: 查询列表，每个查询包含 filter_conditions、search_keywords、synthetic_query
    - **top_k**: 每个查询返回结果数量
    - **response_detail**: 响应详细程度（basic/standard/rich）
    - **enable_rerank**: 是否启用重排序
    """
    try:
        logger.info(f"收到批量检索请求: 查询数={len(request.queries)}, top_k={request.top_k}")

        # 转换查询格式
        queries_dict = [
            {
                "filter_conditions": [
                    {"field": fc.field, "values": fc.values, "operator": fc.operator}
                    for fc in query.filter_conditions
                ],
                "search_keywords": query.search_keywords,
                "synthetic_query": query.synthetic_query
            }
            for query in request.queries
        ]

        result = service.batch_search(
            queries=queries_dict,
            top_k=request.top_k,
            response_detail=request.response_detail,
            enable_rerank=request.enable_rerank
        )
        return result
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"参数验证失败: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"批量检索失败: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="批量检索失败，请稍后再试") from exc


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"未捕获的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后再试"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
