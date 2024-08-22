import requests
import base64
import os
from ocr_to_md import ocr_json_to_md
from merge_md import merge_md_files

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
        logger.info(f"OCR请求成功: {image_path}")
        logger.info(f"OCR结果: {ocr_result}")
        print(f"\n---------------------OCR原文-------------------------\n")
        print(ocr_result)

        # 检查 OCR 结果是否为空
        if not ocr_result['words_result']:
            logger.info(f"OCR结果为空，跳过后续处理: {image_path}")
            print(f"\n---------------------OCR结果为空-------------------------\n")
            print(f"OCR结果为空，跳过后续处理: {image_path}")
            return None, None, None

        file_name = image_name.split('.')[0]  # 去掉文件扩展名
        md_result = ocr_json_to_md(ocr_result)  # 调用 ocr_to_md.py 中的函数

        # 保存结果到 output/sources 文件夹
        output_folder = os.path.join(os.path.dirname(image_path), 'output', 'sources')
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        ocr_result_path = os.path.join(output_folder, f"{file_name}_ocr_result.md")
        md_result_path = os.path.join(output_folder, f"{file_name}_md_result.md")

        with open(ocr_result_path, 'w', encoding='utf-8') as f:
            f.write(str(ocr_result))

        with open(md_result_path, 'w', encoding='utf-8') as f:
            f.write(md_result)

        logger.info(f"结果已保存到: {ocr_result_path} 和 {md_result_path}")
        print(f"\n---------------------结果已保存-------------------------\n")
        print(f"OCR结果已保存到: {ocr_result_path}")
        print(f"Markdown结果已保存到: {md_result_path}")

        return ocr_result, file_name, md_result
    else:
        logger.error(f"OCR请求失败: {image_path}")
        print(f"----------------------------------------")
        print(f"OCR请求失败: {image_path}")

        return None, None, None

def process_images(image_folder, ocr_url, access_token, logger):
    for filename in os.listdir(image_folder):
        if filename.endswith('.jpg') or filename.endswith('.png'):  # 可以根据需要添加其他图片格式
            image_path = os.path.join(image_folder, filename)
            process_image(image_path, ocr_url, access_token, logger)

    # 处理完所有图片后，调用合并函数
    output_folder = os.path.join(image_folder, 'output')
    merge_md_files(output_folder)