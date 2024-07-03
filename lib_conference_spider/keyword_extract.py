from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from prompts import TEMPLATES

def keyword_extract(merged_text, llm_config, template_key):
    llm = ChatZhipuAI(
        model=llm_config["model_name"],
        temperature=llm_config["temperature"],
        api_key=llm_config["api_key"]
    )
    
    system_template = TEMPLATES.get(template_key, TEMPLATES["keywords"])

    messages = [
        SystemMessage(content=system_template),
        HumanMessage(content=merged_text),
    ]

    json_result = llm.invoke(messages)
    parser = StrOutputParser()
    result = parser.invoke(json_result)
    
    return result