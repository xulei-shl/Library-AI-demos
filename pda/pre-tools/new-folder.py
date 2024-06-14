import os
from datetime import date

# 指定父文件夹路径
parent_folder = r'C:\Users\Administrator\Desktop\pda'

# 获取当天日期并创建文件夹
today = date.today().strftime('%Y-%m-%d')
new_folder = os.path.join(parent_folder, today)
os.makedirs(new_folder, exist_ok=True)

# 在新建的文件夹下创建子文件夹
handwriting_folder = os.path.join(new_folder, 'handwriting')
screenshot_folder = os.path.join(new_folder, 'screenshot')
os.makedirs(handwriting_folder, exist_ok=True)
os.makedirs(screenshot_folder, exist_ok=True)

print(f'已成功创建文件夹: {new_folder}')
print(f'已成功创建子文件夹: {handwriting_folder}, {screenshot_folder}')