
from query_analyzer import analyze_query
from langfuse_llm import get_llm_response
from dotenv import load_dotenv
from utils.prompt import LLMConfig, ConfigSource, PromptType
from mix_thinker import MixedThinker
import os
import sys

# 加载 .env 文件
load_dotenv()

# 问题混合思考
def process_question_mixing(user_query: str):
    try:
  
        # 初始化 MixedThinker
        thinker = MixedThinker(
            prompt_source=ConfigSource.LANGFUSE,
            config_source=ConfigSource.LANGFUSE,
            reasoning_prompt_name="最大算力",
            response_prompt_name="最大算力",
            prompt_type=PromptType.USER
        )
        
        # 获取思考过程，使用qwq
        reasoning = thinker.get_reasoning(
            query=user_query,
            trace_name="混合思考",
            trace_tags=["问题分析"],
            trace_metadata={"project": "cnki"}
        )
        print("\n=== 思考结束，开始回答 ===\n")  
        # 获取最终回答
        final_response = thinker.get_final_response(
            query=user_query,
            reasoning=reasoning,
            reasoning_prompt_label="doubao",
            trace_name="混合思考",
            trace_tags=["问题分析"],
            trace_metadata={"project": "cnki"}
        )
        
        # 格式化结果并保存
        formatted_result = f"""## 原始问题
{user_query}

## 思考过程
{reasoning}

## 最终回答
{final_response}
"""
        # 保存初步分析结果
        initial_analysis_path = os.path.join('data', '1. initial_analysis.md')
        with open(initial_analysis_path, 'w', encoding='utf-8') as f:
            f.write(formatted_result)
        print("\n=== 第 1 步问题的混合思考过程结束 ===\n")             
        # 用于后续分析的查询文本
        return final_response

    except Exception as e:
        print(f"\n处理过程中出现错误: {str(e)}")
        return None

# 问题扩展与讨论
def process_question_discussion(user_query: str):
    try:
        analyzed_query = ""
        # 尝试读取第一步的结果，如果失败则使用原始查询
        try:
            initial_analysis_path = os.path.join('data', '1. initial_analysis.md')
            with open(initial_analysis_path, 'r', encoding='utf-8') as f:
                content = f.read()
                final_response_section = content.split("## 最终回答\n")[-1].strip()
                analyzed_query = final_response_section
        except:
            print("\n未找到上一步分析结果，将直接使用原始问题进行分析\n")
            analyzed_query = user_query
        
        # 结构化拼接并第二次分析
        enhanced_query = f"## 原始问题:\n {user_query}\n\n## 初步分析:\n {analyzed_query}"
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
        expanded_analysis_path = os.path.join('data', '2. expanded_questions.md')
        with open(expanded_analysis_path, 'w', encoding='utf-8') as f:
            f.write(expanded_analysis)

    except Exception as e:
        print(f"\n处理过程中出现错误: {str(e)}")
        return None

# 步骤 3: 最终问题
def process_final_question(user_query: str):
    try:
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



        
    except Exception as e:
        print(f"\n文献检索策略处理过程中出现错误: {str(e)}")
        return None

def main():
    user_id = "USR202504170026"
    print("\n=== 学术搜索系统启动 ===\n")
    
    # 初始阶段：获取用户背景信息
    from user_info.query_database import (
        get_user_basic_info,
        get_user_profile_keywords,
        get_user_profile_fields
    )
    
    # 获取用户基本信息
    user_info = get_user_basic_info(user_id)
    # 获取用户研究关键词（top 5）
    user_keywords = get_user_profile_keywords(user_id, top_n=5)
    # 获取用户研究领域（top 3）
    user_fields = get_user_profile_fields(user_id, top_n=3)
    
    # user_query = input("请输入您的查询问题：")
    user_query = "大语言模型多智能体驱动的图书馆定题检索服务新范式（Selective Dissemination of information）"
    
    # 格式化用户背景信息和查询
    enhanced_query = f"""## 用户背景信息
### 基本信息
{user_info}

### 研究关键词
{', '.join([f'{kw[0]}({kw[1]:.2f})' for kw in user_keywords])}

### 研究领域
{', '.join([f'{field[0]}({field[1]:.2f})' for field in user_fields])}

## 用户查询问题
{user_query}
"""
    print("\n=== 用户背景信息与检索问题 ===\n")     
    print(enhanced_query)
    # 是否进行头脑风暴
    brainstorm = input("\n是否进行头脑风暴？(y/n): ")
    if brainstorm.lower() == 'y':
        print("\n=== 头脑风暴阶段 ===\n")
        # 头脑风暴
        brainstorm_result = get_llm_response(
            user_prompt=enhanced_query,
            prompt_name="问题引导",
            trace_name="头脑风暴"
        )
        print("\n=== 头脑风暴完成 ===\n")
        brainstorm_content = brainstorm_result.choices[0].message.content
        # 保存头脑风暴结果
        brainstorm_path = os.path.join('data', 'brainstorm_result.md')
        with open(brainstorm_path, 'w', encoding='utf-8') as f:
            f.write(brainstorm_content)

        # 将头脑风暴结果作为历史消息
        history_messages = [
            {"role": "user", "content": enhanced_query},
            {"role": "assistant", "content": brainstorm_content}
        ]
        
        # 获取用户新的输入
        new_query = input("\n请基于头脑风暴的引导询问，输入您的回答：")
        
        # 调用大模型进行回答
        response = get_llm_response(
            user_prompt=new_query,
            prompt_name="问题引导",
            trace_name="问题深化",
            history=history_messages
        )
        
        # 更新用户查询为最新的回答
        user_query = response.choices[0].message.content
        user_query = brainstorm_content



        
    
    sys.exit()

    # # 调用mix_thinker第一次问答
    # print("\n=== 步骤 1: 问题的混合思考 ===\n")   
    # process_question_mixing(user_query)

    print("\n=== 步骤 2: 问题分析与扩展 ===\n")   
    process_question_discussion(user_query)

    # process_final_question(user_query)

    # process_retrieval_strategy(user_query)
    print("\n=== 处理完成 ===\n")

if __name__ == "__main__":
    main()