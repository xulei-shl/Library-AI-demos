import time
import concurrent.futures
from playwright.sync_api import sync_playwright
from datetime import datetime
import pandas as pd
import os
from unit.log_crawl import log_crawl_info

# 0.2 使用导出与分析的逻辑获取文献元数据

def webserver():
    p = sync_playwright().start()
    # Launch browser
    browser = p.chromium.launch(headless=True)
    
    # 创建新的上下文，只设置 accept_downloads
    context = browser.new_context(
        accept_downloads=True
    )
    
    # Disable images for faster loading
    context.route("**/*.{png,jpg,jpeg}", lambda route: route.abort())
    
    # Create a new page
    page = context.new_page()
    
    # Set page load strategy to none (similar to Selenium)
    page.set_default_timeout(60000)  # 60 seconds timeout
    
    return page, browser, context, p

def open_page(page, keyword, start_year=None, end_year=None, check_core=False):
    # Open the page
    page.goto("https://kns.cnki.net/kns8s/AdvSearch?classid=YSTT4HG0", wait_until="domcontentloaded")
    time.sleep(2)

    # Input keyword
    keyword_input = page.locator('''//*[@id="gradetxt"]/dd[1]/div[2]/input''')
    keyword_input.fill(keyword)
    
    # 勾选同义词扩展选项
    synonym_checkbox = page.locator('''//input[@data-id="TY"]''')
    synonym_checkbox.check()

    # Input start and end year if provided
    if start_year or end_year:
        if start_year:
            start_year_input = page.locator("input[placeholder='起始年']")
            start_year_input.fill(start_year)
        if end_year:
            end_year_input = page.locator("input[placeholder='结束年']")
            end_year_input.fill(end_year)
    else:
        # 如果未提供年份，选择"最近一年"选项
        # 点击展开下拉框
        page.click('.tit-dropdown-box .sort-default')
        time.sleep(1)
        # 选择"最近一年"选项（通过文本内容定位）
        page.evaluate('''() => {
            const links = document.querySelectorAll('.sort-list li a');
            for (const link of links) {
                if (link.textContent.trim() === '最近一年') {
                    link.click();
                    break;
                }
            }
        }''')

    # Check core journal options if specified
    if check_core:
        hx_checkbox = self.page.locator('''//label/input[@key="SI"]''')
        hx_checkbox.check()

        scie_checkbox = self.page.locator('''//label/input[@key="EI"]''')
        scie_checkbox.check()

        scie_checkbox = self.page.locator('''//label/input[@key="CSD"]''')
        scie_checkbox.check()

        scie_checkbox = self.page.locator('''//label/input[@key="AMI"]''')
        scie_checkbox.check()             
        # Check "北大核心" checkbox
        hx_checkbox = page.locator('''//label/input[@key="HX"]''')
        hx_checkbox.check()

        # Check "CSSCI" checkbox
        cssci_checkbox = page.locator('''//label/input[@key="CSI"]''')
        cssci_checkbox.check()

    # Click search button
    search_button = page.locator('''//input[@class="btn-search"]''')
    search_button.click()
    print("正在搜索，请稍后...")
    
    # 等待搜索结果加载
    page.wait_for_selector('//*[@id="countPageDiv"]/span[1]/em', timeout=10000)
    
    # 设置每页显示50条
    page.click('#perPageDiv .sort-default')
    page.click('ul.sort-list li[data-val="50"] a')
    time.sleep(2)  # 等待页面刷新
    
    # 获取总结果数
    try:
        res_unm_element = page.locator('//*[@id="countPageDiv"]/span[1]/em')
        res_unm = res_unm_element.inner_text().replace(",", "")
        res_unm = int(res_unm)
        page_unm = int(res_unm / 50) + 1
        print(f"共找到 {res_unm} 条结果，{page_unm} 页。")
        return res_unm
    except Exception:
        return 0

def select_all_and_export(page, total_results, selected_topic):
    """选择所有结果并导出"""
    selected_count = 0
    current_page = 1
    max_results = 300  # 设置最大选择数量为300条
    
    while selected_count < total_results:
        # 等待页面加载完成
        page.wait_for_selector('#selectCheckAll1', timeout=10000)
        time.sleep(2)
        
        # 点击全选
        page.click('#selectCheckAll1')
        time.sleep(1)
        
        # 获取当前选中数量
        select_count_text = page.locator('#selectCount').inner_text()
        selected_count = int(select_count_text)
        print(f"当前已选择 {selected_count} 条")
        
        # 如果已选数量超过300条，直接退出循环
        if selected_count >= max_results:
            print(f"已达到最大选择数量 {max_results} 条，停止翻页")
            break
            
        # 如果还有下一页且未选择完所有结果
        if selected_count < total_results:
            next_page = page.locator("//a[@id='PageNext']")
            if next_page.count() > 0 and "disabled" not in next_page.get_attribute("class"):
                next_page.click()
                current_page += 1
                print(f"翻到第 {current_page} 页")
                time.sleep(3)  # 等待页面加载
            else:
                break
    
    # 点击导出按钮
    page.evaluate('''() => {
        const exportLinks = document.querySelectorAll('a');
        for (const link of exportLinks) {
            if (link.textContent.trim() === '导出与分析') {
                link.click();
                break;
            }
        }
    }''')
    time.sleep(1)
    
    # 点击导出文献
    page.evaluate('''() => {
        const exportLinks = document.querySelectorAll('a');
        for (const link of exportLinks) {
            if (link.textContent.trim() === '导出文献') {
                link.click();
                break;
            }
        }
    }''')
    time.sleep(1)
    
    # 点击自定义
    page.evaluate('''() => {
        const exportLinks = document.querySelectorAll('a[exporttype="selfDefine"]');
        if (exportLinks.length > 0) {
            exportLinks[0].click();
        }
    }''')
    time.sleep(2)
    
    # 等待新页面加载并切换到新页面
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with page.expect_popup() as popup_info:
                # 等待新页面打开
                time.sleep(3)  # 给更多时间让弹窗准备打开
            
            # 获取新页面并等待加载完成
            new_page = popup_info.value
            new_page.wait_for_load_state('networkidle')
            
            # 在新页面中等待并点击全选按钮
            new_page.wait_for_selector('.check-labels', timeout=15000)
            time.sleep(2)
            break  # 如果成功则跳出循环
            
        except Exception as e:
            retry_count += 1
            print(f"等待元素出现超时，正在进行第 {retry_count} 次重试...")
            if retry_count >= max_retries:
                raise Exception("重试次数已达上限，操作失败") from e
            time.sleep(2)  # 重试前等待
    new_page.evaluate('''() => {
        const allButton = document.querySelector('.check-labels .row-btns a');
        if (allButton && allButton.textContent.trim() === '全选') {
            allButton.click();
        }
    }''')
    time.sleep(2)
    
    # 获取新页面
    new_page.wait_for_load_state()
    
    # 在新页面中点击导出xls
    new_page.evaluate('''() => {
        const xlsButton = document.querySelector('#litoexcel');
        if (xlsButton) {
            xlsButton.click();
        }
    }''')
    time.sleep(2)  # 等待下载开始
    
    # 监听下载事件
    with new_page.expect_download() as download_info:
        # 点击导出xls
        new_page.evaluate('''() => {
            const xlsButton = document.querySelector('#litoexcel');
            if (xlsButton) {
                xlsButton.click();
            }
        }''')
    
    # 等待下载完成
    download = download_info.value
    print("正在下载文件...")
    
    # 设置下载路径为data/selected_topic文件夹
    data_folder = os.path.join(os.path.dirname(__file__), 'data')
    topic_folder = os.path.join(data_folder, selected_topic.replace(' ', '_'))
    os.makedirs(topic_folder, exist_ok=True)  # 确保主题文件夹存在
    
    # 保存文件
    download.save_as(os.path.join(
        topic_folder,
        f'CNKI_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xls'
    ))
    print(f"文件下载完成！保存在: {topic_folder}")
    
    return selected_count

def cnki_spider(selected_topic, start_year=None, end_year=None, check_core=False):
    keyword = selected_topic
    
    # Initialize browser
    page, browser, context, playwright = webserver()
    
    try:
        # 打开页面并搜索
        res_unm = open_page(page, keyword, start_year, end_year, check_core)
        if res_unm == 0:
            print("没有找到相关结果")
            return
            
        # 选择所有结果并导出
        selected_count = select_all_and_export(page, res_unm, selected_topic)
        print(f"成功选择 {selected_count} 条结果并导出")
        
        # 记录日志到主题文件夹下
        data_folder = os.path.join(os.path.dirname(__file__), 'data')
        topic_folder = os.path.join(data_folder, selected_topic.replace(' ', '_'))
        os.makedirs(topic_folder, exist_ok=True)
        log_crawl_info(selected_topic, start_year, end_year, res_unm, selected_count, topic_folder)
        
    finally:
        # 关闭浏览器
        context.close()
        browser.close()
        playwright.stop()


if __name__ == "__main__":
    # Example usage
    # selected_topic = "大模型 图书馆"
    # start_year = "2025"
    # end_year = "2025"
    # cnki_spider(selected_topic, start_year, end_year)
    
    cnki_spider("图书馆 AIGC",check_core=False)