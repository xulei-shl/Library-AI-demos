from problem_classifier import classify_problem
import general_services
import customer_complaint
import sentiment_analysis
import database_support
import items_support
import sys
import os
from dotenv import load_dotenv
import paper_suggest

load_dotenv()

llm_configs = {
    "glm": {
        "temperature": 0,
        "model_name": os.getenv("GLM_MODEL_NAME"),
        "api_key": os.getenv("GLM_API_KEY"),
    },
    "gpt3": {
        "temperature": 0,
        "model_name": os.getenv("GPT3_MODEL_NAME"),
        "api_base": os.getenv("GPT3_API_BASE"),
        "api_key": os.getenv("GPT3_API_KEY"),
    },
    "lingyi": {
        "temperature": 0,
        "model_name": os.getenv("LINGYI_MODEL_NAME"),
        "api_base": os.getenv("LINGYI_API_BASE"),
        "api_key": os.getenv("LINGYI_API_KEY"),
    },
    "grop": {
        "model_name": os.getenv("GROP_MODEL_NAME"),
        "api_key": os.getenv("GROP_API_KEY"),
        "temperature": 0,
    },
    "gpt4": {
        "temperature": 0,
        "model_name": os.getenv("GPT4_MODEL_NAME"),
        "api_base": os.getenv("GPT4_API_BASE"),
        "api_key": os.getenv("GPT4_API_KEY"),
    }
}

def process_query(category, user_input, default_llm_config=llm_configs["lingyi"]):
    category_llm_config_map = {
        '馆藏图书报刊查询': llm_configs["grop"],
        # 其他类别可以在这里添加对应的配置
    }

    llm_config = category_llm_config_map.get(category, default_llm_config)

    category_func_map = {
        '读者投诉': customer_complaint.complaint_reponse,
        '数据库咨询': database_support.query_database_api,
        '馆藏图书报刊查询': items_support.extract_bookinfo,
        '日常业务咨询': general_services.general_response,
        '学术文献查询': lambda user_input, llm_config: paper_suggest.get_paper_recommendations(user_input, llm_configs),
        '其他': general_services.general_response,

    }

    print(f"--------------------------------------------")
    print(f"调用{category}模块")
    func = category_func_map.get(category)

    if func is None:
        return general_services.general_response(user_input, llm_config)
    else:
        return func(user_input, llm_config)

if __name__ == "__main__":
    user_input = """SWOT分析报告和一些商业/市场的分析报告你知道去上图的哪个数据库能找到么？"""

    # 情感分析
    sentiment_analysis_result = sentiment_analysis.sentiment_analysis(user_input, llm_configs["glm"])
    print(f"--------------------------------------------")
    print(sentiment_analysis_result)

    # 退出程序
    #sys.exit()

    if '负面' in sentiment_analysis_result:
        print("调用读者投诉模块")
        print(f"--------------------------------------------")
        complain_response = customer_complaint.complaint_reponse(user_input, llm_configs["lingyi"])
        print(complain_response)
    else:
        try:
            classify_result = classify_problem(user_input, llm_configs)
            print(f"--------------------------------------------")
            print(f"读者咨询问题分类: {classify_result}")
            response = process_query(classify_result, user_input)
        except:
            print(f"--------------------------------------------")
            print("读者咨询问题分类失败,归类为其他类型")
            response = process_query("其他", user_input)

        print(f"--------------------------------------------")
        print(response)