import os
from logs import setup_logger
from pictures_ocr import process_image
from llm_extraction import extract_bookinfo
from process_excel import process_excel_files
from json_excel import save_to_excel
import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件

def main():
    # 文件夹配置
    BASE_PATH = r'C:\Users\Administrator\Desktop\pda\2024-06-04'
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
    LOG_FOLDER_PATH = r'C:\Users\Administrator\Desktop\pda\logs'
    logger = setup_logger(LOG_FOLDER_PATH)

    # LLM配置
    llm_config = {
        #"model_name": "glm-3-turbo",
        "model_name": "GLM-4-Air",
        "api_key": llm_api_key,
    }

    # 处理图像文件
    for folder_path, ocr_url in [(HANDWRITING_FOLDER_PATH, handwriting_ocr_url), (SCREENSHOT_FOLDER_PATH, screenshot_ocr_url)]:
        image_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
        if not image_files:
            logger.info(f"文件夹 {folder_path} 下没有图像文件")
            continue

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
        process_excel_files(BASE_PATH, logger, llm_config)
        logger.info("Excel文件处理完毕")
    else:
        logger.info("未找到Excel文件，跳过处理")
        print(f"----------------------------------------")
        print("未找到Excel文件，跳过处理")

if __name__ == "__main__":
    main()