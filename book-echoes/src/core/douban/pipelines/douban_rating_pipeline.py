#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""豆瓣评分流水线"""

from __future__ import annotations

import sys

from dataclasses import dataclass

from pathlib import Path

from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from src.utils.config_manager import get_config_manager

from src.utils.logger import get_logger

from src.core.douban.analytics import ThemeRatingAnalyzer

from src.core.douban.analytics.dynamic_threshold_filter import (

    DynamicFilterResult,

    DynamicThresholdFilter,

)

from src.core.douban.progress_manager import ProgressManager

from src.core.douban.report_generator import DoubanReportGenerator

from .base import PipelineStep, StageContext

from .douban_db_stage import DoubanDatabaseStage

from .douban_link_pipeline import DoubanLinkStep

from .douban_subject_pipeline import DoubanSubjectStep

logger = get_logger(__name__)

StepsBuilder = Callable[[StageContext, "DoubanRatingPipelineOptions"], List[PipelineStep]]

@dataclass

class DoubanRatingPipelineOptions:

    excel_file: str

    barcode_column: str = "书目条码"

    isbn_column: str = "ISBN"

    status_column: str = "处理状态"

    link_column: Optional[str] = None

    call_number_column: Optional[str] = "索书号"

    config_name: Optional[str] = None

    username: Optional[str] = None  # 兼容旧接口，当前阶段未使用

    password: Optional[str] = None  # 鍏煎鏃ф帴鍙ｏ紝褰撳墠闃舵鏈娇鐢?

    disable_database: bool = False

    force_update: bool = False

    db_path: Optional[str] = None

    enable_isbn_resolution: bool = False  # 鍏煎鏃LI鍙傛暟

    generate_report: bool = True

    enable_db_stage: bool = True

    enable_link_stage: bool = True

    enable_subject_stage: bool = True

    save_interval: int = 15

    prompt_post_link_action: bool = True

    candidate_column: Optional[str] = "候选状态"

    force_db_stage: bool = False

class DoubanRatingPipeline:

    """阶段化豆瓣评分流水线."""

    CANDIDATE_FLAG_VALUE = "候选"

    def __init__(

        self,

        config_manager=None,

        progress_cls=ProgressManager,

        steps_builder: Optional[StepsBuilder] = None,

    ) -> None:

        self.config_manager = config_manager or get_config_manager()

        self.progress_cls = progress_cls

        self.steps_builder = steps_builder

        self.report_generator = DoubanReportGenerator()

        self.dynamic_filter = DynamicThresholdFilter()

        self.theme_analyzer = ThemeRatingAnalyzer(dynamic_filter=self.dynamic_filter)

    def run(self, options: DoubanRatingPipelineOptions) -> Tuple[str, Dict[str, Any]]:

        excel_path = self._validate_excel(options.excel_file)

        douban_config = self.config_manager.get_douban_config()

        full_config = self.config_manager.get_config()

        field_mapping = (full_config.get("fields_mapping", {}) or {}).get("douban", {})

        if not field_mapping:

            raise ValueError("未找到 fields_mapping.douban 配置")

        progress = self.progress_cls(

            excel_file=str(excel_path),

            status_column=options.status_column,

            save_interval=options.save_interval,

        )

        df = progress.load_dataframe()

        resume_from_partial = False

        db_meta_payload: Optional[Dict[str, Any]] = None

        try:

            if progress.partial_exists():

                resume_from_partial = True

                logger.info(

                    "检测到 partial 进度文件，尝试从断点恢复处理 (force_db_stage=%s)",

                    options.force_db_stage,

                )

                db_meta_payload = progress.load_db_meta()

                if db_meta_payload:

                    logger.info("已加载 DB 元数据缓存，稍后自动刷新到进度文件")

                logger.info("暂停模式下跳过豆瓣任务分析报告生成，待 API 阶段执行完毕再生成最终报告")

            resume_from_partial = False

        except Exception:
            resume_from_partial = False

        link_column = options.link_column or field_mapping.get("url")

        if not link_column:

            raise ValueError("未配置豆瓣链接列 (fields_mapping.douban.url)")

        self._ensure_required_columns(

            df=df,

            field_mapping=field_mapping,

            barcode_column=options.barcode_column,

            isbn_column=options.isbn_column,

            link_column=link_column,

            extra_columns=[options.call_number_column] if options.call_number_column else None,

        )

        if options.candidate_column:

            self._ensure_candidate_column(df, options.candidate_column)

        db_config = self._build_db_config(options)

        context = StageContext(

            df=df,

            progress_manager=progress,

            douban_config=douban_config,

            full_config=full_config,

            field_mapping=field_mapping,

            barcode_column=options.barcode_column,

            isbn_column=options.isbn_column,

            link_column=link_column,

            status_column=options.status_column,

            call_number_column=options.call_number_column,

            candidate_column=options.candidate_column,

            excel_path=excel_path,

        )

        context.extra["db_config"] = db_config

        context.extra["resume_from_partial"] = resume_from_partial

        context.extra["db_stage_light_mode"] = resume_from_partial and not options.force_db_stage

        context.extra["force_db_stage"] = bool(options.force_db_stage)

        if db_meta_payload:

            context.extra["db_meta_payload"] = db_meta_payload

        steps = self._resolve_steps(context, options, db_config)

        stage_stats: Dict[str, Dict[str, Any]] = {}

        link_stage_completed = False

        for step in steps:

            if (

                step.name == DoubanSubjectStep.name

                and options.enable_subject_stage

                and link_stage_completed

            ):

                # 检查是否有行需要 API 处理

                api_needed_count = sum(1 for idx in df.index if progress.needs_api(df, idx))



                if api_needed_count == 0:

                    logger.info("无数据需要调用 Subject API，自动跳过用户交互，继续完成流程")

                    # 不提示用户，直接继续

                else:

                    decision = self._resolve_post_link_decision(context, options)

                    if decision == "stop":

                        logger.info("用户选择停止 Subject API 阶段，流水线提前终止")

                        stage_stats[step.name] = {"skipped": True, "reason": "user_abort_post_link"}

                        context.extra["subject_stage_skipped"] = True

                        context.extra["post_link_user_paused"] = True

                        break

            logger.info("开始执行阶段 %s", step.name)

            step.prepare(context)

            stats = step.run(context) or {}

            stage_stats[step.name] = stats

            step.finalize(context)

            if step.name == DoubanLinkStep.name:

                link_stage_completed = True

                filter_result = self._apply_dynamic_filter(context)

                report_path = self._generate_theme_stats(context)

                if report_path:

                    stats["theme_report_file"] = str(report_path)

                    context.extra["theme_report_file"] = str(report_path)

        # 流水线结束后统一刷写数据库（无论是否调用了 API）

        try:

            for idx in range(len(context.df)):

                context.progress_manager.flush_row_to_database(

                    df=context.df,

                    index=idx,

                    barcode_column=context.barcode_column,

                    isbn_column=context.isbn_column,

                    douban_fields_mapping=context.field_mapping,

                )

        except Exception:

            pass

        if context.extra.get("post_link_user_paused"):

            progress.save_partial(df, force=True, reason="user_pause_post_link")

            pause_stats: Dict[str, Any] = {

                "pipeline": "douban_rating",

                "input_file": str(excel_path),

                "output_file": None,

                "stages": stage_stats,

                "subject_api_skipped": True,

                "paused_after_link": True,

                "partial_file": str(progress.partial_path),

            }

            logger.info(

                            "已根据用户指令暂停 Subject API 阶段，partial 文件保留在 %s",

                            progress.partial_path,

                        )

            if options.generate_report:

                logger.info("暂停模式下跳过豆瓣任务分析报告生成，待 API 阶段执行完毕再生成最终报告")

            return str(progress.partial_path), pause_stats

        progress.save_partial(df, force=True, reason="pipeline_completed")

        output_path = self._build_output_path(excel_path)

        progress.finalize_output(output_path, df)

        stats = self._build_pipeline_stats(stage_stats, excel_path, output_path)

        theme_report_file = context.extra.get("theme_report_file")

        if theme_report_file:

            stats["link_theme_report"] = theme_report_file

        if context.extra.get("subject_stage_skipped"):

            stats["subject_api_skipped"] = True

        if options.generate_report:

            self._try_generate_report(

                df=df,

                options=options,

                stats=stats,

                field_mapping=field_mapping,

                final_excel_path=str(output_path),

                categories=context.extra.get("db_categories"),

            )

        try:

            dbm = context.extra.get("db_manager")

            if dbm and getattr(dbm, "close", None):

                dbm.close()

        except Exception:

            pass

        return str(output_path), stats

    def _apply_dynamic_filter(self, context: StageContext) -> Optional[DynamicFilterResult]:

        if not self.dynamic_filter:

            return None

        self._reset_candidate_flags(context)

        rating_column = context.get_field("rating")

        if not rating_column or rating_column not in context.df.columns:

            logger.info("缺少评分列，跳过动态过滤")

            self._mark_link_rows_ready(context)

            context.progress_manager.save_partial(context.df, reason="dynamic_filter_no_rating")

            context.extra["dynamic_filter_dataset"] = None

            context.extra["dynamic_filter_result"] = None

            return None

        rating_count_column = context.get_field("rating_count")

        if rating_count_column not in context.df.columns:

            rating_count_column = None

        call_column = context.call_number_column

        if not call_column or call_column not in context.df.columns:

            call_column = None

        dataset_full = self.dynamic_filter.prepare_dataset(

            df=context.df,

            rating_column=rating_column,

            call_number_column=call_column,

            rating_count_column=rating_count_column,

        )

        context.extra["dynamic_filter_dataset"] = dataset_full

        if dataset_full.empty:

            logger.info('评分数据不足，所有已获取链接保持"链接已获取"状态')

            self._mark_link_rows_ready(context)

            context.progress_manager.save_partial(

                context.df, reason="dynamic_filter_insufficient"

            )

            context.extra["dynamic_filter_result"] = None

            return None

        # 设置原始DataFrame引用,用于列值验证
        self.dynamic_filter._source_df = context.df
        
        result = self.dynamic_filter.analyze(dataset_full)

        self._update_status_with_filter_result(context, result)

        context.progress_manager.save_partial(context.df, reason="dynamic_filter")

        context.extra["dynamic_filter_result"] = result

        return result

    def _update_status_with_filter_result(

        self,

        context: StageContext,

        result: DynamicFilterResult,

    ) -> None:

        df = context.df

        progress = context.progress_manager

        link_column = context.link_column

        candidate_indexes = result.candidate_indexes

        total_link_rows = 0

        candidate_total = len(candidate_indexes)

        api_candidate_rows = 0

        for idx in df.index:

            is_candidate = idx in candidate_indexes

            self._set_candidate_flag(context, idx, is_candidate)

            link_value = str(df.at[idx, link_column] or "").strip()

            if not link_value:

                continue

            total_link_rows += 1

            if progress.should_skip_barcode(df, idx):

                continue

            if is_candidate:

                progress.mark_api_pending(df, idx)

                api_candidate_rows += 1

            else:

                progress.mark_link_ready(df, idx)

        logger.info(

            "动态过滤完成：候选 %s / 已获取链接 %s（待补 API %s）",

            candidate_total,

            total_link_rows,

            api_candidate_rows,

        )

    def _mark_link_rows_ready(self, context: StageContext) -> None:

        self._reset_candidate_flags(context)

        df = context.df

        progress = context.progress_manager

        link_column = context.link_column

        for idx in df.index:

            if progress.should_skip_barcode(df, idx):

                continue

            link_value = str(df.at[idx, link_column] or "").strip()

            if not link_value:

                continue

            progress.mark_link_ready(df, idx)

    def _reset_candidate_flags(self, context: StageContext) -> None:

        column = context.candidate_column

        if not column or column not in context.df.columns:

            return

        try:

            context.df[column] = ""

        except Exception:

            context.df[column] = ""

    def _set_candidate_flag(

        self,

        context: StageContext,

        index: int,

        is_candidate: bool,

    ) -> None:

        column = context.candidate_column

        if not column or column not in context.df.columns:

            return

        value = self.CANDIDATE_FLAG_VALUE if is_candidate else ""

        context.df.at[index, column] = value

    def _generate_theme_stats(self, context: StageContext) -> Optional[Path]:

        rating_column = context.get_field("rating")

        rating_column = rating_column if rating_column in context.df.columns else None

        rating_count_column = context.get_field("rating_count")

        rating_count_column = (

            rating_count_column if rating_count_column in context.df.columns else None

        )

        call_column = context.call_number_column

        if not call_column or call_column not in context.df.columns:

            call_column = None

        return self.theme_analyzer.generate_report(

            df=context.df,

            rating_column=rating_column,

            call_number_column=call_column,

            rating_count_column=rating_count_column,

            source_excel=context.excel_path,

            prepared_dataset=context.extra.get("dynamic_filter_dataset"),

            dynamic_filter_result=context.extra.get("dynamic_filter_result"),

        )

    def _resolve_post_link_decision(

        self,

        context: StageContext,

        options: DoubanRatingPipelineOptions,

    ) -> str:

        if not options.prompt_post_link_action:

            context.extra["post_link_decision"] = "continue"

            return "continue"

        decision = context.extra.get("post_link_decision")

        if decision:

            return decision

        decision = self._prompt_post_link_action()

        context.extra["post_link_decision"] = decision

        return decision

    def _prompt_post_link_action(self) -> str:

        try:

            interactive = sys.stdin.isatty()

        except Exception:

            interactive = False

        if not interactive:

            logger.info("未检测到交互终端，默认继续 Subject API 阶段")

            return "continue"

        print("\n=== 豆瓣链接阶段已完成 ===")

        print("请选择后续操作：")

        print("  1. 继续调用 Subject API 获取豆瓣详情（推荐）")

        print("  2. 暂停/中止本次运行，稍后再执行 API 阶段")

        while True:

            try:

                choice = input("请输入选项编号 (默认 1): ").strip() or "1"

            except KeyboardInterrupt:

                print()

                return "stop"

            if choice in {"1", "继续", "y", "Y"}:

                return "continue"

            if choice in {"2", "停止", "n", "N", "q", "Q"}:

                return "stop"

            print("无效的选项，请输入 1 或 2。")

    def _validate_excel(self, excel_file: str) -> Path:

        path = Path(excel_file).expanduser().resolve()

        if not path.exists():

                    raise FileNotFoundError(f"未找到Excel文件: {path}")

        return path

    def _ensure_required_columns(

        self,

        df: pd.DataFrame,

        field_mapping: Dict[str, str],

        barcode_column: str,

        isbn_column: str,

        link_column: str,

        extra_columns: Optional[List[Optional[str]]] = None,

    ) -> None:

        for column in field_mapping.values():

            if column and column not in df.columns:

                df[column] = ""

        required_columns = {barcode_column, isbn_column, link_column}

        if extra_columns:

            required_columns.update({col for col in extra_columns if col})

        for column in required_columns:

            if column and column not in df.columns:

                df[column] = ""

        for column in set(field_mapping.values()).union(required_columns):

            if column and column in df.columns:

                try:

                    df[column] = df[column].astype("object")

                except Exception:

                    pass

    def _ensure_candidate_column(self, df: pd.DataFrame, column: str) -> None:

        if not column:

            return

        if column not in df.columns:

            df[column] = ""

        try:

            df[column] = df[column].astype("object")

        except Exception:

            pass

    def _build_db_config(self, options: DoubanRatingPipelineOptions) -> Dict[str, Any]:

        douban_config = self.config_manager.get_douban_config()

        db_config = (douban_config.get("database") or {}).copy()

        if options.force_update:

            db_config.setdefault("refresh_strategy", {})["force_update"] = True

        if options.db_path:

            db_config["db_path"] = options.db_path

        return db_config

    def _resolve_steps(

        self,

        context: StageContext,

        options: DoubanRatingPipelineOptions,

        db_config: Dict[str, Any],

    ) -> List[PipelineStep]:

        if self.steps_builder:

            return self.steps_builder(context, options)

        steps: List[PipelineStep] = []

        resume_mode = bool(context.extra.get("resume_from_partial"))

        db_enabled = not options.disable_database and options.enable_db_stage

        if db_enabled:

            steps.append(DoubanDatabaseStage(enabled=True, db_config=db_config))

        if options.enable_link_stage:

            # partial 模式下 link 阶段只处理 needs_link + source_column 为空的数据

            if resume_mode:

                logger.info("partial 模式下 link 阶段仅处理 needs_link 且 source_column 为空的记录")

                def link_filter(df, idx):

                    source_value = df.at[idx, context.progress_manager.source_column]

                    if pd.isna(source_value):

                        source_text = ""

                    else:

                        source_text = str(source_value).strip()

                        if source_text.lower() == "nan":

                            source_text = ""

                    return context.progress_manager.needs_link(df, idx) and not source_text

                steps.append(DoubanLinkStep(row_filter=link_filter))

            else:

                steps.append(DoubanLinkStep())

        if options.enable_subject_stage:

            # partial 模式下 API 阶段只处理 needs_api 的数据

            if resume_mode:

                logger.info("partial 模式下 API 阶段仅处理 needs_api 的记录")

                steps.append(DoubanSubjectStep(row_filter=context.progress_manager.needs_api))

            else:

                steps.append(DoubanSubjectStep())

        return steps

    def _build_output_path(self, excel_path: Path) -> Path:

        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

        output_name = f"{excel_path.stem}_豆瓣结果_{timestamp}{excel_path.suffix}"

        return excel_path.parent / output_name

    def _build_pipeline_stats(

        self,

        stage_stats: Dict[str, Dict[str, Any]],

        excel_path: Path,

        output_path: Path,

    ) -> Dict[str, Any]:

        db_stage = stage_stats.get("database_refresh", {})

        subject_stage = stage_stats.get("subject_api", {})

        link_stage = stage_stats.get("link_resolver", {})

        success_from_db = db_stage.get("existing_valid", 0)

        success_from_api = subject_stage.get("success", 0)

        stats: Dict[str, Any] = {

            "pipeline": "douban_rating",

            "input_file": str(excel_path),

            "output_file": str(output_path),

            "stages": stage_stats,

            "success_douban_count": success_from_db + success_from_api,

            "failed_douban_count": subject_stage.get("failed", 0),

            "link_success_count": link_stage.get("success", 0),

        }

        return stats

    def _try_generate_report(

        self,

        df: pd.DataFrame,

        options: DoubanRatingPipelineOptions,

        stats: Dict[str, Any],

        field_mapping: Dict[str, str],

        final_excel_path: str,

        categories: Optional[Dict[str, Any]] = None,

    ) -> None:

        try:

            report_path = self.report_generator.generate_report(

                df=df,

                status_column=options.status_column,

                field_mapping=field_mapping,

                final_excel_path=final_excel_path,

                categories=categories,

            )

            stats["report_file"] = str(report_path)

        except Exception as exc:  # noqa: BLE001

            logger.warning("豆瓣报告生成失败: %s", exc)
