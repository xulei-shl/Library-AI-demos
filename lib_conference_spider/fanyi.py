import os
import random
import hashlib
import requests
import deepl
from dotenv import load_dotenv

load_dotenv()

def translate_text(text, target_lang):
    try:
        auth_key = os.getenv("DEEPL_AUTH_KEY")
        translator = deepl.Translator(auth_key)
        result = translator.translate_text(text, target_lang=target_lang)
        translated_text = result.text
    except Exception as e:
        print(f"--------------------DeepL翻譯失敗，調用百度翻译--------------------------")
        translated_text = baidu_fanyi(text)

    return translated_text

def baidu_fanyi(query):
    appid = os.getenv("BAIDU_APPID")  # 你的appid
    secretKey = os.getenv("BAIDU_SECRET_KEY")  # 你的密钥
    salt = random.randint(1, 10)  # 随机数
    code = appid + query + str(salt) + secretKey
    sign = hashlib.md5(code.encode()).hexdigest()  # 签名
    api = os.getenv("BAIDU_FANYI_URL")
    data = {
        "q": query,
        "from": "auto",
        "to": "auto",
        "appid": appid,
        "salt": salt,
        "sign": sign
    }
    response = requests.post(api, data)
    try:
        result = response.json()
        dst = result.get("trans_result")[0].get("dst")
    except Exception as e:
        dst = query
    finally:
        return dst