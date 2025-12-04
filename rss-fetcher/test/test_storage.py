"""StorageManager 分析结果保存相关测试"""

import os
import unittest
from datetime import datetime
from tempfile import TemporaryDirectory

import pandas as pd

from src.core.storage import StorageManager


class StorageManagerAnalyzeTests(unittest.TestCase):
    """验证阶段三保存逻辑的关键行为"""

    def setUp(self):
        """搭建临时Excel环境"""
        self.temp_dir = TemporaryDirectory()
        self.storage = StorageManager(self.temp_dir.name)
        month_name = datetime.now().strftime("%Y-%m")
        self.filepath = os.path.join(self.temp_dir.name, f"{month_name}.xlsx")
        pd.DataFrame(self._base_articles()).to_excel(self.filepath, index=False)

    def tearDown(self):
        """清理临时目录"""
        self.temp_dir.cleanup()

    def _base_articles(self):
        """提供默认Excel数据"""
        return [
            {
                "source": "源A",
                "title": "文章一",
                "article_date": "2025-12-03",
                "published_date": "2025-12-03",
                "link": "https://example.com/a",
                "fetch_date": "2025-12-03",
                "summary": "摘要一",
                "extract_status": "success",
                "extract_error": "",
                "content": "原始内容",
                "full_text": "原始全文",
                "llm_status": "",
                "llm_decision": "",
                "llm_score": 0,
                "llm_reason": "",
                "llm_summary": "",
                "llm_tags": "[]",
                "llm_keywords": "[]",
                "llm_primary_dimension": "",
                "llm_mentioned_books": "[]",
                "llm_book_clues": "[]",
                "llm_raw_response": "",
            },
            {
                "source": "源B",
                "title": "文章二",
                "article_date": "2025-12-02",
                "published_date": "2025-12-02",
                "link": "https://example.com/b",
                "fetch_date": "2025-12-02",
                "summary": "摘要二",
                "extract_status": "success",
                "extract_error": "",
                "content": "旧内容",
                "full_text": "旧全文",
                "llm_status": "成功",
                "llm_decision": True,
                "llm_score": 80,
                "llm_reason": "原始理由",
                "llm_summary": "原始总结",
                "llm_tags": "[]",
                "llm_keywords": "[]",
                "llm_primary_dimension": "",
                "llm_mentioned_books": "[]",
                "llm_book_clues": "[]",
                "llm_raw_response": "已有响应",
            },
        ]

    def test_save_analyze_results_updates_ready_articles(self):
        """具备LLM结果的文章应写回Excel"""
        updated_article = self._base_articles()[0].copy()
        updated_article.update(
            {
                "llm_status": "成功",
                "llm_decision": True,
                "llm_score": 90,
                "llm_reason": "命中要点",
                "llm_summary": "总结内容",
                "llm_tags": '["AI"]',
                "llm_keywords": '["关键字"]',
                "llm_primary_dimension": "趋势",
                "llm_mentioned_books": "[]",
                "llm_book_clues": "[]",
                "llm_raw_response": '{"score": 90}',
            }
        )

        result_path = self.storage.save_analyze_results([updated_article], self.filepath)

        self.assertEqual(result_path, self.filepath)
        df = pd.read_excel(self.filepath)
        row = df[df["link"] == "https://example.com/a"].iloc[0]
        self.assertEqual(row["llm_status"], "成功")
        self.assertEqual(row["llm_score"], 90)
        self.assertEqual(row["llm_reason"], "命中要点")

    def test_save_analyze_results_keeps_existing_when_missing_llm_data(self):
        """缺少LLM字段的记录不应覆盖已有结果"""
        stale_article = self._base_articles()[1].copy()
        stale_article["llm_status"] = ""
        stale_article["llm_raw_response"] = ""

        self.storage.save_analyze_results([stale_article], self.filepath)

        df = pd.read_excel(self.filepath)
        row = df[df["link"] == "https://example.com/b"].iloc[0]
        self.assertEqual(row["llm_status"], "成功")
        self.assertEqual(row["llm_raw_response"], "已有响应")


if __name__ == "__main__":
    unittest.main()
