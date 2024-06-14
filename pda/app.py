import streamlit as st
import os
from logs import setup_logger
from pictures_ocr import process_image
from llm_extraction import extract_bookinfo
from process_excel import process_excel_files
from json_excel import save_to_excel
from datetime import date
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件

# v0.3 自动文件夹路径
# v0.4 api存储在 .env中

def check_folder_exists(parent_folder):
    today = date.today().strftime('%Y-%m-%d')
    folder_path = os.path.join(parent_folder, today)
    if os.path.exists(folder_path):
        return folder_path
    else:
        return create_folder(parent_folder)

def create_folder(parent_folder):
    today = date.today().strftime('%Y-%m-%d')
    new_folder = os.path.join(parent_folder, today)
    os.makedirs(new_folder, exist_ok=True)

    handwriting_folder = os.path.join(new_folder, 'handwriting')
    screenshot_folder = os.path.join(new_folder, 'screenshot')
    os.makedirs(handwriting_folder, exist_ok=True)
    os.makedirs(screenshot_folder, exist_ok=True)

    return new_folder

def main():
    st.title("读者荐购信息整理")

    # 获取用户输入的文件夹路径
    folder_path = st.text_input('输入要处理的文件夹路径')
    
    # 添加一个文本框来显示生成的路径
    generated_path = st.empty()

    # 添加按钮用于生成文件夹路径
    if st.button("生成路径"):
        parent_folder = r'E:\scripts\AI-demo\pda-git'  # 修改为你的文件夹路径
        generated_folder_path = check_folder_exists(parent_folder)
        generated_path.text(generated_folder_path)

    # 大模型选择框
    model_name = st.selectbox("选择模型", ["GLM-4-Air", "GLM-4-0520"], index=0)
  

    if st.button("开始处理"):
        BASE_PATH = folder_path
        HANDWRITING_FOLDER_PATH = os.path.join(BASE_PATH, 'handwriting')
        SCREENSHOT_FOLDER_PATH = os.path.join(BASE_PATH, 'screenshot')

        # 从环境变量中获取 access_token 和 api_key
        ocr_access_token = os.getenv("ACCESS_TOKEN")
        llm_api_key = os.getenv("API_KEY")

        # OCR配置
        handwriting_ocr_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting"
        screenshot_ocr_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
        access_token = ocr_access_token

        # 日志文件路径
        LOG_FOLDER_PATH = os.path.join(BASE_PATH, 'logs')
        logger = setup_logger(LOG_FOLDER_PATH)

        # LLM配置
        llm_config = {"model_name": model_name, "api_key": llm_api_key}

        # 处理图像文件
        with st.spinner("正在处理图片..."):
            image_processed = False
            for folder_path, ocr_url in [(HANDWRITING_FOLDER_PATH, handwriting_ocr_url), (SCREENSHOT_FOLDER_PATH, screenshot_ocr_url)]:
                image_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
                if not image_files:
                    logger.info(f"文件夹 {folder_path} 下没有图像文件")
                    continue

                image_processed = True
                for image_path in image_files:
                    ocr_result, file_name = process_image(image_path, ocr_url, access_token, logger)
                    if ocr_result:
                        try:
                            extract_bookinfo_result = extract_bookinfo(ocr_result, file_name, llm_config, logger)
                            save_to_excel(extract_bookinfo_result, BASE_PATH, logger)
                        except Exception as e:
                            logger.error(f"extract_bookinfo 函数运行错误: {str(e)}")
                            save_to_excel({'原文': ocr_result, '原件': file_name, '错误信息': '大模型API调用错误'}, BASE_PATH, logger)

        # 检查是否存在xlsx文件
        excel_files = [f for f in os.listdir(BASE_PATH) if f.endswith('.xlsx')]
        if excel_files:
            with st.spinner("正在处理Excel文件..."):
                process_excel_files(BASE_PATH, logger, llm_config)
                logger.info("Excel文件处理完毕")
        else:
            logger.info("未找到Excel文件，跳过处理")

        st.success("处理完成!")

if __name__ == "__main__":
    main()