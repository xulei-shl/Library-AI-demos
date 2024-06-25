import os
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from prompts import TEMPLATES

def social_media_writer(folder_path, llm_configs, template_key):
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

            system_template = TEMPLATES.get(template_key, TEMPLATES["xhs"])

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