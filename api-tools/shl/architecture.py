import requests
import os
import sys
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

# 解析项目根目录（从 docs/tools/shlname.py 往上两级）
project_root = Path(__file__).resolve().parents[2]

# 优先从项目根目录加载 .env，若不存在则回退到自动搜索
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(find_dotenv(usecwd=True))

# 读取上海图书馆 API Key
shl_key = os.getenv("SHL_API_KEY")
if not shl_key:
    print(f"未读取到环境变量 SHL_API_KEY。尝试路径：{env_path}")
    print("请确认项目根目录下存在 .env 并包含 SHL_API_KEY=...，或检查运行目录与加载路径。")
    sys.exit(1)

url = "http://data1.library.sh.cn/shnh/dydata/webapi/architecture/getArchitecture"
params = {
    "freetext": "长江剧场",
    "key": shl_key,  # 注意：该接口要求大写'Key'
    "pageth": 1,
    "pageSize": 10
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

try:
    response = requests.get(url, params=params, headers=headers, timeout=(5, 20))
except requests.RequestException as e:
    print("请求失败:", e)
    sys.exit(1)

if response.status_code == 200:
    try:
        data = response.json()
    except ValueError:
        print("返回内容非 JSON：", response.text[:500])
        sys.exit(1)
    print(data)
else:
    print("请求失败，状态码错误:", response.status_code)
    print("响应:", response.text[:500])