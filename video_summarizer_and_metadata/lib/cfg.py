import os
import sys

# 设置根目录
ROOT_DIR = os.getcwd().replace('\\', '/')

# 设置临时目录
TMP_DIR = os.path.join(ROOT_DIR, 'tmp').replace('\\', '/')

# 确保临时目录存在
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR, exist_ok=True)

# 设置环境变量
if sys.platform == 'win32':
    os.environ['PATH'] = f'{ROOT_DIR};{ROOT_DIR}\\ffmpeg;' + os.environ['PATH']
else:
    os.environ['PATH'] = f'{ROOT_DIR}:{ROOT_DIR}/ffmpeg:' + os.environ['PATH']