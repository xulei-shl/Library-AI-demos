import os
from langchain_openai import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
import re
from langchain.docstore.document import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
import warnings
from prompts import TEMPLATES


warnings.filterwarnings('ignore')

def preprocess_text(text):
    text = re.sub(r'\[\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\]\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def custom_text_splitter(text, max_chunk_size=1000, overlap=100):
    sentences = re.split(r'(?<=[。！？])\s*', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chunk_size:
            current_chunk += sentence
        else:
            chunks.append(current_chunk)
            current_chunk = sentence[-overlap:] + sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def get_summarize(texts, llm_config):
    llm = ChatOpenAI(
        model=llm_config["glmweb"].get("model_name", "default-model"),
        temperature=llm_config["glmweb"].get("temperature", 0),
        api_key=llm_config["glmweb"].get("api_key"),
        base_url=llm_config["glmweb"].get("api_base")
    )

    prompt_template = """写出以下内容的简洁总结：
    {text}
    简洁总结："""
    prompt = PromptTemplate.from_template(prompt_template)

    refine_template = (
        "您的任务是提供具有关键见解的最终摘要\n"
        "我们已经提供了到目前为止的现有总结: {existing_answer}\n"
        "我们有机会用下面的更多内容来精炼原有总结"
        "(仅在需要时)\n"
        "------------\n"
        "{text}\n"
        "------------\n"
        "根据新的上下文，精炼原有总结，如果上下文不有用，返回原有总结"
        "如果上下文没有用处，返回原来的总结。"
    )
    refine_prompt = PromptTemplate.from_template(refine_template)

    refine_chain = load_summarize_chain(
        llm,
        chain_type="refine",
        question_prompt=prompt,
        refine_prompt=refine_prompt,
        return_intermediate_steps=True,
    )

    refine_outputs = refine_chain({'input_documents': texts})
    return refine_outputs['output_text']

def get_final_insights(summary, llm_config, template_key):
    llm = ChatOpenAI(
        model=llm_config["glmweb"].get("model_name", "default-model"),
        temperature=llm_config["glmweb"].get("temperature", 0),
        api_key=llm_config["glmweb"].get("api_key"),
        base_url=llm_config["glmweb"].get("api_base")
    )

    system_template = TEMPLATES.get(template_key, TEMPLATES["summarization1"])

    human_message = f"## 转录文本的分段总结：\n{summary}"

    messages = [
        SystemMessage(content=system_template),
        HumanMessage(content=human_message),
    ]

    json_result = llm.invoke(messages)
    parser = StrOutputParser()
    llm_result = parser.invoke(json_result)

    return llm_result

def get_insights_in_folder(folder_path, llm_configs, template_key):
    for root, dirs, files in os.walk(folder_path):
        optimized_transcript = None
        for file in files:
            if file.endswith("优化后的转录文本.md"):
                optimized_transcript = os.path.join(root, file)
                break
        
        if optimized_transcript:
            with open(optimized_transcript, 'r', encoding='utf-8') as f:
                content = f.read()

            preprocessed_text = preprocess_text(content)
            text_chunks = custom_text_splitter(preprocessed_text)
            texts = [Document(page_content=chunk) for chunk in text_chunks]

            summary = get_summarize(texts, llm_configs)
            final_insight = get_final_insights(summary, llm_configs, template_key)

            output_file_path = os.path.join(root, "最终洞察报告.md")
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(final_insight)

            print(f"Final insight saved to: {output_file_path}")