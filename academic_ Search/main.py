
from query_analyzer import analyze_query
from dotenv import load_dotenv
from utils.prompt import LLMConfig, ConfigSource, PromptType
import os
import sys

# 加载 .env 文件
load_dotenv()

def process_academic_search():
    try:
        # 步骤 1: 获取用户查询
        user_query = input("请输入您的查询问题：")
        print("\n=== 步骤 1: 问题讨论 ===\n")

        # 第一次分析
        analyzed_query = analyze_query(
            user_query=user_query,
            prompt_name="最大算力",
            prompt_type=PromptType.USER
        )
        print("\n=== 问题分析讨论完成 ===\n")
        
        # 保存初步分析结果
        initial_analysis_path = os.path.join('data', 'initial_analysis.md')
        with open(initial_analysis_path, 'w', encoding='utf-8') as f:
            f.write(analyzed_query)
        
        # 执行第二步分析测试
        # 从data目录读取第一步的结果
        with open(initial_analysis_path, 'r', encoding='utf-8') as f:
            analyzed_query = f.read()
        
        # 结构化拼接并第二次分析
        enhanced_query = f"## 原始问题:\n {user_query}\n\n## 初步分析:\n {analyzed_query}"
        print("\n=== 步骤 2: 问题分析与扩展 ===\n")
        expanded_analysis = analyze_query(
            user_query=enhanced_query,
            # model_name="gemini-2.0-flash-thinking-exp",
            # base_url=os.getenv('ONEAPI_API_BASE'),
            # api_key=os.getenv('ONEAPI_API_KEY'),
            # temperature=0.7,
            # config_source=ConfigSource.DIRECT,
            prompt_name="问题分析与扩展",
            prompt_type=PromptType.SYSTEM
        )
        print("\n=== 扩展分析完成 ===\n")

        # 保存扩展分析结果
        expanded_analysis_path = os.path.join('data', 'expanded_analysis.md')
        with open(expanded_analysis_path, 'w', encoding='utf-8') as f:
            f.write(expanded_analysis)

        # 步骤 3: 最终问题确认
        print("\n=== 步骤 3: 最终问题确认 ===\n")
        final_question = input("请输入您的最终问题：")
        # 读取初步分析结果
        with open(initial_analysis_path, 'r', encoding='utf-8') as f:
            initial_analysis = f.read()      
        # 读取扩展分析结果
        with open(expanded_analysis_path, 'r', encoding='utf-8') as f:
            expanded_analysis = f.read()
            
        # 结构化拼接所有信息
        final_query = f"""
            ## 原始问题：\n {user_query}\n\n
            ## 原始问题讨论：\n {initial_analysis}\n\n
            ## 原始问题扩展分析: \n {expanded_analysis}\n\n
            ## 最终问题：\n {final_question}"""
        print("\n=== 步骤 3: 选题报告 ===\n")
        topic_report = analyze_query(
            user_query=final_query,
            model_name="qwen-max-latest",
            base_url=os.getenv('ONEAPI_API_BASE'),
            api_key=os.getenv('ONEAPI_API_KEY'),
            temperature=0.7,
            config_source=ConfigSource.DIRECT,
            prompt_name="选题报告",
            prompt_type=PromptType.SYSTEM
        )
        print("\n=== 选题报告生成 ===\n")
        topic_report_path = os.path.join('data', 'topic_report_result.md')
        with open(topic_report_path, 'w', encoding='utf-8') as f:
            f.write(topic_report)

    except Exception as e:
        print(f"\n处理过程中出现错误: {str(e)}")
        return None

def process_retrieval_strategy():
    try:
        # 第二阶段第一步 检索词生成
        # 读取选题报告结果
        topic_report_path = os.path.join('data', 'topic_report_result.md')
        with open(topic_report_path, 'r', encoding='utf-8') as f:
            topic_report = f.read()
        
        print("\n=== 文献检索策略阶段 ===\n")
        retrieval_strategy = analyze_query(
            user_query=topic_report,
            prompt_name="文献检索策略",
            prompt_type=PromptType.SYSTEM
        )
        
        print("\n=== 文献检索策略完成 ===\n")
        # 保存检索策略结果
        strategy_path = os.path.join('data', 'retrieval_strategy.md')
        with open(strategy_path, 'w', encoding='utf-8') as f:
            f.write(retrieval_strategy)
            
        return retrieval_strategy

        # 第二阶段第二步 初检索
        user_query = ""
        # user_query = input("请输入您的检索关键词：")
        print("\n=== 步骤 2: 文献检索 ===\n")

        
    except Exception as e:
        print(f"\n文献检索策略处理过程中出现错误: {str(e)}")
        return None

def main():
    print("\n=== 学术搜索系统启动 ===\n")
    # process_academic_search()
    process_retrieval_strategy()
    print("\n=== 处理完成 ===\n")

if __name__ == "__main__":
    main()