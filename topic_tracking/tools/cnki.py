import time
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.action_chains import ActionChains
import os
from datetime import datetime
import pandas as pd
from exceptions import NoResultsFoundException
import streamlit as st

def webserver():
    # get直接返回，不再等待界面加载完成
    desired_capabilities = DesiredCapabilities.EDGE
    desired_capabilities["pageLoadStrategy"] = "none"

    # 设置微软驱动器的环境
    options = webdriver.EdgeOptions()
    # 设置浏览器不加载图片，提高速度
    options.add_argument("--headless")  # 添加无头模式选项
    options.add_argument("--disable-gpu")  # 禁用GPU加速
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})

    # 创建一个微软驱动器
    driver = webdriver.Edge(options=options)

    return driver

def open_page(driver, keyword, start_year=None, end_year=None, st=None):
    # 打开页面，等待两秒
    driver.get("https://kns.cnki.net/kns8s/AdvSearch?classid=YSTT4HG0")
    time.sleep(2)

    # 修改属性，使下拉框显示
    opt = driver.find_element(By.CSS_SELECTOR, 'div.sort-list')  # 定位元素
    driver.execute_script("arguments[0].setAttribute('style', 'display: block;')", opt)  # 执行 js 脚本进行属性的修改；arguments[0]代表第一个属性

    # 鼠标移动到下拉框中的[通讯作者]
    ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, 'li[data-val="RP"]')).perform()

    # 传入关键字
    WebDriverWait(driver, 100).until(
        EC.presence_of_element_located((By.XPATH, '''//*[@id="gradetxt"]/dd[1]/div[2]/input'''))
    ).send_keys(keyword)

    # 如果传入了起止年份,则在出版年度输入框中输入
    if start_year and end_year:
        start_year_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='起始年']")))
        end_year_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='结束年']")))
        start_year_input.send_keys(start_year)
        end_year_input.send_keys(end_year)

    # 使用JavaScript勾选“北大核心”复选框
    hx_checkbox = WebDriverWait(driver, 100).until(
        EC.presence_of_element_located((By.XPATH, '''//label/input[@key="HX"]'''))
    )
    driver.execute_script("arguments[0].click();", hx_checkbox)

    # 使用JavaScript勾选“CSSCI”复选框
    cssci_checkbox = WebDriverWait(driver, 100).until(
        EC.presence_of_element_located((By.XPATH, '''//label/input[@key="CSI"]'''))
    )
    driver.execute_script("arguments[0].click();", cssci_checkbox)

    # 点击搜索
    WebDriverWait(driver, 100).until(
        EC.presence_of_element_located((By.XPATH, '''//input[@class="btn-search"]'''))
    ).click()

    print("正在搜索，请稍后...")

    # 获取总文献数和页数
    try:
        res_unm = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
            (By.XPATH, '''//*[@id="countPageDiv"]/span[1]/em'''))
        ).text
        # 去除千分位里的逗号
        res_unm = int(res_unm.replace(",", ''))
        page_unm = int(res_unm / 20) + 1
        if st:
            st.info(f"共找到 {res_unm} 条结果, {page_unm} 页。")
        else:
            print(f"共找到 {res_unm} 条结果, {page_unm} 页。")
        return res_unm
    except:
        raise NoResultsFoundException("没有检索结果")

def get_info(driver, xpath):
    try:
        element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
        return element.text
    except:
        return '无'
    
def get_choose_info(driver, xpath1, xpath2, str):
    try: 
        if WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, xpath1))).text==str:
            return WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, xpath2))).text
        else:
            return '无'
    except:
        return '无'

def crawl_info(driver, count, term, file_path, st=None):
    try:
        # 获取基础信息
        print('正在获取基础信息...')
        title_xpath = f'''//*[@id="gridTable"]/div/div/table/tbody/tr[{term}]/td[2]'''
        author_xpath = f'''//*[@id="gridTable"]/div/div/table/tbody/tr[{term}]/td[3]'''
        source_xpath = f'''//*[@id="gridTable"]/div/div/table/tbody/tr[{term}]/td[4]'''
        date_xpath = f'''//*[@id="gridTable"]/div/div/table/tbody/tr[{term}]/td[5]'''
        quote_xpath = f'''//*[@id="gridTable"]/div/div/table/tbody/tr[{term}]/td[6]'''
        download_xpath = f'''//*[@id="gridTable"]/div/div/table/tbody/tr[{term}]/td[7]'''
        xpaths = [title_xpath, author_xpath, source_xpath, date_xpath, quote_xpath, download_xpath]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_elements = [executor.submit(get_info, driver, xpath) for xpath in xpaths]
        title, authors, source, date, quote, download = [future.result() for future in future_elements]

        # 如果 title 中包含 "网络首发", 则将其替换为空字符串
        if "网络首发" in title:
            title = title.replace(" 网络首发", "")

        if not quote.isdigit():
            quote = '0'
        if not download.isdigit():
            download = '0'
        print(f"{title} {authors} {source} {date} {quote} {download}\n")

        # 点击条目
        title_list = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "fz14")))
        title_list[term - 1].click()

        # 获取driver的句柄
        n = driver.window_handles

        # driver切换至最新生产的页面
        driver.switch_to.window(n[-1])
        time.sleep(3)

        # 开始获取页面信息
        # 点击展开
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '''//*[@id="ChDivSummaryMore"]'''))
            ).click()
        except:
            pass

        # 获取作者单位
        print('正在获取institute...')
        try:
            institute = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div[1]/div[3]/div/div/div[3]/div/h3[2]"))).text
        except:
            institute = '无'
        print(institute + '\n')

        # 获取摘要、关键词、专辑、专题
        # 获取摘要
        print('正在获取abstract...')
        try:
            abstract = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "abstract-text"))).text
        except:
            abstract = '无'
        print(abstract + '\n')

        # 获取关键词
        print('正在获取keywords...')
        try:
            keywords = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "keywords"))).text[:-1]
        except:
            keywords = '无'
        print(keywords + '\n')

        # 获取专辑
        print('正在获取publication...')
        xpaths = [
            ("/html/body/div[2]/div[1]/div[3]/div/div/div[6]/ul/li[1]/span", "/html/body/div[2]/div[1]/div[3]/div/div/div[6]/ul/li[1]/p"),
            ("/html/body/div[2]/div[1]/div[3]/div/div/div[6]/ul/li[2]/span", "/html/body/div[2]/div[1]/div[3]/div/div/div[6]/ul/li[2]/p"),
            ("/html/body/div[2]/div[1]/div[3]/div/div/div[7]/ul/li[1]/span", "/html/body/div[2]/div[1]/div[3]/div/div/div[7]/ul/li[1]/p"),
            ("/html/body/div[2]/div[1]/div[3]/div/div/div[7]/ul/li[2]/span", "/html/body/div[2]/div[1]/div[3]/div/div/div[7]/ul/li[2]/p"),
            ("/html/body/div[2]/div[1]/div[3]/div/div/div[4]/ul/li[1]/span", "/html/body/div[2]/div[1]/div[3]/div/div/div[4]/ul/li[1]/p")
        ]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(get_choose_info, driver, xpath1, xpath2, '专辑：') for xpath1, xpath2 in xpaths]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        publication = next((result for result in results if result != '无'), '无')
        print(publication + '\n')

        # 获取专题
        print('正在获取topic...')
        xpaths = [
            ("/html/body/div[2]/div[1]/div[3]/div/div/div[6]/ul/li[2]/span", "/html/body/div[2]/div[1]/div[3]/div/div/div[6]/ul/li[2]/p"),
            ("/html/body/div[2]/div[1]/div[3]/div/div/div[6]/ul/li[3]/span", "/html/body/div[2]/div[1]/div[3]/div/div/div[6]/ul/li[3]/p"),
            ("/html/body/div[2]/div[1]/div[3]/div/div/div[7]/ul/li[2]/span", "/html/body/div[2]/div[1]/div[3]/div/div/div[7]/ul/li[2]/p"),
            ("/html/body/div[2]/div[1]/div[3]/div/div/div[7]/ul/li[3]/span", "/html/body/div[2]/div[1]/div[3]/div/div/div[7]/ul/li[3]/p"),
            ("/html/body/div[2]/div[1]/div[3]/div/div/div[4]/ul/li[2]/span", "/html/body/div[2]/div[1]/div[3]/div/div/div[4]/ul/li[2]/p")
        ]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(get_choose_info, driver, xpath1, xpath2, '专题：') for xpath1, xpath2 in xpaths]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        topic = next((result for result in results if result != '无'), '无')
        print(topic+'\n')
        
        url = driver.current_url
        
        # 获取当前日期作为爬取时间
        current_date = datetime.now().strftime("%Y-%m-%d")

        # 修改写入文件的部分
        res = pd.DataFrame({
            '编号': [count],
            '题名': [title],
            '作者': [authors],
            '作者机构': [institute],
            '日期': [date],
            '期刊': [source],
            '专辑': [publication],
            '专题': [topic],
            '引用数': [quote],
            '下载数': [download],
            '关键词': [keywords],
            '摘要': [abstract],
            'URL': [url],
            '爬取时间': [current_date]
        })

        # 在循环开始前创建一个空的占位符
        placeholder = st.empty()
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # 追加写入CSV文件
        try:
            res.to_csv(file_path, mode='a', header=False, index=False, encoding='gbk')
            print(f"第{count}条写入CSV成功")
        except Exception as e:
            print(f'第{count}条写入失败:', str(e))
            raise e
    except:
        print(f" 第{count} 条爬取失败\n")
        # 跳过本条，接着下一个
        raise e

    finally:
        # 如果有多个窗口，关闭第二个窗口， 切换回主页
        n2 = driver.window_handles
        if len(n2) > 1:
            driver.close()
            driver.switch_to.window(n2[0])

def get_existing_data_count(file_path):
    if os.path.exists(file_path):
        encodings = ['gbk', 'utf-8']
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding, sep='\t')
                return len(df)
            except UnicodeDecodeError:
                continue
        print("Error reading file with both 'gbk' and 'utf-8' encodings.")
    return 0

# 假设 TOPICS_FILE 是包含主题词和文件路径的 CSV 文件
TOPICS_FILE = 'data/topics.csv'

def load_topics():
    if os.path.exists(TOPICS_FILE):
        return pd.read_csv(TOPICS_FILE)
    return pd.DataFrame(columns=['topic', 'file_path'])

def cnki_spider(selected_topic, start_year, end_year, st=None):
    keyword = selected_topic
    driver = webserver()  # 假设 webserver 是一个函数，需要定义或导入
    
    # 加载主题词
    topics_df = load_topics()
    
    # 获取文件路径
    file_path = topics_df[topics_df['topic'] == selected_topic]['file_path'].values[0]
    print(file_path)
    
    # 获取检索结果总数
    res_unm = open_page(driver, keyword, start_year, end_year, st)
    
    # 获取已有数据数量
    existing_data_count = get_existing_data_count(file_path)
    print(existing_data_count)
    
    if existing_data_count == 0:
        # 第一次爬取，爬取所有数据
        papers_need = res_unm
        if st:
            st.info(f"首次爬取，将爬取所有 {papers_need} 条数据。")
        else:
            print(f"首次爬取，将爬取所有 {papers_need} 条数据。")
    else:
        # 非首次爬取，计算需要爬取的差额
        papers_need = res_unm - existing_data_count
        print(papers_need)
        if papers_need > 0:
            if st:
                st.info(f"发现 {papers_need} 条新数据，开始爬取。")
            else:
                print(f"发现 {papers_need} 条新数据，开始爬取。")
        else:
            if st:
                st.info("没有新数据需要爬取。")
            else:
                print("没有新数据需要爬取。")
            driver.close()
            return
    
    # 开始爬取
    crawl(driver, papers_need, file_path)

    # 关闭浏览器
    driver.close()

def crawl(driver, papers_need, file_path):
    count = 1
    current_page = 1

    print(f"从第 {count} 条开始爬取\n")

    while count <= papers_need:
        # 等待加载完全，休眠3S
        time.sleep(3)

        # 获取当前页面的条目数
        items_on_page = len(WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "fz14"))))

        # 循环网页一页中的条目
        for i in range((count-1) % 20 + 1, items_on_page + 1):
            print(f"\n### 正在爬取第 {count} 条(第{current_page}页第{i}条) #######################################\n")
            crawl_info(driver, count, i, file_path, st)
            count += 1
            if count > papers_need:
                break

        # 检查是否有下一页
        next_page = driver.find_elements(By.XPATH, "//a[@id='PageNext']")
        if next_page and "disabled" not in next_page[0].get_attribute("class"):
            next_page[0].click()
            current_page += 1
        else:
            print("已到达最后一页，爬取结束")
            break

    print("爬取完毕！")


if __name__ == "__main__":
    # 这部分代码只在直接运行脚本时执行，不影响作为模块导入时的行为
    selected_topic = "特藏建设 图书馆"
    start_year = "2021"
    end_year = "2021"
    cnki_spider(selected_topic, start_year, end_year)