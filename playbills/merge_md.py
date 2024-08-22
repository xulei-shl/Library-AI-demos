import os
import re

def merge_files(source_folder, output_folder, result_suffix, final_suffix):
    # 获取所有生成的文件
    files = [f for f in os.listdir(source_folder) if f.endswith(result_suffix)]

    # 使用字典来分组文件
    grouped_files = {}

    for file in files:
        # 提取文件名前缀
        match = re.match(r'(.*)-\d+' + result_suffix, file)
        if match:
            prefix = match.group(1)
            if prefix not in grouped_files:
                grouped_files[prefix] = []
            grouped_files[prefix].append(file)

    # 合并相同前缀的文件
    for prefix, files in grouped_files.items():
        merged_content = []
        for file in files:
            file_path = os.path.join(source_folder, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 检查 words_result_num 是否为 0
                if result_suffix == '_ocr_result.md' and re.search(r"'words_result_num': 0", content):
                    continue
                # 添加文件名作为分隔符
                merged_content.append(f"# {file}")
                merged_content.append(content)

        # 写入合并后的文件
        if merged_content:
            merged_file_path = os.path.join(output_folder, f"{prefix}{final_suffix}")
            with open(merged_file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(merged_content))

    print(f"合并后的 {result_suffix} 文件已保存到: {output_folder}")

def merge_md_files(output_folder):
    source_folder = os.path.join(output_folder, 'sources')
    merge_files(source_folder, output_folder, '_md_result.md', '_md_final_result.md')
    merge_files(source_folder, output_folder, '_ocr_result.md', '_ocr_1_final_result.md')

    # 处理 _ocr_1_final_result.md 文件
    ocr_1_final_files = [f for f in os.listdir(output_folder) if f.endswith('_ocr_1_final_result.md')]
    for file in ocr_1_final_files:
        file_path = os.path.join(output_folder, file)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用正则表达式提取 words 字段中的文本
        words_pattern = re.compile(r"'words': '([^']*)'")
        words = words_pattern.findall(content)
        processed_content = "\n".join(words)

        # 写入处理后的文件
        processed_file_path = os.path.join(output_folder, file.replace('_ocr_1_final_result.md', '_ocr_final_result.md'))
        with open(processed_file_path, 'w', encoding='utf-8') as f:
            f.write(processed_content)

    print(f"处理后的 _ocr_1_final_result.md 文件已保存到: {output_folder}")

# 测试函数
# if __name__ == "__main__":
#     output_folder = r"E:\scripts\jiemudan\1\output"
#     merge_md_files(output_folder)