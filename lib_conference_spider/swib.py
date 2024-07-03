import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from fanyi import translate_text
from keyword_extract import keyword_extract
import os
from dotenv import load_dotenv

load_dotenv()

def scrape_talks(start_year, end_year, llm_config, template_key):
    data = []
    seen_titles = set()  # 用于存储已经爬取过的标题

    for year in range(start_year, end_year + 1):
        base_url = f"https://swib.org/swib{str(year)[-2:]}/programme.html#day"
        day = 1

        while True:
            schedule_url = f"{base_url}{day}"
            response = requests.get(schedule_url)

            if response.status_code == 404:
                break

            soup = BeautifulSoup(response.content, 'html.parser')
            talks = soup.find_all('tr', id=lambda x: x and x.startswith('contrib'))

            new_data = []  # 用于存储当前页面的新数据

            for talk in talks:
                talk_title_tag = talk.find('h4')
                if not talk_title_tag:
                    continue
                talk_title = talk_title_tag.text.strip()

                # 检查是否已经爬取过这个标题
                if talk_title in seen_titles:
                    continue

                seen_titles.add(talk_title)

                abstract_tag = talk.find('details')
                if abstract_tag:
                    abstract = abstract_tag.text.strip()
                    abstract = abstract.replace("Abstract", "", 1).strip()
                else:
                    abstract = ""

                print(f"\n---------------------------------------------------------\n")
                print(abstract)

                # 翻译 Title 和 Abstract
                translated_title = translate_text(talk_title, "ZH")
                if abstract:
                    translated_abstract = translate_text(abstract, "ZH")
                else:
                    translated_abstract = ""

                # 处理 Slides 和 Video 链接
                slides_link = ""
                video_link = ""

                for link in talk.find_all('a'):
                    if 'Slides' in link.text:
                        slides_link = link['href']
                    elif 'Video' in link.text:
                        video_link = link['href']

                # 拼接中文报告名和中文摘要，调用 keyword_extract 函数
                if abstract:
                    merged_text = f"### 报告名\n{translated_title}\n\n### 报告摘要\n{translated_abstract}"
                else:
                    merged_text = f"### 报告名\n{translated_title}"
                keywords = keyword_extract(merged_text, llm_config, template_key)

                # 删除包含 "关键词_??" 格式的字符串
                keywords = [kw for kw in keywords.split(',') if not kw.strip().startswith('关键词_')]
                keywords = ', '.join(keywords)

                new_data.append([year, talk_title, translated_title, abstract, translated_abstract, f"https://swib.org/swib{str(year)[-2:]}/programme.html#day{day}", slides_link, video_link, keywords])

                print(f"\n---------------------------------------------------------\n")
                print(f"爬取成功: {talk_title}")
                print(f"翻译成功: {translated_title}")
                print(f"关键词提取成功: {keywords}")

            if not new_data:  # 如果没有新数据，说明已经爬取完所有数据
                break

            data.extend(new_data)

            # 立即写入Excel
            file_name = f'C:\\Users\\Administrator\\Desktop\\SWIB-talks-{start_year}-{end_year}.xlsx'
            df = pd.DataFrame(data, columns=['会议年', 'Title', '报告名', 'Abstract', '摘要', 'Link', 'ppt', '视频', '关键词'])
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
    end_year = 2023
    data = scrape_talks(start_year, end_year, llm_configs[selected_config], template_key="keywords")