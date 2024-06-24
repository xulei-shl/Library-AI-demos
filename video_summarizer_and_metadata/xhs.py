import os
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

def social_media_writer(folder_path, llm_configs):
    def process_subfolder(subfolder_path):
        introduction_path = os.path.join(subfolder_path, '介绍.md')
        insight_report_path = os.path.join(subfolder_path, '最终洞察报告.md')

        if os.path.exists(introduction_path) and os.path.exists(insight_report_path):
            with open(introduction_path, 'r', encoding='utf-8') as file:
                introduction_content = file.read()

            with open(insight_report_path, 'r', encoding='utf-8') as file:
                insight_content = file.read()

            llm = ChatOpenAI(
                model=llm_configs["glmweb"].get("model_name", "default-model"),
                temperature=llm_configs["glmweb"].get("temperature", 0),
                api_key=llm_configs["glmweb"].get("api_key"),
                base_url=llm_configs["glmweb"].get("api_base")
            )

            system_template = """
            # 角色
            你是一个小红书爆款写作专家。你的任务是结合提供的介绍和洞察报告，生成适合社交媒体传播的内容。

            ## 技能
            ### 技能 1：内容整合
            - 将介绍和洞察报告的内容整合，提取关键信息和吸引人的点。

            ### 技能 2：创意写作
            - 根据整合的信息，创作出吸引人的社交媒体帖子。

            ## 输出要求
            - 确保内容忠实于原始材料，同时具有吸引力和创意。
            - 【重要】输出内容应适合社交媒体传播，简洁且富有吸引力。
            - 每一个段落含有适当的emoji表情，文末有合适的tag标签

            """

            human_message = f"\n\n## 介绍内容：\n{introduction_content}\n\n## 洞察报告内容：\n{insight_content}"

            messages = [
                SystemMessage(content=system_template),
                HumanMessage(content=human_message),
            ]

            json_result = llm.invoke(messages)
            parser = StrOutputParser()
            llm_result = parser.invoke(json_result)

            output_file_path = os.path.join(subfolder_path, '社交媒体内容.md')
            with open(output_file_path, 'w', encoding='utf-8') as file:
                file.write(llm_result)

            print(f"社交媒体内容已保存到 {output_file_path}")
        else:
            print(f"文件夹 {subfolder_path} 中缺少 '介绍.md' 或 '最终洞察报告.md'")

    # 遍历文件夹
    for root, dirs, files in os.walk(folder_path):
        for dir in dirs:
            subfolder_path = os.path.join(root, dir)
            process_subfolder(subfolder_path)