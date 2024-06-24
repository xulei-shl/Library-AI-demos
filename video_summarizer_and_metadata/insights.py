import os
from langchain_openai import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
import re
from langchain.docstore.document import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
import warnings

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

def get_final_insights(summary, llm_config):
    llm = ChatOpenAI(
        model=llm_config["glmweb"].get("model_name", "default-model"),
        temperature=llm_config["glmweb"].get("temperature", 0),
        api_key=llm_config["glmweb"].get("api_key"),
        base_url=llm_config["glmweb"].get("api_base")
    )

    system_template = """
    - Role: 您是一位专业的文本摘要助手，专注于从长文本中提炼关键信息。

    - Background: 用户需要从一篇讲座转录的长文本中获取其核心要点，包括标签、一句话总结、详细摘要和核心观点。

    - Profile: 您具备深厚的语言理解能力，能够从音频转录的长文本中剔除无关内容，快速识别和总结文本的核心内容。

    - Skills: 您拥有文本分析、信息提取和总结的能力。

    - Goals: 您需要帮助用户从长文本中提取以下信息：
    1. 标签：识别文本的关键领域、学科或专有名词。
    2. 一句话总结：用一句话概括文章的主旨。
    3. 摘要：提供文本的详细摘要，包括大纲和要点。
    4. 讨论话题与要点：列出他们讨论的主要话题，以及每个话题下的要点。

    - Constrains: 确保摘要准确反映原文内容，避免加入个人解释或总结。

    - OutputFormat: 
    1. 结果应包括标签列表、一句话总结、详细摘要和讨论话题与要点。
    2. 使用 markdown 格式。

    - Workflow:
    1. 阅读用户提供的长文本。
    2. 识别并标注文本的关键领域、学科或专有名词。提供3-5个即可。
    3. 撰写一句话总结，概括文章的主旨。
    4. 根据文本内容，撰写详细摘要，包括大纲和要点。
    5. 尽可能列出他们讨论的主要话题，不要遗漏
    6. 基于每个话题用bullet points列出要点

    """

    human_message = f"## 转录文本的分段总结：\n{summary}"

    messages = [
        SystemMessage(content=system_template),
        HumanMessage(content=human_message),
    ]

    json_result = llm.invoke(messages)
    parser = StrOutputParser()
    llm_result = parser.invoke(json_result)

    return llm_result

def get_insights_in_folder(folder_path, llm_configs):
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
            final_insight = get_final_insights(summary, llm_configs)

            output_file_path = os.path.join(root, "最终洞察报告.md")
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(final_insight)

            print(f"Final insight saved to: {output_file_path}")