import os
import re
import time
import random
from langchain_community.chat_models import ChatZhipuAI
from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

def clean_optimized_text(file_path):
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # 删除 '优化后的文本' 及其前后的符号或字符
    cleaned_lines = []
    for line in lines:
        cleaned_line = re.sub(r'[^a-zA-Z0-9\s]*优化后的文本[^a-zA-Z0-9\s]*', '', line).strip()
        if cleaned_line:  # 只保留非空行
            cleaned_lines.append(cleaned_line)
    
    # 合并非时间戳的行到前一行
    final_lines = []
    current_line = ""
    
    timestamp_pattern = re.compile(r'^\[\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\]')
    
    for line in cleaned_lines:
        if timestamp_pattern.match(line):
            if current_line:
                final_lines.append(current_line)
            current_line = line  # 初始化为当前行
        else:
            current_line += " " + line.strip()
    
    # 添加最后一行
    if current_line:
        final_lines.append(current_line)
    
    # 严格匹配删除 '[]'
    cleaned_content = '\n'.join(final_lines)
    cleaned_content = re.sub(r'\[\]', '', cleaned_content)
    
    # 将处理后的内容写回文件
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(cleaned_content)
    print(f"\n-------------------已完成清洗并更新文件----------------------\n")
    print(file_path)

def split_transcript(transcript_text):
    # 使用正则表达式分割文本为句子
    lines = transcript_text.split('\n')
    segments = []
    current_segment = ""
    start_timestamp = ""
    end_timestamp = ""

    # 定义句子结束的标记
    sentence_end_patterns = r'[。！？…]+'
    clause_end_patterns = r'[，；：、]'

    for line in lines:
        if not line.strip():
            continue
        
        # 提取时间戳
        match = re.match(r'\[([\d:,]+) --> ([\d:,]+)\]', line)
        if match:
            if not start_timestamp:
                start_timestamp = match.group(1)
            end_timestamp = match.group(2)
            text = line[line.index(']') + 1:].strip()
            
            # 检查是否是句子或从句的结束
            if re.search(sentence_end_patterns, text):
                current_segment += text + " "
                segments.append((start_timestamp, end_timestamp, current_segment.strip()))
                current_segment = ""
                start_timestamp = ""
            elif re.search(clause_end_patterns, text) and len(current_segment) > 200:
                current_segment += text + " "
                segments.append((start_timestamp, end_timestamp, current_segment.strip()))
                current_segment = ""
                start_timestamp = ""
            else:
                current_segment += text + " "

    if current_segment:
        segments.append((start_timestamp, end_timestamp, current_segment.strip()))

    return segments

def optimize_segment(introductions, segment, llm_config):
    # llm = ChatZhipuAI(
    #     model=llm_config["glm"].get("model_name", "default-model"),
    #     temperature=llm_config["glm"].get("temperature", 0),
    #     api_key=llm_config["glm"].get("api_key"),
    # )
    llm = ChatOpenAI(
        model=llm_config["glmweb"].get("model_name", "default-model"),
        temperature=llm_config["glmweb"].get("temperature", 0),
        api_key=llm_config["glmweb"].get("api_key"),
        base_url=llm_config["glmweb"].get("api_base")
    )


    system_template = """
    # 角色
    你是一个出色的语音转录优化专家。你的长处在于能够精确地辨识和修正语音转录文本中的错误，并优化其口语化的表达方式。

    ## 技能
    ### 技能 1：识别错误
    - 分析转录文本（{{transcript_text}}），并找出可能识别错误的词语。
    - 根据上下文和提供的背景信息（{{introductions}}）推测可能正确的词。

    ### 技能 2：优化转录文本
    - 在修正了错误识别词语之后，对已转录的文本进行整体优化。
    - 合并文稿中的重复片段，删除多余的辅助词、语气词，清除不必要的部分，保持语义简洁清晰，逻辑顺畅。

    ### 技能 2：文本合并
    - 请将优化后的多个换行分段的短句合并为一个完整的句子，同时对其时间戳进行合并。

    ## 输出要求
    - 确保忠实于原始转录文本内容，以及文本的完整性，避免信息丢失。
    - 【重要】保留原始的时间戳和文本的对应关系。
    - 【重要】严格按照原始文本进行优化，不要有任何的说明或解释。
    - 【重要！！！】直接输出优化后的文本，不要有任何多余的内容。
    """

    start_time, end_time, text = segment
    human_message = f"\n\n## 背景介绍：{introductions}\n\n## 原始的转录文本：\n[{start_time} --> {end_time}] {text}"

    messages = [
        SystemMessage(content=system_template),
        HumanMessage(content=human_message),
    ]

    json_result = llm.invoke(messages)
    parser = StrOutputParser()
    llm_result = parser.invoke(json_result)

    return llm_result

def optimize_transcripts_in_folder(folder_path, llm_configs):
    for root, dirs, files in os.walk(folder_path):
        for sub_dir in dirs:
            sub_dir_path = os.path.join(root, sub_dir)
            transcript_file = next((f for f in os.listdir(sub_dir_path) if f.endswith("时间戳文本.md")), None)
            introduction_file = next((f for f in os.listdir(sub_dir_path) if f == "介绍.md"), None)
            if transcript_file and introduction_file:
                transcript_path = os.path.join(sub_dir_path, transcript_file)
                introduction_path = os.path.join(sub_dir_path, introduction_file)
                with open(transcript_path, "r", encoding="utf-8") as f:
                    transcript_text = f.read()
                with open(introduction_path, "r", encoding="utf-8") as f:
                    introductions = f.read()
                
                segments = split_transcript(transcript_text)
                
                optimized_filename = transcript_file.replace("时间戳文本.md", "优化后的转录文本.md")
                optimized_path = os.path.join(sub_dir_path, optimized_filename)
                
                for idx, segment in enumerate(segments, 1):  # 使用 enumerate 计数
                    optimized_segment = optimize_segment(introductions, segment, llm_configs)
                    with open(optimized_path, "a", encoding="utf-8") as f:
                        f.write(optimized_segment + "\n\n")
                    print(f"\n-------------------已优化并保存片段 {idx} ----------------------\n")
                    
                    # 随机暂停1-2秒
                    time.sleep(random.uniform(1, 2))
                print(f"\n-------------------已完成优化并保存转录文本----------------------\n")
                print(optimized_path)
                # 清理优化后的文本
                clean_optimized_text(optimized_path)