import requests
import base64
import os

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_image(image_path, ocr_url, access_token, logger):
    image_name = os.path.basename(image_path)
    logger.info(f"当前处理图片名: {image_name}")
    print(f"\n-----------------当前处理图片名-------------------------\n")
    print(image_name)

    ocr_img = image_to_base64(image_path)
    params = {"image": ocr_img}
    request_url = ocr_url + "?access_token=" + access_token
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    response = requests.post(request_url, data=params, headers=headers)

    if response:
        ocr_result = response.json()
        formatted_text = format_ocr_result(ocr_result)
        logger.info(f"OCR请求成功: {image_path}")
        logger.info(f"OCR结果: {formatted_text}")
        print(f"\n---------------------OCR原文-------------------------\n")
        print(formatted_text)
        
        file_name = image_name
        return formatted_text, file_name
    else:
        logger.error(f"OCR请求失败: {image_path}")
        print(f"----------------------------------------")
        print(f"OCR请求失败: {image_path}")

        return None, None

def format_ocr_result(ocr_result):
    formatted_text = []

    if 'words_result' in ocr_result:
        words_list = [item['words'] for item in ocr_result['words_result']]
        formatted_text = ' '.join(words_list)

    return formatted_text
