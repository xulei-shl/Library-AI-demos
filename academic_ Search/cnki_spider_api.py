import time
import concurrent.futures
from playwright.async_api import async_playwright
import pyperclip
from datetime import datetime
import pandas as pd
import os
from unit.log_crawl import log_crawl_info
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import threading
import uvicorn
import asyncio

# 使用导出与分析的逻辑，勾选关键词和摘要，复制到剪贴板

# 定义请求模型
class SearchRequest(BaseModel):
    topic: str
    start_year: str = None
    end_year: str = None
    check_core: bool = False

class CNKISpider:
    def __init__(self):
        self.page = None
        self.browser = None
        self.context = None
        self.playwright = None
        
    async def webserver(self):
        p = await async_playwright().start()
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        
        # 创建新的上下文，只设置 accept_downloads
        context = await browser.new_context(
            accept_downloads=True
        )
        
        # Disable images for faster loading
        await context.route("**/*.{png,jpg,jpeg}", lambda route: route.abort())
        
        # Create a new page
        page = await context.new_page()
        
        # Set page load strategy to none
        page.set_default_timeout(60000)  # 60 seconds timeout
        
        self.page = page
        self.browser = browser
        self.context = context
        self.playwright = p
        
        return page, browser, context, p

    async def open_page(self, keyword, start_year=None, end_year=None, check_core=False):
        # 将所有的同步操作改为异步
        await self.page.goto("https://kns.cnki.net/kns8s/AdvSearch?classid=YSTT4HG0", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        keyword_input = self.page.locator('''//*[@id="gradetxt"]/dd[1]/div[2]/input''')
        await keyword_input.fill(keyword)
        
        # 勾选同义词扩展选项
        synonym_checkbox = self.page.locator('''//input[@data-id="TY"]''')
        await synonym_checkbox.check()

        # 处理年份选择
        if start_year or end_year:
            # 点击展开年份选择框
            await self.page.click('.tit-dropdown-box .sort-default')
            await asyncio.sleep(1)
            
            if start_year:
                start_year_input = self.page.locator("input[placeholder='起始年']")
                await start_year_input.fill(start_year)
            if end_year:
                end_year_input = self.page.locator("input[placeholder='结束年']")
                await end_year_input.fill(end_year)
        else:
            # 如果未提供年份，选择"最近一年"选项
            await self.page.evaluate('''() => {
                const dropdownBox = document.querySelector('.tit-dropdown-box');
                if (dropdownBox) {
                    // 点击展开下拉框
                    const defaultSort = dropdownBox.querySelector('.sort-default');
                    defaultSort && defaultSort.click();
                    
                    // 等待下拉列表显示
                    setTimeout(() => {
                        const yearLink = Array.from(document.querySelectorAll('.sort-list li a')).find(
                            link => link.textContent.trim() === '最近一年'
                        );
                        yearLink && yearLink.click();
                    }, 100);
                }
            }''')
            await asyncio.sleep(1)  # 等待选择生效

        # 处理核心期刊选择
        if check_core:
            # 点击展开核心期刊选择框
            await self.page.click('.tit-dropdown-box .sort-default')
            await asyncio.sleep(1)
            
            # 勾选所有核心期刊选项
            core_journals = [
                '//label/input[@key="SI"]',  # SCI
                '//label/input[@key="EI"]',  # EI
                '//label/input[@key="CSD"]', # CSCD
                '//label/input[@key="AMI"]', # AMI
                '//label/input[@key="HX"]',  # 北大核心
                '//label/input[@key="CSI"]'  # CSSCI
            ]
            for locator in core_journals:
                checkbox = self.page.locator(locator)
                await checkbox.check()
                await asyncio.sleep(0.5)

        # 点击搜索按钮
        search_button = self.page.locator('''//input[@class="btn-search"]''')
        await search_button.click()
        print("正在搜索，请稍后...")
        
        # 等待搜索结果加载
        await self.page.wait_for_selector('//*[@id="countPageDiv"]/span[1]/em', timeout=10000)
        
        # 设置每页显示50条
        await self.page.click('#perPageDiv .sort-default')
        await self.page.click('ul.sort-list li[data-val="50"] a')
        await asyncio.sleep(2)  # 等待页面刷新
        
        # 获取总结果数
        try:
            res_unm_element = self.page.locator('//*[@id="countPageDiv"]/span[1]/em')
            res_unm = await res_unm_element.inner_text()
            res_unm = int(res_unm.replace(",", ""))
            page_unm = int(res_unm / 50) + 1
            print(f"共找到 {res_unm} 条结果，{page_unm} 页。")
            return res_unm
        except Exception:
            return 0

    async def select_all_and_export(self, total_results, selected_topic):
        """选择所有结果并导出"""
        selected_count = 0
        clipboard_content = ""  # 添加默认值
        
        try:
            current_page = 1
            max_results = 100  # 设置最大选择数量为100条
            
            while selected_count < total_results:
                # 等待页面加载完成
                await self.page.wait_for_selector('#selectCheckAll1', timeout=10000)
                await asyncio.sleep(2)
                
                # 点击全选
                await self.page.click('#selectCheckAll1')
                await asyncio.sleep(1)
                
                # 获取当前选中数量
                select_count_text = await self.page.locator('#selectCount').inner_text()
                selected_count = int(select_count_text)
                print(f"当前已选择 {selected_count} 条")
                
                # 如果已选数量超过100条，直接退出循环
                if selected_count >= max_results:
                    print(f"已达到最大选择数量 {max_results} 条，停止翻页")
                    break
                    
                # 如果还有下一页且未选择完所有结果
                if selected_count < total_results:
                    next_page = self.page.locator("//a[@id='PageNext']")
                    if await next_page.count() > 0 and "disabled" not in await next_page.get_attribute("class"):
                        await next_page.click()
                        current_page += 1
                        print(f"翻到第 {current_page} 页")
                        await asyncio.sleep(3)  # 等待页面加载
                    else:
                        break
            
            # 点击导出按钮
            await self.page.evaluate('''() => {
                const exportLinks = document.querySelectorAll('a');
                for (const link of exportLinks) {
                    if (link.textContent.trim() === '导出文献') {
                        link.click();
                        break;
                    }
                }
            }''')
            await asyncio.sleep(1)
            
            # 点击导出文献
            await self.page.evaluate('''() => {
                const exportLinks = document.querySelectorAll('a');
                for (const link of exportLinks) {
                    if (link.textContent.trim() === '导出文献') {
                        link.click();
                        break;
                    }
                }
            }''')
            await asyncio.sleep(1)
            
            # 点击自定义
            await self.page.evaluate('''() => {
                const exportLinks = document.querySelectorAll('a[exporttype="selfDefine"]');
                if (exportLinks.length > 0) {
                    exportLinks[0].click();
                }
            }''')
            await asyncio.sleep(2)
            
            # 等待新页面加载并切换到新页面
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    await asyncio.sleep(2)
                    all_pages = self.context.pages
                    if len(all_pages) > 1:
                        new_page = all_pages[-1]
                        await new_page.wait_for_load_state('domcontentloaded')
                        # 等待新页面加载并确保勾选框可见
                        await new_page.wait_for_selector('label[title="Keyword-关键词"] input', timeout=5000)
                        await new_page.wait_for_selector('label[title="Summary-摘要"] input', timeout=5000)
                        
                        # 使用click而不是evaluate来勾选
                        await new_page.click('label[title="Keyword-关键词"] input')
                        await new_page.click('label[title="Summary-摘要"] input')
                        await asyncio.sleep(1)  # 等待勾选生效
                        
                        # 确认勾选状态
                        keyword_checked = await new_page.evaluate('''() => {
                            const keywordCheckbox = document.querySelector('label[title="Keyword-关键词"] input');
                            return keywordCheckbox && keywordCheckbox.checked;
                        }''')
                        
                        summary_checked = await new_page.evaluate('''() => {
                            const summaryCheckbox = document.querySelector('label[title="Summary-摘要"] input');
                            return summaryCheckbox && summaryCheckbox.checked;
                        }''')
                        
                        if not (keyword_checked and summary_checked):
                            print("重试勾选操作...")
                            await new_page.click('label[title="Keyword-关键词"] input')
                            await new_page.click('label[title="Summary-摘要"] input')
                            await asyncio.sleep(1)
                        
                        # 点击导出按钮并等待下载完成
                        async with new_page.expect_download() as download_info:
                            await new_page.click('#litotxt')
                            await asyncio.sleep(2)
                        
                        download = await download_info.value
                        print("正在下载文件...")
                        
                        # 等待下载完成并获取文件路径
                        path = await download.path()
                        print(f"文件已下载到: {path}")
                        
                        # 读取文件内容并复制到剪贴板
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            pyperclip.copy(content)
                        
                        print("已将文件内容复制到剪贴板")
                        return selected_count, content
                        
                except Exception as e:
                    print(f"尝试处理新页面时出错: {str(e)}")
                    retry_count += 1
                    await asyncio.sleep(2)
                    
            print("处理新页面失败")
            return selected_count, clipboard_content
            
        except Exception as e:
            print(f"导出过程中出错: {str(e)}")
            return selected_count, clipboard_content

    async def cnki_spider(self, selected_topic, start_year=None, end_year=None, check_core=False):
        keyword = selected_topic
        result = {"status": "success", "message": "", "data": {}}
        
        try:
            # 初始化浏览器
            await self.webserver()
            
            # 打开页面并搜索
            res_unm = await self.open_page(keyword, start_year, end_year, check_core)
            if res_unm == 0:
                result["status"] = "error"
                result["message"] = "没有找到相关结果"
                return result
                
            # 选择所有结果并导出
            selected_count, clipboard_content = await self.select_all_and_export(res_unm, selected_topic)
            print(f"成功选择 {selected_count} 条结果并导出")
            
            # 记录日志到主题文件夹下
            data_folder = os.path.join(os.path.dirname(__file__), 'data')
            topic_folder = os.path.join(data_folder, selected_topic.replace(' ', '_'))
            os.makedirs(topic_folder, exist_ok=True)
            log_crawl_info(selected_topic, start_year, end_year, res_unm, selected_count, topic_folder)
            
            result["data"] = {
                "topic": selected_topic,
                "total_results": res_unm,
                "selected_count": selected_count,
                "folder_path": topic_folder,
                "content": clipboard_content  # 添加剪贴板内容
            }
            result["message"] = f"成功选择 {selected_count} 条结果并复制"
            
            return result
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"爬取过程中出错: {str(e)}"
            return result
            
        finally:
            # 关闭浏览器
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()

# 创建FastAPI应用
app = FastAPI(title="CNKI爬虫API", description="知网文献爬取服务")
spider_instance = None
spider_lock = asyncio.Lock()  # 修改为asyncio.Lock

# FastAPI路由部分
@app.post("/api/cnki/search", response_model=dict)
async def search_cnki(request_data: SearchRequest):
    global spider_instance
    
    if not request_data.topic:
        raise HTTPException(status_code=400, detail="请提供搜索主题")
    
    async with spider_lock:  # 直接使用async with
        if spider_instance is None:
            spider_instance = CNKISpider()
        
        try:
            result = await spider_instance.cnki_spider(
                request_data.topic, 
                request_data.start_year, 
                request_data.end_year, 
                request_data.check_core
            )
            return result
        finally:
            # 重置spider_instance
            spider_instance = None

@app.get("/api/status")
async def get_status():
    return {"status": "running"}

def start_server(host='0.0.0.0', port=5000):
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    # 启动服务器
    start_server()