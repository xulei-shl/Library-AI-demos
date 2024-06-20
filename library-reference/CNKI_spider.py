import time
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.action_chains import ActionChains
import re

class PaperCrawler:
    def __init__(self, keywords, start_year=None, end_year=None, papers_need=10):
        self.keywords = keywords
        self.start_year = start_year
        self.end_year = end_year
        self.papers_need = papers_need
        self.driver = self.webserver()

    def webserver(self):
        # get直接返回,不再等待界面加载完成
        desired_capabilities = DesiredCapabilities.EDGE
        desired_capabilities["pageLoadStrategy"] = "none"

        # 设置微软驱动器的环境
        options = webdriver.EdgeOptions()
        # 设置浏览器不加载图片,提高速度
        options.add_argument("--headless")  # 添加无头模式选项
        options.add_argument("--disable-gpu")  # 禁用GPU加速
        options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})

        # 创建一个微软驱动器
        driver = webdriver.Edge(options=options)

        return driver

    def open_page(self):
        # 打开页面,等待两秒
        driver = self.driver
        driver.get("https://kns.cnki.net/kns8s/AdvSearch?classid=YSTT4HG0")
        time.sleep(2)

        # 修改属性,使下拉框显示
        opt = driver.find_element(By.CSS_SELECTOR, 'div.sort-list')  # 定位元素
        driver.execute_script("arguments[0].setAttribute('style', 'display: block;')", opt)  # 执行 js 脚本进行属性的修改;arguments[0]代表第一个属性

        # 鼠标移动到下拉框中的[通讯作者]
        ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, 'li[data-val="RP"]')).perform()

        # 传入关键字
        WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((By.XPATH, '''//*[@id="gradetxt"]/dd[1]/div[2]/input'''))
        ).send_keys(self.keywords)

        # 如果传入了起止年份,则在出版年度输入框中输入
        if self.start_year and self.end_year:
            start_year_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='起始年']")))
            end_year_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='结束年']")))
            start_year_input.send_keys(self.start_year)
            end_year_input.send_keys(self.end_year)

        # 使用JavaScript勾选"北大核心"复选框
        hx_checkbox = WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((By.XPATH, '''//label/input[@key="HX"]'''))
        )
        driver.execute_script("arguments[0].click();", hx_checkbox)

        # 使用JavaScript勾选"CSSCI"复选框
        cssci_checkbox = WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((By.XPATH, '''//label/input[@key="CSI"]'''))
        )
        driver.execute_script("arguments[0].click();", cssci_checkbox)

        # 点击搜索
        WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((By.XPATH, '''//input[@class="btn-search"]'''))
        ).click()

        print("正在搜索,请稍后...")

        # 获取总文献数和页数
        try:
            res_unm_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '''//*[@id="countPageDiv"]/span[1]/em'''))
            )
            res_unm = res_unm_elem.text
            res_unm = int(res_unm.replace(",", ''))
            page_unm = int(res_unm / 20) + 1
            print(f"------------------CNKI搜索成功-------------------------")
            print(f"共找到 {res_unm} 条结果, {page_unm} 页。")
            return res_unm
        except:
            print("无法获取总文献数和页数信息")
            return 0

    def get_info(self, xpath):
        driver = self.driver
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
            return element.text
        except:
            return '无'

    def crawl_info(self, term, results):
        driver = self.driver
        try:
            # 获取基础信息
            print('正在获取基础信息...\n')
            title_xpath = f'''//*[@id="gridTable"]/div/div/table/tbody/tr[{term}]/td[2]'''
            author_xpath = f'''//*[@id="gridTable"]/div/div/table/tbody/tr[{term}]/td[3]'''
            source_xpath = f'''//*[@id="gridTable"]/div/div/table/tbody/tr[{term}]/td[4]'''
            date_xpath = f'''//*[@id="gridTable"]/div/div/table/tbody/tr[{term}]/td[5]'''
            xpaths = [title_xpath, author_xpath, source_xpath, date_xpath]
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_elements = [executor.submit(self.get_info, xpath) for xpath in xpaths]
            title, authors, source, date = [future.result() for future in future_elements]

            # 如果 title 中包含 "网络首发", 则将其替换为空字符串
            if "网络首发" in title:
                title = title.replace(" 网络首发", "")

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

            # 获取摘要、关键词
            # 获取摘要
            print('正在获取abstract...\n')
            try:
                abstract = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "abstract-text"))).text
            except:
                abstract = '无'

            # 获取关键词
            print('正在获取keywords...\n')
            try:
                keywords = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "keywords"))).text[:-1]
            except:
                keywords = '无'

            url = driver.current_url

            # 将结果整合为 Markdown 格式
            res = f"## {term}. {title}\n\n**作者:** {authors}\n\n**期刊:** {source}\n\n**日期:** {date}\n\n### 摘要\n\n{abstract}\n\n### 关键词\n\n{keywords}\n\n**URL:** {url}\n\n---\n\n"
            results.append(res)

            print("爬取成功！\n")

        except Exception as e:
            print(f"爬取失败: {str(e)}\n")

        finally:
            # 如果有多个窗口，关闭第二个窗口， 切换回主页
            n2 = driver.window_handles
            if len(n2) > 1:
                driver.close()
                driver.switch_to.window(n2[0])

    def crawl(self):
        while True:
            res_unm = self.open_page()
            if res_unm == 0:
                return ""

            papers_need = self.papers_need if self.papers_need <= res_unm else res_unm
            results = []

            print(f"爬取前 {papers_need} 条数据\n")
            for i in range(1, papers_need + 1):
                print(f"\n### 正在爬取第 {i} 条 #######################################\n")
                self.crawl_info(i, results)

            print("爬取完毕！")
            print(f"\n### 爬取结果如下: #######################################\n")

            markdown_results = "".join(results)
            print(markdown_results)

            break  # 如果需要继续搜索,可以移除这一行

        # 关闭浏览器
        self.driver.quit()

        return markdown_results

# 测试
# if __name__ == "__main__":
#     # 在这里输入所需的参数
#     keywords = "中美地缘关系"
#     start_year = "2020"
#     end_year = "2024"
#     papers_need = 5

#     # 实例化 PaperCrawler 类并调用 crawl 方法
#     crawler = PaperCrawler(keywords, start_year, end_year, papers_need)
#     results = crawler.crawl()
#     print(results)