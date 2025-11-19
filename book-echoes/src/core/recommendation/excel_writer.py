import os
import pandas as pd
from typing import Dict, Any, List
from src.utils.logger import get_logger

logger = get_logger(__name__)

INITIAL_COLUMNS = [
    "初评结果", "初评分数", "初评理由", "初评淘汰原因", "初评淘汰说明"
]

RUNOFF_COLUMNS = [
    "主题内决选结果", "主题内决选理由"
]

FINAL_COLUMNS = [
    "终评结果", "终评分数", "终评理由", "终评淘汰原因", "终评淘汰说明",
    "人工评选", "人工推荐语"
]

class ExcelRecommendationWriter:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.df = None

    def load(self):
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(self.excel_path)
        self.df = pd.read_excel(self.excel_path)
        for col in INITIAL_COLUMNS + RUNOFF_COLUMNS + FINAL_COLUMNS:
            if col not in self.df.columns:
                self.df[col] = ""
        return True

    def _find_row(self, barcode: str) -> int:
        if self.df is None:
            return -1
        col = None
        if "书目条码" in self.df.columns:
            col = "书目条码"
        elif "barcode" in self.df.columns:
            col = "barcode"
        else:
            return -1
        for i, row in self.df.iterrows():
            if str(row.get(col, "")).strip() == str(barcode).strip():
                return i
        return -1

    def _has_value(self, row_index: int, column: str) -> bool:
        v = self.df.at[row_index, column]
        if pd.isna(v):
            return False
        s = str(v).strip()
        if not s:
            return False
        return not s.startswith("ERROR:")

    def write_initial(self, result: Dict[str, Any]):
        selected = result.get("selected_books", [])
        unselected_groups = result.get("unselected_books", [])
        updated = 0
        for book in selected:
            idx = self._find_row(book.get("id", ""))
            if idx == -1:
                continue
            if self._has_value(idx, "初评结果"):
                continue
            self.df.at[idx, "初评结果"] = "通过"
            self.df.at[idx, "初评分数"] = book.get("rating", "")
            self.df.at[idx, "初评理由"] = book.get("reason", "")
            updated += 1
        for group in unselected_groups:
            reason_cat = group.get("category", "")
            explain = group.get("explanation", "")
            # 检查是否是错误类型
            is_error = reason_cat.startswith("ERROR:")
            for b in group.get("books", []):
                idx = self._find_row(b.get("id", ""))
                if idx == -1:
                    continue
                if self._has_value(idx, "初评结果"):
                    continue
                # 如果是ERROR，将错误信息写入初评结果列
                if is_error:
                    self.df.at[idx, "初评结果"] = reason_cat
                    self.df.at[idx, "初评淘汰说明"] = explain
                else:
                    self.df.at[idx, "初评结果"] = "未通过"
                    self.df.at[idx, "初评淘汰原因"] = reason_cat
                    self.df.at[idx, "初评淘汰说明"] = explain
                updated += 1
        return updated

    def write_runoff(self, result: Dict[str, Any]) -> int:
        """
        写入主题内决选结果

        重要：只写入 RUNOFF_COLUMNS，不触碰 INITIAL_COLUMNS 和 FINAL_COLUMNS

        返回：更新的行数
        """
        selected = result.get("selected_books", [])
        unselected_groups = result.get("unselected_books", [])
        updated = 0

        for book in selected:
            idx = self._find_row(book.get("id", ""))
            if idx == -1:
                continue
            if self._has_value(idx, "主题内决选结果"):
                continue
            self.df.at[idx, "主题内决选结果"] = "晋级"
            self.df.at[idx, "主题内决选理由"] = book.get("reason", "")
            updated += 1

        for group in unselected_groups:
            reason_cat = str(group.get("category", "")).strip()
            reason = group.get("explanation", "")
            is_error = reason_cat.startswith("ERROR:")
            for b in group.get("books", []):
                idx = self._find_row(b.get("id", ""))
                if idx == -1:
                    continue
                if self._has_value(idx, "主题内决选结果"):
                    continue
                if is_error:
                    # 失败信息直接写入结果列，方便后续检测重试
                    self.df.at[idx, "主题内决选结果"] = reason_cat or "ERROR: 调用失败"
                    self.df.at[idx, "主题内决选理由"] = reason or reason_cat
                else:
                    self.df.at[idx, "主题内决选结果"] = "未晋级"
                    self.df.at[idx, "主题内决选理由"] = reason
                updated += 1

        return updated

    def write_final(self, result: Dict[str, Any]):
        selected = result.get("selected_books", [])
        unselected_groups = result.get("unselected_books", [])
        updated = 0
        for book in selected:
            idx = self._find_row(book.get("id", ""))
            if idx == -1:
                continue
            if self._has_value(idx, "终评结果"):
                continue
            self.df.at[idx, "终评结果"] = "通过"
            self.df.at[idx, "终评分数"] = book.get("rating", "")
            self.df.at[idx, "终评理由"] = book.get("reason", "")
            updated += 1
        for group in unselected_groups:
            reason_cat = str(group.get("category", "")).strip()
            explain = group.get("explanation", "")
            is_error = reason_cat.startswith("ERROR:")
            for b in group.get("books", []):
                idx = self._find_row(b.get("id", ""))
                if idx == -1:
                    continue
                if self._has_value(idx, "终评结果"):
                    continue
                if is_error:
                    self.df.at[idx, "终评结果"] = reason_cat or "ERROR: 调用失败"
                    self.df.at[idx, "终评淘汰说明"] = explain or reason_cat
                else:
                    self.df.at[idx, "终评结果"] = "未通过"
                    self.df.at[idx, "终评淘汰原因"] = reason_cat
                    self.df.at[idx, "终评淘汰说明"] = explain
                updated += 1
        return updated

    def save(self, output_path: str = None) -> str:
        path = output_path or self.excel_path
        dirp = os.path.dirname(path)
        if dirp and not os.path.exists(dirp):
            os.makedirs(dirp, exist_ok=True)
        self.df.to_excel(path, index=False)
        return path
