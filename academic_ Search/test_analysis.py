import unittest
from main import process_academic_search
from query_analyzer import analyze_query
from utils.prompt import PromptType
import os

class TestAcademicSearch(unittest.TestCase):
    def test_second_analysis_step(self):
        # 从data目录读取第一步的结果
        test_data_path = os.path.join('data', 'step1_result.md')
        with open(test_data_path, 'r', encoding='utf-8') as f:
            analyzed_query = f.read()
        
        # 构造测试用的用户查询
        user_query = "以“记忆女神图集”为代表的瓦尔堡图像学研究方法论分析"
        
        # 执行第二步分析
        enhanced_query = f"原始问题: {user_query}\n初步分析: {analyzed_query}"
        expanded_analysis = analyze_query(
            user_query=enhanced_query,
            prompt_name="问题分析与扩展",
            prompt_type=PromptType.SYSTEM
        )
        
        print("\n=== 扩展分析结果 ===\n")
        print(expanded_analysis)
    

if __name__ == '__main__':
    unittest.main()