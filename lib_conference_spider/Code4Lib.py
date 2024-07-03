import requests
from bs4 import BeautifulSoup
import pandas as pd
from dotenv import load_dotenv
import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fanyi import translate_text
from keyword_extract import keyword_extract


load_dotenv()

def get_abstract_with_selenium(url):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # 无头模式
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    
    try:
        # 等待页面中的 <p> 元素出现
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'p'))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        abstract = soup.find('p').text.strip()
    except Exception as e:
        print(f"Selenium 获取摘要失败: {e}")
        abstract = ""
    finally:
        driver.quit()
    
    return abstract

def scrape_talks(start_year, end_year, llm_config, template_key):
    data = []

    for year in range(start_year, end_year + 1):
        base_url = f"https://{year}.code4lib.org/schedule/day-"
        day = 1

        while True:
            schedule_url = f"{base_url}{day}/"
            response = requests.get(schedule_url)

            if response.status_code == 404:
                break

            soup = BeautifulSoup(response.content, 'html.parser')
            talks = soup.find_all('div', class_='row talk-row')

            for talk in talks:
                talk_title_tag = talk.find('h3', class_='talk-title')
                talk_link = talk_title_tag.find('a')['href']
                talk_title = talk_title_tag.text.strip()

                speakers = talk.find_all('div', class_='col-sm-3 text-center')
                speaker_names = [speaker.find('span').text.strip() for speaker in speakers]
                speaker_names = ", ".join(speaker_names)

                try:
                    talk_response = requests.get(f"https://{year}.code4lib.org{talk_link}")
                    talk_response.raise_for_status()  # 检查请求是否成功
                    talk_soup = BeautifulSoup(talk_response.content, 'html.parser')
                    abstract = talk_soup.find('p').text.strip()
                except requests.exceptions.RequestException as e:
                    print(f"打开链接失败: {talk_link}, 错误: {e}")
                    abstract = get_abstract_with_selenium(f"https://{year}.code4lib.org{talk_link}")

                translated_title = translate_text(talk_title, "ZH")
                if abstract:
                    translated_abstract = translate_text(abstract, "ZH")
                else:
                    translated_abstract = ""


                if abstract:
                    merged_text = f"### 报告名\n{translated_title}\n\n### 报告摘要\n{translated_abstract}"
                else:
                    merged_text = f"### 报告名\n{translated_title}"
                keywords = keyword_extract(merged_text, llm_config, template_key)

                # 删除包含 "关键词_??" 格式的字符串
                keywords = [kw for kw in keywords.split(',') if not kw.strip().startswith('关键词_')]
                keywords = ', '.join(keywords)

                data.append([year, talk_title, translated_title, speaker_names, abstract, translated_abstract, f"https://{year}.code4lib.org{talk_link}", keywords])

                print(f"\n---------------------------------------------------------\n")
                print(f"爬取成功: {talk_title}")
                print(f"翻译成功: {translated_title}")
                print(f"LLM调用成功: {keywords}")

                # 立即写入Excel
                file_name = f'C:\\Users\\Administrator\\Desktop\\Code4Lib-talks-{start_year}-{end_year}.xlsx'
                df = pd.DataFrame(data, columns=['会议年', 'Title', '报告名', 'Speakers', 'Abstract', '摘要', 'Link', '关键词'])
                df.to_excel(file_name, index=False)
                print(f"写入成功: {file_name}")

                wait_time = random.randint(1, 2)
                time.sleep(wait_time)

            day += 1
    print(f"\n--------------------数据已成功保存到文件----------------------------------\n")


if __name__ == "__main__":

    llm_configs = {
        "glm": {
            "temperature": 0,
            "model_name": os.getenv("GLM_MODEL_NAME"),
            "api_key": os.getenv("GLM_API_KEY"),
        },
        "lingyi": {
            "temperature": 0,
            "model_name": os.getenv("LINGYI_MODEL_NAME"),
            "api_base": os.getenv("LINGYI_API_BASE"),
            "api_key": os.getenv("LINGYI_API_KEY"),
        },
        "gpt": {
            "temperature": 0,
            "model_name": os.getenv("GPT_MODEL_NAME"),
            "api_base": os.getenv("GPT_API_BASE"),
            "api_key": os.getenv("GPT_API_KEY"),
        }
    }

    # 选择一个配置进行调用，例如 "glm"
    selected_config = "glm"    
    start_year = 2023
    end_year = 2024
    data = scrape_talks(start_year, end_year, llm_configs[selected_config], template_key="keywords")