from typing import Dict, List, Any
import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger
from .theme_grouper import group_by_theme, split_batches
from .executor import RecommendationExecutor
from .excel_writer import ExcelRecommendationWriter
from .config import get_theme_finalist_quota, get_final_top_n, get_initial_batch_size
import random

logger = get_logger(__name__)

def _to_book_dict(row: pd.Series) -> Dict[str, Any]:
    """将 DataFrame 行转换为书目字典,包含基本信息"""
    return {
        "书目条码": row.get("书目条码", ""),
        "书名": row.get("书名", ""),
        "豆瓣副标题": row.get("豆瓣副标题", ""),
        "豆瓣作者": row.get("豆瓣作者", ""),
        "豆瓣丛书": row.get("豆瓣丛书", ""),
        "豆瓣内容简介": row.get("豆瓣内容简介", ""),
        "豆瓣作者简介": row.get("豆瓣作者简介", ""),
        "豆瓣目录": row.get("豆瓣目录", ""),
        "索书号": row.get("索书号", ""),
    }

def _to_book_dict_with_reasons(row: pd.Series) -> Dict[str, Any]:
    """将 DataFrame 行转换为书目字典,包含基本信息和历史评选理由"""
    book_dict = _to_book_dict(row)
    # 添加历史评选理由
    if pd.notna(row.get("初评理由")):
        book_dict["初评理由"] = row.get("初评理由")
    if pd.notna(row.get("主题内决选理由")):
        book_dict["主题内决选理由"] = row.get("主题内决选理由")
    return book_dict

def _get_series_or_default(df: pd.DataFrame, column: str, default: Any = "") -> pd.Series:
    """返回指定列；若缺失则提供一个默认值序列以避免布尔筛选报错。"""
    if column in df.columns:
        return df[column]
    if len(df) == 0:
        return pd.Series([], index=df.index, dtype=object)
    return pd.Series([default] * len(df), index=df.index)

def _needs_initial_review(row: pd.Series) -> bool:
    """检查数据是否需要初评（跳过已有合法结果的数据）"""
    result = row.get("初评结果", "")
    if pd.isna(result):
        return True
    result_str = str(result).strip()
    if not result_str:
        return True
    # 已有合法结果（通过/未通过），不需要重新评审
    if result_str in ["通过", "未通过"]:
        logger.info("跳过已有初评结果的数据: 书目条码=%s, 结果=%s", row.get("书目条码", ""), result_str)
        return False
    # ERROR开头的需要重试
    return True

def _needs_runoff(row: pd.Series) -> bool:
    """检查数据是否需要主题内决选（跳过已有合法决选结果的数据）"""
    result = row.get("主题内决选结果", "")
    if pd.isna(result):
        return True
    result_str = str(result).strip()
    if not result_str:
        return True
    if result_str in ["自动晋级", "晋级", "未晋级"]:
        logger.info("跳过已有决选结果的数据: 书目条码=%s, 结果=%s", row.get("书目条码", ""), result_str)
        return False
    return True

def _needs_final(row: pd.Series) -> bool:
    """检查数据是否需要终评（跳过已有合法终评结果的数据）"""
    result = row.get("终评结果", "")
    if pd.isna(result):
        return True
    result_str = str(result).strip()
    if not result_str:
        return True
    if result_str in ["通过", "未通过"]:
        logger.info("跳过已有终评结果的数据: 书目条码=%s, 结果=%s", row.get("书目条码", ""), result_str)
        return False
    return True

def _has_failed_review(row: pd.Series) -> bool:
    """检查数据是否初评失败（非合法值都视为失败）"""
    result = row.get("初评结果", "")
    if pd.isna(result):
        return True
    result_str = str(result).strip()
    if not result_str:
        return True
    # 白名单模式：只有"通过"或"未通过"是合法值，其他都需要重新处理
    if result_str not in ["通过", "未通过"]:
        logger.info("发现非法初评结果值: 书目条码=%s, 结果=%s", row.get("书目条码", ""), result_str)
        return True
    return False

def _retry_failed_reviews(excel_path: str, executor, writer) -> int:
    """兜底重试：处理所有失败的初评数据"""
    df = pd.read_excel(excel_path)
    candidate_status = _get_series_or_default(df, "候选状态", "")
    df = df[candidate_status == "候选"].copy()

    # 筛选出需要重试的数据
    failed_df = df[df.apply(_has_failed_review, axis=1)].copy()
    if len(failed_df) == 0:
        logger.info("没有需要兜底重试的数据")
        return 0

    logger.info("")
    logger.info("=" * 60)
    logger.info("开始兜底重试失败数据")
    logger.info("发现 %d 条失败数据", len(failed_df))

    # 重新加载writer以获取最新数据
    writer.load()

    # 按主题分组重试
    groups = group_by_theme(failed_df)

    # 从配置文件读取批次大小
    batch_size = get_initial_batch_size()

    # 统计重试批次
    retry_stats = {}
    total_retry_batches = 0
    for theme, gdf in groups.items():
        books = [_to_book_dict(row) for _, row in gdf.iterrows()]
        batches = split_batches(books, batch_size)
        retry_stats[theme] = {"count": len(books), "batches": len(batches)}
        total_retry_batches += len(batches)

    logger.info("重试主题数: %d 个", len(groups))
    logger.info("重试总批次: %d 批", total_retry_batches)
    logger.info("-" * 60)
    for theme, stats in sorted(retry_stats.items()):
        logger.info("重试主题 [%s]: %d 条 -> %d 批", theme, stats["count"], stats["batches"])
    logger.info("=" * 60)

    retry_count = 0
    processed_retry_batches = 0

    for theme_idx, (theme, gdf) in enumerate(groups.items(), 1):
        books = [_to_book_dict(row) for _, row in gdf.iterrows()]
        batches = split_batches(books, batch_size)

        logger.info("")
        logger.info("兜底重试主题 [%s] (%d/%d)", theme, theme_idx, len(groups))

        for batch_idx, batch in enumerate(batches, 1):
            logger.info("-> 兜底重试 [%s] 第 %d/%d 批，本批 %d 条 | 总进度: %d/%d 批",
                       theme, batch_idx, len(batches), len(batch),
                       processed_retry_batches + 1, total_retry_batches)

            result = executor.initial(theme, batch)
            if result is None:
                logger.error("兜底重试返回None，跳过写入")
                processed_retry_batches += 1
                continue

            updated = writer.write_initial(result)
            retry_count += updated
            processed_retry_batches += 1

            logger.info("-> 兜底重试 [%s] 第 %d/%d 批完成，成功更新 %d 条",
                       theme, batch_idx, len(batches), updated)

    writer.save()

    logger.info("")
    logger.info("=" * 60)
    logger.info("兜底重试完成: 共处理 %d 批，成功更新 %d 条数据", total_retry_batches, retry_count)
    logger.info("=" * 60)

    return retry_count

def run_theme_recommendation_initial(excel_path: str) -> Dict[str, List[Dict]]:
    df = pd.read_excel(excel_path)
    candidate_status = _get_series_or_default(df, "候选状态", "")
    df = df[candidate_status == "候选"].copy()

    # 过滤掉已有合法初评结果的数据
    original_count = len(df)
    df = df[df.apply(_needs_initial_review, axis=1)].copy()
    filtered_count = len(df)
    if filtered_count < original_count:
        logger.info("已过滤 %d 条已有初评结果的数据，剩余 %d 条待处理",
                   original_count - filtered_count, filtered_count)

    if filtered_count == 0:
        logger.info("没有需要初评的数据")
        return {"selected": []}

    groups = group_by_theme(df)

    # 从配置文件读取批次大小
    batch_size = get_initial_batch_size()

    # 统计主题分组信息
    theme_stats = {}
    total_batches = 0
    for theme, gdf in groups.items():
        books = [_to_book_dict(row) for _, row in gdf.iterrows()]
        batches = split_batches(books, batch_size)
        theme_stats[theme] = {
            "count": len(books),
            "batches": len(batches),
            "batch_sizes": [len(b) for b in batches]
        }
        total_batches += len(batches)

    # 输出总体进度信息
    logger.info("=" * 60)
    logger.info("主题初评任务开始")
    logger.info("候选数据总数: %d 条", original_count)
    logger.info("已完成数据: %d 条", original_count - filtered_count)
    logger.info("待处理数据: %d 条", filtered_count)
    logger.info("主题大类总数: %d 个", len(groups))
    logger.info("总批次数量: %d 批", total_batches)
    logger.info("-" * 60)
    for theme, stats in sorted(theme_stats.items()):
        logger.info("主题 [%s]: %d 条 -> %d 批 (批次大小: %s)",
                   theme, stats["count"], stats["batches"],
                   ", ".join(map(str, stats["batch_sizes"])))
    logger.info("=" * 60)

    executor = RecommendationExecutor()
    writer = ExcelRecommendationWriter(excel_path)
    writer.load()
    selected_all: List[Dict] = []

    # 处理进度跟踪
    processed_batches = 0
    processed_books = 0

    for theme_idx, (theme, gdf) in enumerate(groups.items(), 1):
        books = [_to_book_dict(row) for _, row in gdf.iterrows()]
        batches = split_batches(books, batch_size)

        logger.info("")
        logger.info("开始处理主题 [%s] (%d/%d)", theme, theme_idx, len(groups))
        logger.info("主题 [%s] 包含 %d 条数据，分为 %d 批", theme, len(books), len(batches))

        for batch_idx, batch in enumerate(batches, 1):
            logger.info("-> 主题 [%s] 第 %d/%d 批，本批 %d 条 | 总进度: %d/%d 批, %d/%d 条",
                       theme, batch_idx, len(batches), len(batch),
                       processed_batches + 1, total_batches,
                       processed_books + len(batch), filtered_count)

            result = executor.initial(theme, batch)
            if result is None:
                logger.error("批次处理返回None，跳过写入")
                processed_batches += 1
                processed_books += len(batch)
                continue

            writer.write_initial(result)
            for sb in result.get("selected_books", []):
                m = next((b for b in batch if str(b.get("书目条码")) == str(sb.get("id"))), None)
                if m:
                    selected_all.append({**m, "初评理由": sb.get("reason", "")})

            processed_batches += 1
            processed_books += len(batch)

            logger.info("-> 主题 [%s] 第 %d/%d 批完成，本批选中 %d 条",
                       theme, batch_idx, len(batches),
                       len(result.get("selected_books", [])))

        logger.info("主题 [%s] 处理完成 (%d/%d)", theme, theme_idx, len(groups))

    writer.save()

    logger.info("")
    logger.info("=" * 60)
    logger.info("所有主题初评完成: 共处理 %d 批，%d 条数据", total_batches, filtered_count)
    logger.info("=" * 60)

    # 兜底重试：检查是否有ERROR或空的初评结果
    retry_count = _retry_failed_reviews(excel_path, executor, writer)
    if retry_count > 0:
        logger.info("兜底重试完成，处理了 %d 条失败数据", retry_count)

    return {"selected": selected_all}

def _has_failed_runoff(row: pd.Series) -> bool:
    """检查数据是否决选失败"""
    result = row.get("主题内决选结果", "")
    if pd.isna(result) or not str(result).strip():
        return True
    # 白名单：合法值为 "自动晋级", "晋级", "未晋级"
    if str(result).strip() not in ["自动晋级", "晋级", "未晋级"]:
        logger.info("发现非法决选结果值: 书目条码=%s, 结果=%s", row.get("书目条码", ""), str(result))
        return True
    return False

def _retry_failed_runoffs(excel_path: str, executor, writer) -> int:
    """兜底重试:处理所有失败的主题内决选数据"""
    df = pd.read_excel(excel_path)
    # 只重试初评通过但决选失败的数据
    initial_results = _get_series_or_default(df, "初评结果", "")
    passed_df = df[initial_results == "通过"].copy()
    failed_df = passed_df[passed_df.apply(_has_failed_runoff, axis=1)].copy()

    if len(failed_df) == 0:
        logger.info("没有需要兜底重试的决选数据")
        return 0

    logger.info("")
    logger.info("=" * 60)
    logger.info("开始兜底重试决选失败数据")
    logger.info("发现 %d 条失败数据", len(failed_df))
    logger.info("=" * 60)

    # 重新加载writer
    writer.load()

    # 按主题分组重试
    groups = group_by_theme(failed_df)
    quota = get_theme_finalist_quota()
    retry_count = 0

    for theme, gdf in groups.items():
        theme_count = len(gdf)

        if theme_count <= quota:
            # 自动晋级
            logger.info("重试主题 [%s]: %d 本 ≤ 配额 %d,自动晋级", theme, theme_count, quota)
            for _, row in gdf.iterrows():
                idx = writer._find_row(row.get("书目条码", ""))
                if idx != -1:
                    writer.df.at[idx, "主题内决选结果"] = "自动晋级"
                    retry_count += 1
        else:
            # 重新调用LLM
            logger.info("重试主题 [%s]: %d 本 > 配额 %d,执行决选", theme, theme_count, quota)
            books = [_to_book_dict_with_reasons(row) for _, row in gdf.iterrows()]
            result = executor.runoff(theme, books, quota)
            if result:
                updated = writer.write_runoff(result)
                retry_count += updated
                logger.info("重试主题 [%s] 完成,更新 %d 条", theme, updated)

    writer.save()

    logger.info("")
    logger.info("=" * 60)
    logger.info("决选兜底重试完成: 成功更新 %d 条数据", retry_count)
    logger.info("=" * 60)

    return retry_count

def _ensure_runoff_completion(excel_path: str) -> None:
    """确保所有应参与决选的数据都获得了合法结果"""
    df = pd.read_excel(excel_path)
    initial_results = _get_series_or_default(df, "初评结果", "")
    passed_df = df[initial_results == "通过"].copy()
    pending_df = passed_df[passed_df.apply(_has_failed_runoff, axis=1)].copy()
    if len(pending_df) == 0:
        return
    sample = ", ".join(str(pending_df.iloc[i].get("书目条码", "")) for i in range(min(5, len(pending_df))))
    msg = f"主题内决选仍有 {len(pending_df)} 条书目未得到合法结果,示例条码: {sample}"
    logger.error(msg)
    raise RuntimeError("主题内决选未全部完成,请处理失败记录后重试")

def run_theme_runoff(excel_path: str) -> List[Dict]:
    """
    主题内决选:智能控制各主题晋级终评的数量上限

    流程:
    1. 读取初评通过的书目(初评结果='通过')
    2. 按索书号首字母重新分组
    3. 对每个主题组:
       - 若数量 > THEME_FINALIST_QUOTA(默认8):
         * 调用LLM进行主题内决选
         * 选出最优的quota本
         * 写回"主题内决选结果"和"主题内决选理由"
       - 若数量 <= THEME_FINALIST_QUOTA:
         * 全部自动晋级,跳过LLM调用(节省成本)
         * 在"主题内决选结果"列写入"自动晋级"
    4. 返回所有晋级终评的书目列表

    返回:晋级终评的书目列表
    """
    df = pd.read_excel(excel_path)

    # 筛选初评通过的书目
    initial_results = _get_series_or_default(df, "初评结果", "")
    passed_df = df[initial_results == "通过"].copy()
    if len(passed_df) == 0:
        logger.info("没有初评通过的数据,跳过决选阶段")
        return []

    # 过滤掉已有合法决选结果的数据,避免重复调用LLM
    pending_df = passed_df[passed_df.apply(_needs_runoff, axis=1)].copy()
    filtered_out = len(passed_df) - len(pending_df)
    if filtered_out > 0:
        logger.info("已跳过 %d 条已有决选结果的数据,剩余 %d 条待处理", filtered_out, len(pending_df))

    # 加载配额配置
    quota = get_theme_finalist_quota()

    executor = RecommendationExecutor()
    writer = ExcelRecommendationWriter(excel_path)

    all_finalists = []

    logger.info("=" * 60)
    logger.info("主题内决选开始")
    logger.info("初评通过总数: %d 本", len(passed_df))
    logger.info("待执行决选数: %d 本", len(pending_df))

    if len(pending_df) > 0:
        groups = group_by_theme(pending_df)
        logger.info("主题总数: %d 个", len(groups))
        logger.info("决选配额: %d 本/主题", quota)
        logger.info("-" * 60)

        writer.load()

        for theme, gdf in groups.items():
            theme_count = len(gdf)

            if theme_count <= quota:
                # 自动晋级,不调用LLM
                logger.info("主题 [%s]: %d 本 <= 配额 %d,自动晋级", theme, theme_count, quota)

                for _, row in gdf.iterrows():
                    book_dict = _to_book_dict(row)
                    all_finalists.append(book_dict)
                    # 写回标记
                    idx = writer._find_row(row.get("书目条码", ""))
                    if idx != -1:
                        writer.df.at[idx, "主题内决选结果"] = "自动晋级"
            else:
                # 需要决选,调用LLM
                logger.info("主题 [%s]: %d 本 > 配额 %d,执行决选", theme, theme_count, quota)

                books = [_to_book_dict_with_reasons(row) for _, row in gdf.iterrows()]
                result = executor.runoff(theme, books, quota)

                # 收集晋级书目
                for book in result.get("selected_books", []):
                    matched = next((b for b in books if str(b.get("书目条码")) == str(book.get("id"))), None)
                    if matched:
                        all_finalists.append(matched)

                # 写入结果
                writer.write_runoff(result)

                logger.info("主题 [%s] 决选完成: 晋级 %d 本", theme, len(result.get("selected_books", [])))

        writer.save()
    else:
        logger.info("-" * 60)
        logger.info("所有初评通过书目均已有合法决选结果,跳过本轮决选调用")

    logger.info("=" * 60)
    logger.info("主题内决选完成: 晋级了 %d 条数据", len(all_finalists))

    # 兜底重试
    retry_count = _retry_failed_runoffs(excel_path, executor, writer)
    if retry_count > 0:
        logger.info("终选兜底重试完成,处理了 %d 条失败数据", retry_count)

    # 重新读取Excel数据，生成终评候选信息
    df = pd.read_excel(excel_path)
    runoff_results = _get_series_or_default(df, "主题内决选结果", "")
    advanced_df = df[runoff_results.isin(["晋级", "自动晋级"])].copy()

    # 过滤掉已有合法终评结果的数据，避免重复调用终评LLM
    advanced_original = len(advanced_df)
    advanced_df = advanced_df[advanced_df.apply(_needs_final, axis=1)].copy()
    if len(advanced_df) < advanced_original:
        logger.info("已跳过 %d 条已有终评结果的数据，剩余 %d 条待处理", advanced_original - len(advanced_df), len(advanced_df))

    # 组装最终需要进入终评的书目列表
    all_finalists = []
    for _, row in advanced_df.iterrows():
        book_dict = _to_book_dict(row)
        # 添加初评理由
        if pd.notna(row.get("初评理由")):
            book_dict["初评理由"] = row.get("初评理由")
        # 添加主题内决选理由
        if pd.notna(row.get("主题内决选理由")):
            book_dict["主题内决选理由"] = row.get("主题内决选理由")
        all_finalists.append(book_dict)

    logger.info("候选统计: 共 %d 条书目进入终评", len(all_finalists))

    _ensure_runoff_completion(excel_path)

    return all_finalists

def _has_failed_final(row: pd.Series) -> bool:
    """检查数据是否终评失败"""
    result = row.get("终评结果", "")
    if pd.isna(result) or not str(result).strip():
        return True
    # 白名单：合法值为 "通过", "未通过"
    if str(result).strip() not in ["通过", "未通过"]:
        logger.info("发现非法终评结果值: 书目条码=%s, 结果=%s", row.get("书目条码", ""), str(result))
        return True
    return False

def _retry_failed_finals(excel_path: str, executor, writer, top_n: int = 10) -> int:
    """兜底重试：处理所有失败的终评数据"""
    df = pd.read_excel(excel_path)

    # 统计当前终评状态
    final_results = _get_series_or_default(df, "终评结果", "")
    runoff_results = _get_series_or_default(df, "主题内决选结果", "")

    # 统计已通过的数据
    passed_count = len(df[final_results == "通过"])

    # 只重试决选晋级但终评失败的数据
    advanced_df = df[runoff_results.isin(["晋级", "自动晋级"])].copy()
    failed_df = advanced_df[advanced_df.apply(_has_failed_final, axis=1)].copy()

    if len(failed_df) == 0:
        logger.info("没有需要兜底重试的终评数据")
        logger.info("当前终评通过数: %d 本 | 目标: %d 本", passed_count, top_n)
        return 0

    logger.info("")
    logger.info("=" * 60)
    logger.info("开始兜底重试终评失败数据")
    logger.info("当前终评通过: %d 本 | 目标: %d 本", passed_count, top_n)
    logger.info("发现 %d 条失败数据", len(failed_df))

    # 如果已达到目标数量，记录警告但仍然处理失败数据（给它们一个公平的机会）
    if passed_count >= top_n:
        logger.warning("已达到目标数量 %d 本，但仍有 %d 条失败数据", top_n, len(failed_df))
        logger.warning("这些失败数据将被标记为'未通过'而非ERROR，确保数据完整性")
        # 将失败数据标记为未通过
        writer.load()
        updated = 0
        for _, row in failed_df.iterrows():
            idx = writer._find_row(row.get("书目条码", ""))
            if idx != -1 and not writer._has_value(idx, "终评结果"):
                writer.df.at[idx, "终评结果"] = "未通过"
                writer.df.at[idx, "终评淘汰原因"] = "配额已满"
                writer.df.at[idx, "终评淘汰说明"] = "终评名额已达上限"
                updated += 1
        writer.save()
        logger.info("已将 %d 条失败数据标记为'未通过'", updated)
        logger.info("=" * 60)
        return updated

    # 计算剩余配额
    remaining_quota = top_n - passed_count
    logger.info("剩余配额: %d 本", remaining_quota)
    logger.info("=" * 60)

    # 重新调用终评，使用剩余配额
    failed_books = [_to_book_dict(row) for _, row in failed_df.iterrows()]
    result = executor.final(failed_books, remaining_quota)

    if result:
        writer.load()
        updated = writer.write_final(result)
        writer.save()

        # 重新统计通过数量
        df_after = pd.read_excel(excel_path)
        final_results_after = _get_series_or_default(df_after, "终评结果", "")
        passed_count_after = len(df_after[final_results_after == "通过"])

        logger.info("")
        logger.info("=" * 60)
        logger.info("终评兜底重试完成: 成功更新 %d 条数据", updated)
        logger.info("终评通过总数: %d 本 | 目标: %d 本", passed_count_after, top_n)
        logger.info("=" * 60)
        return updated

    return 0

def _ensure_final_completion(excel_path: str) -> None:
    """确保所有晋级终评的书目都获得了合法终评结果"""
    df = pd.read_excel(excel_path)
    runoff_results = _get_series_or_default(df, "主题内决选结果", "")
    advanced_df = df[runoff_results.isin(["晋级", "自动晋级"])].copy()
    pending_df = advanced_df[advanced_df.apply(_has_failed_final, axis=1)].copy()
    if len(pending_df) == 0:
        return
    sample = ", ".join(str(pending_df.iloc[i].get("书目条码", "")) for i in range(min(5, len(pending_df))))
    msg = f"终评阶段仍有 {len(pending_df)} 条书目未得到合法结果，示例条码: {sample}"
    logger.error(msg)
    raise RuntimeError("终评未全部完成，请处理失败记录后重试")



def run_adaptive_final(excel_path: str, finalists: List[Dict], top_n: int = 10, max_batch_size: int = 30):
    """
    自适应终评（漏斗模式）：
    1. 如果候选数 <= max_batch_size：直接终评
    2. 如果候选数 > max_batch_size：
       - 阶段1（海选）：分批进行半决赛，每批选出 (max_batch_size / 批数) 本，
         确保总晋级数 ≈ max_batch_size。
       - 阶段2（决胜）：将海选晋级者（此时 <= max_batch_size）合并，进行一次性终评。
    """
    total_candidates = len(finalists)
    executor = RecommendationExecutor()
    writer = ExcelRecommendationWriter(excel_path)
    writer.load()

    logger.info("=" * 60)
    
    # --- 风险缓解 1: 配置验证 ---
    if max_batch_size < top_n:
        logger.warning("配置风险: max_batch_size (%d) < top_n (%d)", max_batch_size, top_n)
        logger.warning("这可能导致海选后幸存者不足，最终结果少于目标数量")
        logger.warning("建议: 将 max_batch_size 设置为至少 top_n 的 1.5 倍 (推荐: %d)", int(top_n * 1.5))
    
    # --- 风险缓解 2: 动态调整批次大小 ---
    # 当候选数过多时，自动提高 max_batch_size，避免海选过于激烈
    original_batch_size = max_batch_size
    if total_candidates > 100:
        # 候选数 > 100 时，临时提高批次上限到 50
        max_batch_size = max(max_batch_size, 50)
        if max_batch_size != original_batch_size:
            logger.info("候选数 (%d) 较多，自动提高批次上限: %d → %d", 
                       total_candidates, original_batch_size, max_batch_size)
    elif total_candidates > 200:
        # 候选数 > 200 时，进一步提高到 80
        max_batch_size = max(max_batch_size, 80)
        if max_batch_size != original_batch_size:
            logger.info("候选数 (%d) 非常多，自动提高批次上限: %d → %d", 
                       total_candidates, original_batch_size, max_batch_size)
    
    logger.info("自适应终评开始 | 候选数: %d | 批次上限: %d | 目标Top: %d", 
                total_candidates, max_batch_size, top_n)

    # --- 场景 1: 直接终评 ---
    if total_candidates <= max_batch_size:
        logger.info("候选数 (%d) <= 批次上限 (%d)，直接进入终评", total_candidates, max_batch_size)
        result = executor.final(finalists, top_n)
        writer.write_final(result)
        writer.save()
        
        selected_count = len(result.get("selected_books", []))
        logger.info("终评完成 | 最终入选: %d 本", selected_count)
        
        # 兜底重试
        retry_count = _retry_failed_finals(excel_path, executor, writer, top_n)
        if retry_count > 0:
            logger.info("终评兜底重试完成，处理了 %d 条失败数据", retry_count)
        _ensure_final_completion(excel_path)
        return

    # --- 场景 2: 海选 + 终评 ---
    logger.info("候选数 (%d) > 批次上限 (%d)，触发海选流程", total_candidates, max_batch_size)
    
    # 1. 计算分批
    # 向上取整计算批数
    num_batches = (total_candidates + max_batch_size - 1) // max_batch_size
    # 确保至少分2批
    num_batches = max(num_batches, 2)
    
    # 计算每批晋级名额 (目标总晋级数 = max_batch_size)
    # 这样能保证海选后的幸存者能一次性塞入 Final 阶段
    quota_per_batch = max_batch_size // num_batches
    # 至少选1本
    quota_per_batch = max(quota_per_batch, 1)
    
    logger.info("海选策略: 分 %d 批 | 每批晋级 %d 本 | 预计总晋级 %d 本", 
                num_batches, quota_per_batch, num_batches * quota_per_batch)

    # 随机打乱以保证公平
    shuffled_books = finalists.copy()
    random.shuffle(shuffled_books)
    batches = split_batches(shuffled_books, max_batch_size) # 这里split_batches会尽量均匀分

    semifinal_survivors = []
    semifinal_eliminated_count = 0

    # 2. 执行海选 (Semifinal)
    for i, batch in enumerate(batches, 1):
        logger.info("海选批次 %d/%d | 本批 %d 本 -> 晋级 %d 本", 
                    i, len(batches), len(batch), quota_per_batch)
        
        result = executor.semifinal(batch, quota_per_batch)
        
        # 处理晋级者
        for book in result.get("selected_books", []):
            matched = next((b for b in batch if str(b["书目条码"]) == str(book["id"])), None)
            if matched:
                # 保留半决赛的评语和分数，供终评参考
                survivor = {
                    **matched, 
                    "半决赛分数": book.get("rating"), 
                    "半决赛理由": book.get("reason")
                }
                semifinal_survivors.append(survivor)

        # 处理淘汰者 (写入Excel)
        for group in result.get("unselected_books", []):
            reason_cat = str(group.get("category", "")).strip()
            explanation = group.get("explanation", "")
            is_error = reason_cat.startswith("ERROR:")

            for b in group.get("books", []):
                idx = writer._find_row(b.get("id", ""))
                if idx == -1: continue
                
                if writer._has_value(idx, "终评结果"): continue

                if is_error:
                    writer.df.at[idx, "终评结果"] = reason_cat or "ERROR: 海选调用失败"
                else:
                    writer.df.at[idx, "终评结果"] = "未通过"
                    writer.df.at[idx, "终评淘汰原因"] = "海选淘汰"
                    writer.df.at[idx, "终评淘汰说明"] = explanation
                
                semifinal_eliminated_count += 1
        
        # 批次间保存，防止中断
        writer.save()

    logger.info("海选结束 | 晋级: %d 本 | 淘汰: %d 本", len(semifinal_survivors), semifinal_eliminated_count)

    # 3. 执行决胜 (Final)
    if not semifinal_survivors:
        logger.warning("海选后无幸存者，终评提前结束")
        return

    logger.info("-" * 60)
    logger.info("进入决赛圈 | 幸存者: %d 本 | 目标Top: %d", len(semifinal_survivors), top_n)
    
    # 此时 survivors 数量应该 <= max_batch_size (或略多一点点，如果除不尽)，直接一次性调用
    final_result = executor.final(semifinal_survivors, top_n)
    
    writer.load() # 重新加载以防万一
    writer.write_final(final_result)
    writer.save()

    logger.info("自适应终评完成 | 最终入选: %d 本", len(final_result.get("selected_books", [])))
    logger.info("=" * 60)

    # 兜底重试
    retry_count = _retry_failed_finals(excel_path, executor, writer, top_n)
    if retry_count > 0:
        logger.info("终评兜底重试完成，处理了 %d 条失败数据", retry_count)
    _ensure_final_completion(excel_path)

def run_theme_recommendation_final(excel_path: str, finalists: List[Dict], top_n: int = 10) -> None:
    """
    全局终评入口
    """
    # 从配置读取批次大小，默认为30
    from .config import get_final_batch_size
    max_batch_size = get_final_batch_size()
    
    run_adaptive_final(excel_path, finalists, top_n, max_batch_size)

def run_theme_recommendation_final_old(excel_path: str, selected_with_reason: List[Dict]) -> None:
    executor = RecommendationExecutor()
    writer = ExcelRecommendationWriter(excel_path)
    writer.load()
    result = executor.final(selected_with_reason, top_n=10)
    writer.write_final(result)
    writer.save()

def run_theme_recommendation(excel_path: str) -> None:
    run_theme_recommendation_initial(excel_path)
    # 生成运行报告
    try:
        from .report_generator import RecommendationReportGenerator
        report_gen = RecommendationReportGenerator()
        report_gen.generate_report(excel_path)
    except Exception as e:
        logger.error("生成分析报告失败: %s", e)

def run_theme_recommendation_full(excel_path: str) -> None:
    """
    完整三阶段评选流程

    流程：
    1. 阶段1：主题内初评（海选）
    2. 阶段2：主题内决选（晋级赛）
    3. 阶段3：全局终评（决赛圈）
    """
    # 阶段1: 初评
    run_theme_recommendation_initial(excel_path)

    # 阶段2: 主题内决选
    finalists = run_theme_runoff(excel_path)

    # 阶段3: 全局终评（智能模式选择）
    if len(finalists) > 0:
        # 从配置文件读取终评目标数量
        top_n = get_final_top_n()
        run_theme_recommendation_final(excel_path, finalists, top_n)
    else:
        logger.warning("没有书目晋级终评，跳过终评阶段")

    # 生成运行报告
    try:
        from .report_generator import RecommendationReportGenerator
        report_gen = RecommendationReportGenerator()
        report_gen.generate_report(excel_path)
    except Exception as e:
        logger.error("生成分析报告失败: %s", e)
