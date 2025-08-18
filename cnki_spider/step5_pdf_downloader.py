import os
import time
import random
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from datetime import datetime
import re

class PDFDownloader:
    def __init__(self, download_dir="pdfs", headless=False, min_delay=3, max_delay=8):
        """
        初始化PDF下载器
        
        Args:
            download_dir: PDF下载目录
            headless: 是否无头模式运行（False表示显示浏览器窗口）
            min_delay: 最小等待时间（秒）
            max_delay: 最大等待时间（秒）
        """
        self.download_dir = os.path.abspath(download_dir)
        self.headless = headless
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.browser = None
        self.page = None
        self.playwright = None
        self.failed_downloads = []
        self.is_downloading = True  # 添加下载状态标志
        self.should_stop = None  # 停止检查函数
        
        # 确保下载目录存在
        os.makedirs(self.download_dir, exist_ok=True)
        
        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def random_delay(self):
        """
        随机等待，模拟人工操作习惯
        参考step2_cnki_spider.py的延迟策略，增加随机性模拟真实用户行为
        """
        # 生成随机延迟时间，模拟人类操作间隔
        delay = random.uniform(self.min_delay, self.max_delay)
        self.logger.info(f"模拟人工操作间隔，等待 {delay:.1f} 秒...")
        
        # 分段等待，便于快速响应停止信号
        total_wait = 0
        while total_wait < delay:
            # 检查是否需要停止
            if not self.is_downloading or (self.should_stop and self.should_stop()):
                self.logger.info("等待被中断")
                return False
            
            # 每次最多等待0.5秒，保持响应性
            wait_time = min(0.5, delay - total_wait)
            time.sleep(wait_time)
            total_wait += wait_time
        
        return True
    
    def setup_driver(self):
        """设置Playwright浏览器，参考step2_cnki_spider.py的webserver函数"""
        try:
            self.playwright = sync_playwright().start()
            
            # 参考step2的浏览器启动配置
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,  # 显示浏览器窗口，便于人工处理验证码
                slow_mo=2000,    # 每个操作间隔2秒，便于观察和模拟人工操作
                devtools=False    # 不打开开发者工具
            )
            
            # 创建新的上下文，参考step2的设置
            context = self.browser.new_context(
                accept_downloads=True
            )
            
            # 禁用图片加载以提高速度（参考step2逻辑）
            context.route("**/*.{png,jpg,jpeg}", lambda route: route.abort())
            
            # 创建页面
            self.page = context.new_page()
            
            # 设置页面超时，参考step2的设置
            self.page.set_default_timeout(60000)  # 60秒超时
            
            self.logger.info("Playwright浏览器启动成功")
            return True
        except Exception as e:
            self.logger.error(f"启动Playwright浏览器失败: {e}")
            return False
    
    def wait_for_download_page(self, url, max_wait_time=300):
        """
        等待下载页面加载，处理可能的验证码
        参考step2_cnki_spider.py的页面等待逻辑
        
        Args:
            url: 论文详情页URL
            max_wait_time: 最大等待时间（秒）
        
        Returns:
            bool: 是否成功进入下载页面
        """
        try:
            self.logger.info(f"正在访问: {url}")
            
            # 参考step2的页面加载策略
            self.page.goto(url, wait_until="domcontentloaded")
            time.sleep(2)  # 参考step2的等待时间
            
            # 检查并处理可能出现的弹窗（参考step2逻辑）
            try:
                time.sleep(1)
                popup = self.page.locator('.layui-layer-dialog')
                if popup.count() > 0:
                    self.logger.info("检测到弹窗，正在处理...")
                    confirm_button = self.page.locator('.layui-layer-btn0')
                    if confirm_button.count() > 0:
                        confirm_button.click()
                        self.logger.info("已点击确认按钮关闭弹窗")
                        time.sleep(1)
            except Exception as e:
                self.logger.debug(f"处理弹窗时出错: {e}")
            
            # 检查是否有验证码页面
            page_content = self.page.content()
            if "验证" in page_content or "captcha" in page_content.lower() or "安全验证" in page_content:
                self.logger.info("检测到验证码页面，请手动处理验证码...")
                self.logger.info(f"将等待最多 {max_wait_time} 秒，直到出现PDF下载按钮")
            
            # 等待PDF下载按钮出现（参考step2的元素等待策略）
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                # 检查是否需要停止
                if not self.is_downloading or (self.should_stop and self.should_stop()):
                    self.logger.info("等待下载页面被中断")
                    return False
                
                try:
                    # 更全面的PDF下载相关元素选择器
                    pdf_selectors = [
                        "text=PDF下载",
                        "text=下载PDF", 
                        "text=全文下载",
                        "text=PDF全文下载",
                        "a[href*='.pdf']",
                        "a[href*='download']",
                        ".btn-dlpdf",
                        ".download-btn",
                        "[class*='pdf-download']",
                        "[class*='download']",
                        "button:has-text('PDF')",
                        "button:has-text('下载')",
                        "#pdfDown",
                        ".icon-pdf"
                    ]
                    
                    for selector in pdf_selectors:
                        try:
                            elements = self.page.locator(selector)
                            if elements.count() > 0:
                                # 检查元素是否可见
                                first_element = elements.first
                                if first_element.is_visible():
                                    self.logger.info(f"检测到PDF下载按钮: {selector}")
                                    return True
                        except Exception as selector_error:
                            continue
                    
                    # 检查是否还在验证页面
                    current_content = self.page.content()
                    if "验证" not in current_content and "captcha" not in current_content.lower() and "安全验证" not in current_content:
                        # 可能已经通过验证，再等待一下看是否有下载按钮
                        time.sleep(3)
                        
                        # 再次检查下载按钮
                        for selector in pdf_selectors:
                            try:
                                elements = self.page.locator(selector)
                                if elements.count() > 0 and elements.first.is_visible():
                                    self.logger.info(f"验证通过后检测到PDF下载按钮: {selector}")
                                    return True
                            except:
                                continue
                    
                    time.sleep(5)  # 每5秒检查一次
                    
                except Exception as e:
                    self.logger.debug(f"检查下载页面时出错: {e}")
                    time.sleep(5)
            
            self.logger.warning(f"等待 {max_wait_time} 秒后仍未检测到PDF下载按钮")
            return False
            
        except Exception as e:
            self.logger.error(f"访问页面失败: {e}")
            return False
    
    def download_pdf(self, url, title="", is_first_download=False):
        """
        下载单个PDF文件
        
        Args:
            url: 论文详情页URL
            title: 论文标题（用于日志）
            is_first_download: 是否为第一次下载（用于处理验证码）
        
        Returns:
            tuple: (是否成功, 消息)
        """
        # 第一次下载的第一条链接直接失败的优化逻辑
        if is_first_download:
            self.logger.info(f"第一次运行的第一条链接，模拟失败: {title}")
            
            # 仍然需要访问页面和点击下载按钮来模拟真实操作
            try:
                # 等待下载页面加载
                if not self.wait_for_download_page(url):
                    self.logger.error(f"无法进入下载页面: {title}")
                    self.failed_downloads.append({"title": title, "url": url, "reason": "无法进入下载页面"})
                    return False, "无法进入下载页面"
                
                # 查找并点击下载按钮
                pdf_download_selectors = [
                    "text=PDF下载",
                    "text=下载PDF",
                    "text=全文下载", 
                    "text=PDF全文下载",
                    "a[href*='.pdf']",
                    "a[href*='download']",
                    "button:has-text('PDF下载')",
                    "button:has-text('下载PDF')",
                    "button:has-text('全文下载')",
                    "button:has-text('PDF')",
                    "button:has-text('下载')",
                    ".btn-dlpdf",
                    ".download-btn",
                    "[class*='pdf-download']",
                    "[class*='download']",
                    "#pdfDown",
                    ".icon-pdf"
                ]
                
                download_button = None
                selected_selector = None
                
                # 查找可见的下载按钮
                for selector in pdf_download_selectors:
                    try:
                        elements = self.page.locator(selector)
                        if elements.count() > 0:
                            for i in range(elements.count()):
                                element = elements.nth(i)
                                if element.is_visible():
                                    download_button = element
                                    selected_selector = selector
                                    break
                            if download_button:
                                break
                    except Exception as e:
                        continue
                
                if download_button:
                    self.logger.info(f"找到下载按钮: {selected_selector}")
                    # 滚动到按钮位置并点击
                    download_button.scroll_into_view_if_needed()
                    time.sleep(1)
                    download_button.click()
                    self.logger.info("已点击下载按钮")
                    
                    # 随机等待1-2秒后直接记录为失败
                    wait_time = random.uniform(1, 2)
                    self.logger.info(f"等待 {wait_time:.1f} 秒后记录为失败...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"未找到可见的PDF下载按钮: {title}")
                
                # 直接记录为失败
                self.failed_downloads.append({"title": title, "url": url, "reason": "第一次运行模拟失败"})
                self.logger.info(f"第一条链接已记录为失败: {title}")
                return False, "第一次运行模拟失败"
                
            except Exception as e:
                self.logger.error(f"第一次下载模拟过程中发生错误: {title}, 错误: {e}")
                self.failed_downloads.append({"title": title, "url": url, "reason": f"第一次下载模拟错误: {e}"})
                return False, f"第一次下载模拟错误: {e}"
        try:
            # 检查是否需要停止
            if not self.is_downloading or (self.should_stop and self.should_stop()):
                return False, "下载已停止"
            
            # 生成安全的文件名
            if title:
                # 清理文件名中的非法字符，保留中文字符
                import re
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', title).strip()
                # 限制文件名长度，避免路径过长
                if len(safe_title) > 100:
                    safe_title = safe_title[:100]
                filename = f"{safe_title}.pdf"
            else:
                filename = f"document_{int(time.time())}.pdf"
            
            pdf_path = os.path.join(self.download_dir, filename)
            
            # 检查文件是否已存在
            if os.path.exists(pdf_path):
                self.logger.info(f"文件已存在，跳过下载: {filename}")
                return True, "文件已存在"
            
            self.logger.info(f"开始下载: {title}")
            
            # 等待下载页面加载
            if not self.wait_for_download_page(url):
                self.logger.error(f"无法进入下载页面: {title}")
                self.failed_downloads.append({"title": title, "url": url, "reason": "无法进入下载页面"})
                return False, "无法进入下载页面"
            
            # 更全面的PDF下载按钮选择器
            pdf_download_selectors = [
                "text=PDF下载",
                "text=下载PDF",
                "text=全文下载", 
                "text=PDF全文下载",
                "a[href*='.pdf']",
                "a[href*='download']",
                "button:has-text('PDF下载')",
                "button:has-text('下载PDF')",
                "button:has-text('全文下载')",
                "button:has-text('PDF')",
                "button:has-text('下载')",
                ".btn-dlpdf",
                ".download-btn",
                "[class*='pdf-download']",
                "[class*='download']",
                "#pdfDown",
                ".icon-pdf"
            ]
            
            download_button = None
            selected_selector = None
            
            # 查找可见的下载按钮
            for selector in pdf_download_selectors:
                try:
                    elements = self.page.locator(selector)
                    if elements.count() > 0:
                        for i in range(elements.count()):
                            element = elements.nth(i)
                            if element.is_visible():
                                download_button = element
                                selected_selector = selector
                                break
                        if download_button:
                            break
                except Exception as e:
                    continue
            
            if not download_button:
                self.logger.error(f"未找到可见的PDF下载按钮: {title}")
                # 记录页面内容用于调试
                try:
                    page_text = self.page.inner_text('body')[:500]  # 获取前500个字符
                    self.logger.debug(f"页面内容片段: {page_text}")
                except:
                    pass
                self.failed_downloads.append({"title": title, "url": url, "reason": "未找到PDF下载按钮"})
                return False, "未找到PDF下载按钮"
            
            self.logger.info(f"找到下载按钮: {selected_selector}")
            
            # 尝试多种下载方式
            download_success = False
            
            # 方式1: 监听下载事件
            try:
                self.logger.info("尝试方式1: 监听下载事件")
                
                # 滚动到按钮位置
                download_button.scroll_into_view_if_needed()
                time.sleep(1)
                
                with self.page.expect_download(timeout=60000) as download_info:
                    download_button.click()
                    self.logger.info("已点击下载按钮，等待下载...")
                
                download = download_info.value
                
                # 保存下载的文件
                download.save_as(pdf_path)
                self.logger.info(f"PDF下载成功: {title}")
                download_success = True
                
            except PlaywrightTimeoutError:
                self.logger.warning("方式1超时，尝试其他方式")
                
                # 方式2: 直接点击并等待
                try:
                    self.logger.info("尝试方式2: 直接点击")
                    download_button.click()
                    
                    # 等待一段时间看是否有文件生成
                    wait_time = 0
                    max_wait = 30
                    while wait_time < max_wait:
                        if os.path.exists(pdf_path):
                            self.logger.info(f"检测到下载文件: {title}")
                            download_success = True
                            break
                        
                        # 检查下载目录中是否有新文件
                        try:
                            files = os.listdir(self.download_dir)
                            pdf_files = [f for f in files if f.endswith('.pdf') and f.startswith(safe_title[:20])]
                            if pdf_files:
                                # 找到可能的下载文件，重命名
                                downloaded_file = os.path.join(self.download_dir, pdf_files[0])
                                if os.path.exists(downloaded_file) and downloaded_file != pdf_path:
                                    os.rename(downloaded_file, pdf_path)
                                    self.logger.info(f"重命名下载文件: {pdf_files[0]} -> {filename}")
                                    download_success = True
                                    break
                        except:
                            pass
                        
                        time.sleep(2)
                        wait_time += 2
                        
                        # 检查是否需要停止
                        if not self.is_downloading or (self.should_stop and self.should_stop()):
                            return False, "下载已停止"
                    
                    if not download_success:
                        self.logger.warning("方式2未检测到下载文件")
                        
                except Exception as e:
                    self.logger.error(f"方式2失败: {e}")
            
            except Exception as e:
                self.logger.error(f"方式1失败: {e}")
            
            # 方式3: 尝试右键另存为（如果是直接PDF链接）
            if not download_success:
                try:
                    self.logger.info("尝试方式3: 检查直接PDF链接")
                    
                    # 检查是否是直接的PDF链接
                    href = download_button.get_attribute('href')
                    if href and '.pdf' in href:
                        self.logger.info(f"发现直接PDF链接: {href}")
                        
                        # 直接访问PDF链接
                        response = self.page.goto(href, timeout=60000)
                        if response and response.status == 200:
                            # 等待PDF加载
                            time.sleep(3)
                            
                            # 使用浏览器的打印功能保存PDF
                            pdf_bytes = self.page.pdf(path=pdf_path, format='A4')
                            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:  # 文件大于1KB
                                self.logger.info(f"通过PDF链接下载成功: {title}")
                                download_success = True
                            
                except Exception as e:
                    self.logger.error(f"方式3失败: {e}")
            
            if download_success:
                # 验证下载的文件
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:  # 文件大于1KB
                    self.logger.info(f"PDF下载并验证成功: {title} ({os.path.getsize(pdf_path)} bytes)")
                    return True, "下载成功"
                else:
                    self.logger.error(f"下载的文件无效或过小: {title}")
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)  # 删除无效文件
                    self.failed_downloads.append({"title": title, "url": url, "reason": "下载的文件无效"})
                    return False, "下载的文件无效"
            else:
                self.logger.error(f"所有下载方式都失败: {title}")
                self.failed_downloads.append({"title": title, "url": url, "reason": "所有下载方式都失败"})
                return False, "下载失败"
                
        except Exception as e:
            self.logger.error(f"下载PDF时发生错误: {title}, 错误: {e}")
            self.failed_downloads.append({"title": title, "url": url, "reason": f"下载错误: {e}"})
            return False, f"下载错误: {e}"
    
    def download_from_excel(self, excel_file, url_column="链接", title_column="标题"):
        """
        从Excel文件批量下载PDF
        
        Args:
            excel_file: Excel文件路径
            url_column: URL列名
            title_column: 标题列名
        
        Returns:
            dict: 下载统计信息
        """
        if not self.setup_driver():
            return {"success": 0, "failed": 0, "total": 0}
        
        try:
            # 读取Excel文件
            df = pd.read_excel(excel_file)
            total_count = len(df)
            success_count = 0
            
            self.logger.info(f"开始批量下载，共 {total_count} 个文件")
            
            for index, row in df.iterrows():
                url = row.get(url_column, "")
                title = row.get(title_column, f"文件_{index+1}")
                
                if not url:
                    self.logger.warning(f"第 {index+1} 行缺少URL，跳过")
                    self.failed_downloads.append({"title": title, "url": "", "reason": "缺少URL"})
                    continue
                
                self.logger.info(f"正在处理第 {index+1}/{total_count} 个文件")
                
                success, message = self.download_pdf(url, title)
                if success:
                    success_count += 1
                    self.logger.info(f"处理成功: {title} - {message}")
                else:
                    self.logger.error(f"处理失败: {title} - {message}")
                
                # 随机等待，模拟人工操作习惯
                if not self.random_delay():
                    self.logger.info("下载已被停止")
                    break
            
            # 保存失败列表
            if self.failed_downloads:
                failed_file = os.path.join(self.download_dir, "下载失败列表.txt")
                with open(failed_file, "w", encoding="utf-8") as f:
                    f.write("下载失败的文件列表:\n\n")
                    for item in self.failed_downloads:
                        f.write(f"标题: {item['title']}\n")
                        f.write(f"URL: {item['url']}\n")
                        f.write(f"失败原因: {item['reason']}\n")
                        f.write("-" * 50 + "\n")
                
                self.logger.info(f"失败列表已保存到: {failed_file}")
            
            return {
                "success": success_count,
                "failed": len(self.failed_downloads),
                "total": total_count
            }
            
        except Exception as e:
            self.logger.error(f"批量下载过程中发生错误: {e}")
            return {"success": 0, "failed": 0, "total": 0}
        
        finally:
            self.close_browser()
    
    def download_pdfs_batch(self, urls_titles_list):
        """
        批量下载PDF文件，支持跳过已存在文件和失败重试
        
        Args:
            urls_titles_list: [(url, title), ...] 格式的列表
        
        Returns:
            dict: 下载统计信息
        """
        if not self.setup_driver():
            self.logger.error("浏览器启动失败，无法进行批量下载")
            return {"success": 0, "failed": 0, "skipped": 0, "total": 0}
        
        try:
            total_count = len(urls_titles_list)
            success_count = 0
            skip_count = 0
            failed_count = 0
            
            self.logger.info(f"开始批量下载，共 {total_count} 个文件")
            
            # 第一轮下载
            for i, (url, title) in enumerate(urls_titles_list):
                # 检查是否需要停止
                if not self.is_downloading or (self.should_stop and self.should_stop()):
                    self.logger.info("下载已被用户停止")
                    break
                
                self.logger.info(f"正在处理第 {i+1}/{total_count} 个文件: {title}")
                
                # 验证URL
                if not url or not url.strip():
                    self.logger.warning(f"跳过空URL: {title}")
                    failed_count += 1
                    self.failed_downloads.append({"title": title, "url": url, "reason": "URL为空"})
                    continue
                
                try:
                    # 第一个文件需要处理验证码，后续文件不需要
                    is_first = (i == 0)
                    success, message = self.download_pdf(url.strip(), title, is_first_download=is_first)
                    if success:
                        if "已存在" in message:
                            skip_count += 1
                            self.logger.info(f"文件已存在，跳过: {title}")
                        else:
                            success_count += 1
                            self.logger.info(f"下载成功: {title}")
                    else:
                        failed_count += 1
                        self.logger.error(f"下载失败: {title} - {message}")
                        
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"处理文件时发生异常: {title} - {str(e)}")
                    self.failed_downloads.append({"title": title, "url": url, "reason": f"处理异常: {str(e)}"})
                
                # 每条数据之间增加随机间隔，模拟人类操作
                if i < total_count - 1:  # 最后一个文件不需要等待
                    if not self.random_delay():
                        self.logger.info("下载在等待过程中被停止")
                        break
            
            # 第一轮下载完成报告
            self.logger.info(f"批量下载完成 - 成功: {success_count}, 跳过: {skip_count}, 失败: {failed_count}")
            
            # 失败重试机制
            if self.failed_downloads and self.is_downloading:
                self.logger.info(f"开始重试失败的 {len(self.failed_downloads)} 个文件...")
                retry_list = self.failed_downloads.copy()
                self.failed_downloads.clear()  # 清空失败列表，准备重试
                
                retry_success = 0
                for i, failed_item in enumerate(retry_list):
                    # 检查是否需要停止
                    if not self.is_downloading or (self.should_stop and self.should_stop()):
                        self.logger.info("重试过程被用户停止")
                        # 将未重试的项目重新加入失败列表
                        self.failed_downloads.extend(retry_list[i:])
                        break
                    
                    url = failed_item["url"]
                    title = failed_item["title"]
                    
                    if not url or not url.strip():
                        self.failed_downloads.append(failed_item)
                        continue
                    
                    self.logger.info(f"重试第 {i+1}/{len(retry_list)} 个文件: {title}")
                    
                    try:
                        success, message = self.download_pdf(url.strip(), title)
                        if success:
                            if "已存在" in message:
                                skip_count += 1
                                self.logger.info(f"重试成功(文件已存在): {title}")
                            else:
                                success_count += 1
                                retry_success += 1
                                self.logger.info(f"重试成功: {title}")
                        else:
                            self.logger.error(f"重试仍然失败: {title} - {message}")
                            # 重试失败，更新失败原因
                            self.failed_downloads.append({"title": title, "url": url, "reason": f"重试后仍失败: {message}"})
                            
                    except Exception as e:
                        self.logger.error(f"重试时发生异常: {title} - {str(e)}")
                        self.failed_downloads.append({"title": title, "url": url, "reason": f"重试异常: {str(e)}"})
                    
                    # 重试间隔
                    if i < len(retry_list) - 1:
                        if not self.random_delay():
                            self.logger.info("重试在等待过程中被停止")
                            # 将未重试的项目重新加入失败列表
                            self.failed_downloads.extend(retry_list[i+1:])
                            break
                
                # 更新失败计数
                failed_count = len(self.failed_downloads)
                self.logger.info(f"重试完成 - 重试成功: {retry_success}, 最终失败: {failed_count}")
            
            # 保存失败列表
            if self.failed_downloads:
                try:
                    failed_file = os.path.join(self.download_dir, f"下载失败列表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                    with open(failed_file, "w", encoding="utf-8") as f:
                        f.write(f"下载失败的文件列表 (生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
                        f.write(f"总计: {len(self.failed_downloads)} 个失败项目\n\n")
                        f.write("=" * 60 + "\n\n")
                        
                        for i, item in enumerate(self.failed_downloads, 1):
                            f.write(f"{i}. 标题: {item['title']}\n")
                            f.write(f"   URL: {item['url']}\n")
                            f.write(f"   失败原因: {item['reason']}\n")
                            f.write("-" * 50 + "\n")
                    
                    self.logger.info(f"失败列表已保存到: {failed_file}")
                except Exception as e:
                    self.logger.error(f"保存失败列表时出错: {e}")
            
            return {
                "success": success_count,
                "failed": failed_count,
                "skipped": skip_count,
                "total": total_count
            }
            
        except Exception as e:
            self.logger.error(f"批量下载过程中发生严重错误: {e}")
            return {
                "success": 0,
                "failed": len(urls_titles_list),
                "skipped": 0,
                "total": len(urls_titles_list)
            }
            
        finally:
            try:
                self.close_browser()
            except Exception as e:
                self.logger.error(f"关闭浏览器时出错: {e}")
    
    def close_browser(self):
        """关闭浏览器"""
        try:
            # 设置下载状态为False
            self.is_downloading = False
            
            # 关闭页面
            if hasattr(self, 'page') and self.page:
                try:
                    self.page.close()
                    self.logger.info("页面已关闭")
                except Exception as e:
                    self.logger.debug(f"关闭页面时出错: {e}")
                finally:
                    self.page = None
            
            # 关闭浏览器
            if hasattr(self, 'browser') and self.browser:
                try:
                    self.browser.close()
                    self.logger.info("浏览器已关闭")
                except Exception as e:
                    self.logger.debug(f"关闭浏览器时出错: {e}")
                finally:
                    self.browser = None
            
            # 停止Playwright
            if hasattr(self, 'playwright') and self.playwright:
                try:
                    self.playwright.stop()
                    self.logger.info("Playwright已停止")
                except Exception as e:
                    self.logger.debug(f"停止Playwright时出错: {e}")
                finally:
                    self.playwright = None
                    
        except Exception as e:
            self.logger.error(f"关闭浏览器过程中发生错误: {e}")


class PDFDownloaderTab:
    def __init__(self, parent_frame):
        """
        PDF下载器GUI组件
        
        Args:
            parent_frame: 父级框架
        """
        self.parent_frame = parent_frame
        self.selected_file = None
        self.is_downloading = False
        self.download_thread = None
        self.downloader = None
        
        # GUI变量
        self.file_label = None
        self.threshold_var = tk.DoubleVar(value=7.0)
        self.use_threshold_var = tk.BooleanVar(value=False)
        self.progress_var = tk.StringVar(value="等待开始...")
        self.progress_bar = None
        self.log_text = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主容器
        main_frame = ttk.Frame(self.parent_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 标题
        title_label = ttk.Label(main_frame, text="PDF文献下载器", 
                               font=('Microsoft YaHei UI', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding=10)
        file_frame.pack(fill='x', pady=(0, 10))
        
        file_row = ttk.Frame(file_frame)
        file_row.pack(fill='x')
        
        self.file_label = ttk.Label(file_row, text="未选择文件", foreground='gray')
        self.file_label.pack(side='left', fill='x', expand=True)
        
        ttk.Button(file_row, text="选择Excel文件", 
                  command=self.select_file).pack(side='right')
        
        # 筛选设置
        filter_frame = ttk.LabelFrame(main_frame, text="筛选设置", padding=10)
        filter_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Checkbutton(filter_frame, text="启用评分筛选", 
                       variable=self.use_threshold_var).pack(anchor='w')
        
        threshold_frame = ttk.Frame(filter_frame)
        threshold_frame.pack(fill='x', pady=(5, 0))
        
        ttk.Label(threshold_frame, text="最低评分:").pack(side='left')
        
        threshold_scale = ttk.Scale(threshold_frame, from_=0, to=10, 
                                   variable=self.threshold_var, orient='horizontal')
        threshold_scale.pack(side='left', fill='x', expand=True, padx=(10, 10))
        
        self.threshold_label = ttk.Label(threshold_frame, text="7.0")
        self.threshold_label.pack(side='right')
        
        threshold_scale.configure(command=self.update_threshold_label)
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        self.start_button = ttk.Button(button_frame, text="开始下载", 
                                      command=self.start_download)
        self.start_button.pack(side='left', padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="停止下载", 
                                     command=self.stop_download, state='disabled')
        self.stop_button.pack(side='left')
        
        # 进度显示
        progress_frame = ttk.LabelFrame(main_frame, text="下载进度", padding=10)
        progress_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(anchor='w')
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill='x', pady=(5, 0))
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="下载日志", padding=10)
        log_frame.pack(fill='both', expand=True)
        
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_container, height=10, wrap='word')
        log_scrollbar = ttk.Scrollbar(log_container, orient='vertical', 
                                     command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # 初始日志
        self.log_message("PDF下载器已就绪")
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        def update_log():
            self.log_text.insert(tk.END, formatted_message)
            self.log_text.see(tk.END)
            self.parent_frame.update()
        
        if threading.current_thread() == threading.main_thread():
            update_log()
        else:
            self.parent_frame.after(0, update_log)
    
    def select_file(self):
        """选择Excel文件"""
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.selected_file = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=filename, foreground='black')
            self.log_message(f"已选择文件: {filename}")
            
            # 检查文件内容
            try:
                df = pd.read_excel(file_path)
                self.log_message(f"文件包含 {len(df)} 条记录")
                
                # 检查列名
                columns = df.columns.tolist()
                self.log_message(f"列名: {', '.join(columns)}")
                
            except Exception as e:
                self.log_message(f"读取文件出错: {str(e)}")
    
    def update_threshold_label(self, value):
        """更新阈值标签"""
        self.threshold_label.config(text=f"{float(value):.1f}")
    
    def start_download(self):
        """开始下载"""
        if not self.selected_file:
            messagebox.showerror("错误", "请先选择Excel文件")
            return
        
        if self.is_downloading:
            messagebox.showwarning("警告", "下载正在进行中")
            return
        
        self.is_downloading = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress_bar.start()
        self.progress_var.set("正在准备下载...")
        
        # 在新线程中执行下载
        self.download_thread = threading.Thread(target=self._download_worker)
        self.download_thread.start()
    
    def _download_worker(self):
        """下载工作线程"""
        try:
            # 读取Excel文件
            df = pd.read_excel(self.selected_file)
            self.log_message(f"读取到 {len(df)} 条记录")
            
            # 初始化跳过计数
            self.skipped_no_score_count = 0
            
            # 应用筛选
            if self.use_threshold_var.get():
                threshold = self.threshold_var.get()
                # 查找"相关性评分"列
                score_col = None
                for col in df.columns:
                    if col == "相关性评分":
                        score_col = col
                        break
                
                if score_col:
                    # 统计空值情况
                    original_count = len(df)
                    df[score_col] = pd.to_numeric(df[score_col], errors='coerce')
                    
                    # 分别统计空值和有效值
                    null_count = df[score_col].isnull().sum()
                    self.skipped_no_score_count = null_count
                    
                    # 跳过空值行，只保留有评分且满足阈值的行
                    df = df.dropna(subset=[score_col])  # 移除空值行
                    df = df[df[score_col] >= threshold]  # 应用阈值筛选
                    
                    # 构建筛选结果消息
                    filter_msg = f"阈值筛选: {original_count} -> {len(df)} 条记录"
                    if null_count > 0:
                        filter_msg += f"，其中{null_count}条没有评分"
                    self.log_message(filter_msg)
                else:
                    self.log_message("未找到'相关性评分'列，跳过筛选")
            
            if len(df) == 0:
                self.log_message("没有记录需要下载")
                return
            
            # 批量下载
            self.batch_download_pdfs(df, "pdfs")
            
        except Exception as e:
            self.log_message(f"下载过程出错: {str(e)}")
            messagebox.showerror("错误", f"下载失败: {str(e)}")
        
        finally:
            self.is_downloading = False
            self.start_button.config(state='disabled')
            self.stop_button.config(state='disabled')
            self.progress_bar.stop()
            self.progress_var.set("下载完成")
    
    def batch_download_pdfs(self, df, output_folder):
        """批量下载PDF文件"""
        # 创建下载器实例，启用随机延迟
        self.downloader = PDFDownloader(download_dir=output_folder, headless=False, min_delay=3, max_delay=8)
        
        # 设置停止检查函数
        def should_stop():
            return not self.is_downloading
        self.downloader.should_stop = should_stop
        
        # 重定向日志到GUI
        original_log = self.downloader.logger.info
        def gui_log(message):
            if self.is_downloading:  # 只有在下载状态时才记录日志
                self.log_message(message)
        self.downloader.logger.info = gui_log
        
        # 查找URL和标题列
        url_columns = [col for col in df.columns if 'URL' in col or '网址' in col or '链接' in col]
        title_columns = [col for col in df.columns if '标题' in col or 'title' in col.lower()]
        
        if not url_columns:
            self.log_message("错误: 未找到URL列")
            return
        
        url_col = url_columns[0]
        title_col = title_columns[0] if title_columns else None
        
        self.log_message(f"使用URL列: {url_col}")
        if title_col:
            self.log_message(f"使用标题列: {title_col}")
        
        # 准备下载列表
        download_list = []
        for index, row in df.iterrows():
            url = row.get(url_col, "")
            title = row.get(title_col, f"文档_{index+1}") if title_col else f"文档_{index+1}"
            
            if url:
                download_list.append((url, title))
        
        self.log_message(f"准备下载 {len(download_list)} 个文件")
        
        # 同步下载状态
        self.downloader.is_downloading = self.is_downloading
        
        # 执行下载
        result = self.downloader.download_pdfs_batch(download_list)
        
        # 显示结果
        if self.is_downloading:  # 只有在正常完成时才显示结果
            self.log_message(f"下载完成: 成功 {result['success']}, 失败 {result['failed']}, 跳过 {result['skipped']}")
            
            # 显示无评分统计（如果启用了评分筛选）
            if hasattr(self, 'skipped_no_score_count') and self.skipped_no_score_count > 0:
                self.log_message(f"无评分跳过统计: {self.skipped_no_score_count} 条记录因缺少相关性评分被跳过")
        else:
            self.log_message("下载已停止")
            # 即使停止也显示无评分统计
            if hasattr(self, 'skipped_no_score_count') and self.skipped_no_score_count > 0:
                self.log_message(f"无评分跳过统计: {self.skipped_no_score_count} 条记录因缺少相关性评分被跳过")
    
    def download_single_pdf(self, row, output_folder):
        """下载单个PDF文件 - 供GUI调用"""
        if not self.downloader:
            self.downloader = PDFDownloader(download_dir=output_folder, headless=False)
            
            # 设置停止检查函数
            def should_stop():
                return not self.is_downloading
            self.downloader.should_stop = should_stop
            
            # 重定向日志到GUI
            def gui_log(message):
                if self.is_downloading:
                    self.log_message(message)
            self.downloader.logger.info = gui_log
        
        # 查找URL和标题列
        url_columns = [col for col in row.index if 'URL' in col or '网址' in col or '链接' in col]
        title_columns = [col for col in row.index if '标题' in col or 'title' in col.lower()]
        
        if not url_columns:
            self.log_message("错误: 未找到URL列")
            return False, "未找到URL列"
        
        url_col = url_columns[0]
        title_col = title_columns[0] if title_columns else None
        
        url = row.get(url_col, "")
        title = row.get(title_col, "未知标题") if title_col else "未知标题"
        
        if not url:
            return False, "URL为空"
        
        # 同步下载状态
        self.downloader.is_downloading = self.is_downloading
        
        # 下载PDF
        return self.downloader.download_pdf(url, title)
    
    def stop_download(self):
        """停止下载"""
        if self.is_downloading:
            self.is_downloading = False
            self.log_message("正在停止下载...")
            
            # 停止下载器
            if self.downloader:
                self.downloader.is_downloading = False
                try:
                    self.downloader.close_browser()
                    self.log_message("浏览器已关闭")
                except Exception as e:
                    self.log_message(f"关闭浏览器时出错: {str(e)}")
            
            # 更新UI状态
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.progress_bar.stop()
            self.progress_var.set("下载已停止")
            
            # 等待下载线程结束
            if self.download_thread and self.download_thread.is_alive():
                self.log_message("等待下载线程结束...")
                threading.Thread(target=self._wait_for_thread_stop).start()
        else:
            self.log_message("当前没有正在进行的下载任务")
    
    def _wait_for_thread_stop(self):
        """等待下载线程停止"""
        try:
            if self.download_thread:
                self.download_thread.join(timeout=5)  # 最多等待5秒
                if self.download_thread.is_alive():
                    self.log_message("下载线程未能及时停止")
                else:
                    self.log_message("下载线程已停止")
        except Exception as e:
            self.log_message(f"等待线程停止时出错: {str(e)}")
    
    def close_browser(self):
        """关闭浏览器"""
        if self.downloader:
            self.downloader.close_browser()


def main():
    """主函数，用于测试"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CNKI PDF下载器")
    parser.add_argument("--excel", required=True, help="Excel文件路径")
    parser.add_argument("--download_dir", default="pdfs", help="下载目录")
    parser.add_argument("--headless", action="store_true", help="无头模式运行")
    
    args = parser.parse_args()
    
    downloader = PDFDownloader(download_dir=args.download_dir, headless=args.headless)
    result = downloader.download_from_excel(args.excel)
    
    print(f"\n下载完成!")
    print(f"总计: {result['total']} 个文件")
    print(f"成功: {result['success']} 个文件")
    print(f"失败: {result['failed']} 个文件")


if __name__ == "__main__":
    main()