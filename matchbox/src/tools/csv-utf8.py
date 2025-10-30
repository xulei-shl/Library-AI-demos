import chardet
import os

def convert_csv_to_utf8(input_path, output_path=None, overwrite=False):
    """
    将本地 CSV 文件转换为 UTF-8 编码。

    参数:
        input_path (str): 输入 CSV 文件的路径。
        output_path (str, optional): 输出文件路径。若为 None 且 overwrite=False，则自动添加 '_utf8' 后缀。
        overwrite (bool): 是否覆盖原文件（慎用）。

    返回:
        str: 输出文件的路径。
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    # 自动检测原始编码
    with open(input_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']

    if encoding is None:
        raise ValueError("无法检测文件编码，请手动指定。")

    print(f"检测到编码: {encoding} (置信度: {confidence:.2%})")

    # 读取原始内容
    try:
        with open(input_path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()
    except UnicodeDecodeError as e:
        raise ValueError(f"使用检测到的编码 {encoding} 读取文件失败: {e}")

    # 确定输出路径
    if overwrite:
        output_path = input_path
    elif output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_utf8{ext}"

    # 写入 UTF-8 编码文件
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)

    print(f"文件已成功转换为 UTF-8 并保存至: {output_path}")
    return output_path


# 使用示例
if __name__ == "__main__":
    input_file = r"E:\Desk\object_results.csv"  # 替换为你的 CSV 文件路径
    convert_csv_to_utf8(input_file)  # 默认生成 your_file_utf8.csv
    # 或者：convert_csv_to_utf8(input_file, overwrite=True)  # 覆盖原文件（谨慎！）
