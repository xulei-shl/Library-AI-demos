#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISBN补充阶段流水线.

在数据库查重阶段之后,对ISBN为空且状态为"待处理"的记录进行补充检索.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any, Dict

from .base import PipelineStep, StageContext
from src.utils.logger import get_logger
from src.core.douban.isbn_processor_config import (
    ProcessingConfig,
    get_config,
    load_config_from_yaml,
)

logger = get_logger(__name__)


class ISBNSupplementStep(PipelineStep):
    """ISBN补充步骤 - 在豆瓣处理前补充缺失的ISBN"""
    
    name = "isbn_supplement"
    
    def __init__(self, min_threshold: int = 5):
        """
        初始化ISBN补充步骤
        
        Args:
            min_threshold: 最小阈值,只有当需要补充的记录数>=此值时才启动FOLIO处理器
        """
        self.min_threshold = min_threshold
    
    def run(self, context: StageContext) -> Dict[str, int]:
        """
        执行ISBN补充逻辑
        
        Returns:
            统计信息字典
        """
        df = context.df
        progress = context.progress_manager
        isbn_column = context.isbn_column
        barcode_column = context.barcode_column
        
        logger.info("=" * 80)
        logger.info("[ISBN补充] 开始检查需要补充ISBN的记录")
        logger.info("=" * 80)
        
        # 筛选需要补充ISBN的行: ISBN为空 且 状态为"待处理"
        indices_to_process = []
        for index, row in df.iterrows():
            # 检查ISBN是否为空
            isbn_value = str(row.get(isbn_column, "") or "").strip()
            if isbn_value and isbn_value.lower() not in ["nan", "", "获取失败"]:
                continue
            
            # 检查状态是否为"待处理"
            status = progress.row_status(df, index)
            if status != progress.STATUS_PENDING:
                continue
            
            # 检查是否有条码
            barcode = str(row.get(barcode_column, "") or "").strip()
            if not barcode or barcode.lower() == "nan":
                continue
            
            indices_to_process.append(index)
        
        if not indices_to_process:
            logger.info("[ISBN补充] 无需补充ISBN的记录")
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0
            }
        
        logger.info(f"[ISBN补充] 发现 {len(indices_to_process)} 条记录需要补充ISBN")
        
        # 检查是否达到最小阈值
        if len(indices_to_process) < self.min_threshold:
            logger.info(
                f"[ISBN补充] 需要补充的记录数({len(indices_to_process)}) "
                f"< 最小阈值({self.min_threshold}),跳过FOLIO检索"
            )
            return {
                "total": len(indices_to_process),
                "success": 0,
                "failed": 0,
                "skipped": len(indices_to_process)
            }
        
        # 调用FOLIO ISBN处理器
        try:
            from src.core.douban.folio_isbn_async_processor import ISBNAsyncProcessor
            
            # 获取配置
            douban_config = context.douban_config or {}
            isbn_config = douban_config.get('isbn_processor', {}) or {}
            processing_config = self._resolve_processing_config(isbn_config)
            
            # 创建处理器
            processor = ISBNAsyncProcessor(
                processing_config=processing_config,
                enable_database=False  # 补充阶段不使用数据库
            )
            
            # 获取partial文件路径
            partial_path = str(progress.partial_path)
            
            logger.info(f"[ISBN补充] 开始调用FOLIO处理器,处理 {len(indices_to_process)} 条记录")
            
            # 异步调用处理器
            _, stats = asyncio.run(processor.process_excel_file(
                excel_file_path=partial_path,
                barcode_column=barcode_column,
                output_column=isbn_column,
                retry_failed=True,
                target_indices=indices_to_process
            ))
            
            logger.info("[ISBN补充] FOLIO处理完成,开始更新状态")
            
            # 重新加载DataFrame(因为处理器会修改Excel文件)
            import pandas as pd
            df_updated = pd.read_excel(partial_path)
            
            # 更新状态: 成功获取ISBN的改为"待补链接",失败的保持"待处理"
            success_count = 0
            failed_count = 0
            
            for index in indices_to_process:
                isbn_value = str(df_updated.at[index, isbn_column] or "").strip()
                
                if isbn_value and isbn_value not in ["", "nan", "获取失败"]:
                    # 成功获取ISBN,标记为"待补链接"
                    progress.mark_link_pending(df, index)
                    # 同步到df
                    for col in df.columns:
                        df.at[index, col] = df_updated.at[index, col]
                    success_count += 1
                    logger.debug(f"[ISBN补充] 行{index+1}: 成功获取ISBN={isbn_value},状态改为'待补链接'")
                else:
                    # 仍然失败,保持"待处理"状态
                    failed_count += 1
                    logger.debug(f"[ISBN补充] 行{index+1}: 未能获取ISBN,保持'待处理'状态")
            
            # 保存更新后的状态
            progress.save_partial(df, force=True, reason="isbn_supplement")
            
            logger.info("=" * 80)
            logger.info("[ISBN补充] 处理完成:")
            logger.info(f"  总记录数: {len(indices_to_process)}")
            logger.info(f"  成功获取: {success_count}")
            logger.info(f"  仍然失败: {failed_count}")
            logger.info("=" * 80)
            
            return {
                "total": len(indices_to_process),
                "success": success_count,
                "failed": failed_count,
                "skipped": 0
            }
            
        except Exception as e:
            logger.error(f"[ISBN补充] 处理失败: {e}", exc_info=True)
            return {
                "total": len(indices_to_process),
                "success": 0,
                "failed": len(indices_to_process),
                "skipped": 0
            }

    def _resolve_processing_config(self, isbn_config: Dict[str, Any]) -> ProcessingConfig:
        """
        根据配置字典构建 ProcessingConfig，优先复用全局配置策略
        """
        raw_config = isbn_config or {}
        config = load_config_from_yaml(raw_config) or get_config("balanced")
        override_fields = (
            "max_concurrent",
            "batch_size",
            "min_delay",
            "max_delay",
            "retry_times",
            "timeout",
            "browser_startup_timeout",
            "page_navigation_timeout",
        )
        overrides: Dict[str, Any] = {}
        for field in override_fields:
            if field in raw_config and raw_config[field] is not None:
                overrides[field] = raw_config[field]
        if overrides:
            config = replace(config, **overrides)
        return config
