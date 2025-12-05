"""单元测试：验证StorageManager Analyze阶段字段级更新修复"""

import os
import tempfile
import pandas as pd
import shutil
from src.core.storage import StorageManager


class TestStorageAnalyzeFieldUpdateFix:
    """测试StorageManager Analyze阶段字段级更新修复"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.storage = StorageManager(self.test_dir)
        
    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_analyze_field_level_update_preserves_data(self):
        """测试Analyze阶段字段级更新保留现有数据"""
        # 模拟现有的数据（包含fetch和extract阶段的字段）
        existing_articles = [
            {
                "source": "TestSource",
                "title": "原始标题",
                "article_date": "2025-12-01",
                "link": "https://example.com/article1",
                "published_date": "2025-12-01T10:00:00",
                "fetch_date": "2025-12-01T10:05:00",
                "summary": "原始摘要",
                "content": "原始内容",
                "full_text": "原始全文",
                "extract_status": "success",
                "extract_error": "",
                "filter_pass": True,
                "filter_reason": "",
                "filter_status": "pending"
            }
        ]
        
        # 模拟新的分析结果（只包含analyze阶段字段）
        new_articles = [
            {
                "title": "更新后的标题",
                "link": "https://example.com/article1",
                "published_date": "2025-12-01T10:00:00",
                "llm_status": "completed",
                "llm_score": 85,
                "llm_reason": "高质量文章",
                "llm_summary": "更新后的摘要",
                "filter_pass": False,
                "filter_reason": "内容不符主题",
                "filter_status": "rejected"
            }
        ]
        
        # 创建临时文件并写入现有数据
        test_file = os.path.join(self.test_dir, "2025-12.xlsx")
        df = pd.DataFrame(existing_articles)
        df.to_excel(test_file, index=False)
        
        # 执行save_analyze_results
        result = self.storage.save_analyze_results(new_articles, input_file=test_file)
        
        # 验证结果
        assert result is not None
        
        # 读取结果并验证
        updated_articles = self.storage.load_stage_data("analyze", result)
        assert len(updated_articles) == 1
        
        updated_article = updated_articles[0]
        
        # 验证fetch阶段的字段被保留
        assert updated_article["source"] == "TestSource"
        assert updated_article["article_date"] == "2025-12-01"
        assert updated_article["fetch_date"] == "2025-12-01T10:05:00"
        assert updated_article["summary"] == "原始摘要"
        assert updated_article["content"] == "原始内容"
        
        # 验证extract阶段的字段被保留
        assert updated_article["full_text"] == "原始全文"
        assert updated_article["extract_status"] == "success"
        # 处理pandas读取Excel时的NaN值
        extract_error = updated_article["extract_error"]
        assert extract_error == "" or str(extract_error).lower() in ["nan", "none", ""]
        
        # 验证analyze阶段的字段被正确更新
        assert updated_article["title"] == "更新后的标题"
        assert updated_article["llm_status"] == "completed"
        assert updated_article["llm_score"] == 85
        assert updated_article["llm_reason"] == "高质量文章"
        assert updated_article["llm_summary"] == "更新后的摘要"
        assert updated_article["filter_pass"] == False
        assert updated_article["filter_reason"] == "内容不符主题"
        assert updated_article["filter_status"] == "rejected"
    
    def test_standard_columns_consistency(self):
        """测试标准字段顺序常量的一致性"""
        # 验证标准字段定义存在
        assert hasattr(self.storage, 'STANDARD_COLUMNS')
        assert hasattr(self.storage, 'ANALYZE_UPDATE_FIELDS')
        
        # 验证各阶段字段定义完整
        assert "fetch" in self.storage.STANDARD_COLUMNS
        assert "extract" in self.storage.STANDARD_COLUMNS
        assert "analyze" in self.storage.STANDARD_COLUMNS
        
        # 验证analyze更新字段列表
        expected_analyze_fields = [
            "filter_pass", "filter_reason", "filter_status",
            "llm_status", "llm_score", "llm_reason", "llm_summary", 
            "llm_thematic_essence", "llm_tags", 
            "llm_primary_dimension", "llm_mentioned_books"
        ]
        
        for field in expected_analyze_fields:
            assert field in self.storage.ANALYZE_UPDATE_FIELDS