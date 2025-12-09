"""
WorldCat爬虫模块 (简化登录版)
独立的WorldCat馆藏信息爬虫，采用简化的手动登录流程
- 简化了登录检测逻辑，减少自动化检测失败
- 缩短了超时时间，避免长时间等待
- 提供更清晰的用户交互界面
- 支持用户手动登录后直接开始爬取
"""
import time
import random
import logging
import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from playwright.sync_api import sync_playwright
import pandas as pd
from pathlib import Path


@dataclass
class LibraryInfo:
    """图书馆信息数据结构"""
    name: str          # 图书馆名称
    location: str      # 地理位置 (CN, US,CA, HK等)
    code: str          # 图书馆代码
    local_holdings: str = ""  # 当地馆藏信息
    url: str = ""      # 图书馆链接


@dataclass
class WorldCatResult:
    """WorldCat爬取结果数据结构"""
    success: bool           # 是否成功
    search_term: str        # 搜索词
    libraries: List[str]    # 海外图书馆名称列表（去重后的非CN地区）
    libraries_count: int    # 海外图书馆数量
    all_libraries: List[LibraryInfo]  # 所有图书馆信息
    error_message: str = "" # 错误信息
    search_url: str = ""    # 搜索页面URL
    detail_url: str = ""    # 详情页面URL


class WorldCatScraper:
    """WorldCat爬虫类"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化WorldCat爬虫
        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # 配置参数
        self.headless = self.config.get('headless', False)
        self.timeout = self.config.get('timeout', 15000)  # 减少到15秒
        self.page_load_timeout = self.config.get('page_load_timeout', 10000)  # 页面加载超时10秒
        self.delay_range = self.config.get('delay_range', [2, 5])
        self.max_retries = self.config.get('max_retries', 3)

        # 浏览器实例
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # 基础URL
        self.base_url = "https://z.library.sh.cn/next/resource/databases/search"
        self.worldcat_url_pattern = "https://firstsearch.oclc.org/fsip?dbname=WorldCat"

        # Cookie和状态保存
        self.cookie_file = "worldcat_cookies.json"
        self.state_file = "worldcat_state.json"

    def start_browser(self) -> bool:
        """
        启动浏览器
        Returns:
            是否成功启动
        """
        try:
            self.playwright = sync_playwright().start()

            # 增强浏览器启动参数，支持新tab和更好的兼容性
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-default-apps',
                '--disable-popup-blocking',  # 允许弹出窗口和新tab
                '--disable-extensions',  # 禁用扩展避免冲突
                '--disable-plugins',
                '--disable-images',  # 可选：禁用图片加快速度
                # '--disable-javascript',  # 注意：如果需要JS交互，不要禁用 - 已注释，保持JS启用
                '--enable-automation',  # 启用自动化模式
                '--disable-infobars'
            ]

            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )

            # 创建浏览器上下文，配置更宽松的权限
            self.context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800},
                ignore_https_errors=True,  # 忽略HTTPS错误
                accept_downloads=True,  # 允许下载
                java_script_enabled=True,  # 启用JavaScript
                bypass_csp=True,  # 绕过内容安全策略
                extra_http_headers={
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                }
            )

            # 监听新页面事件，用于处理新tab
            self.context.on('page', self.handle_new_page)

            self.page = self.context.new_page()
            self.page.set_default_timeout(self.timeout)

            # 设置页面事件监听
            self.page.on('popup', self.handle_popup)

            self.logger.info("浏览器启动成功")
            return True

        except Exception as e:
            self.logger.error(f"启动浏览器失败: {str(e)}")
            return False

    def handle_new_page(self, page):
        """
        处理新页面（新tab）事件
        Args:
            page: 新页面对象
        """
        try:
            self.logger.info(f"检测到新页面打开: {page.url}")
            # 可以在这里设置新页面的默认行为
            page.set_default_timeout(self.timeout)

            # 监听新页面的关闭事件
            page.on('close', lambda: self.logger.info(f"页面已关闭: {page.url}"))

        except Exception as e:
            self.logger.warning(f"处理新页面事件时出错: {str(e)}")

    def handle_popup(self, popup):
        """
        处理弹窗事件
        Args:
            popup: 弹窗页面对象
        """
        try:
            self.logger.info(f"检测到弹窗打开: {popup.url}")
            # 设置弹窗的超时时间
            popup.set_default_timeout(self.timeout)

        except Exception as e:
            self.logger.warning(f"处理弹窗事件时出错: {str(e)}")

    def create_new_tab(self, url: str = None) -> bool:
        """
        创建新的标签页
        Args:
            url: 要打开的URL，如果为None则创建空白页面
        Returns:
            是否成功创建
        """
        try:
            if not self.context:
                self.logger.error("浏览器上下文不存在")
                return False

            new_page = self.context.new_page()
            new_page.set_default_timeout(self.timeout)

            if url:
                new_page.goto(url, timeout=self.page_load_timeout)
                self.logger.info(f"在新标签页中打开: {url}")

            # 可选：切换到新标签页
            # new_page.bring_to_front()

            return True

        except Exception as e:
            self.logger.error(f"创建新标签页失败: {str(e)}")
            return False

    def switch_to_tab_by_url(self, url_pattern: str) -> bool:
        """
        根据URL模式切换到指定标签页
        Args:
            url_pattern: URL模式或关键词
        Returns:
            是否成功切换
        """
        try:
            if not self.context:
                return False

            pages = self.context.pages
            for page in pages:
                if url_pattern.lower() in page.url.lower():
                    page.bring_to_front()
                    self.page = page
                    self.logger.info(f"已切换到标签页: {page.url}")
                    return True

            self.logger.warning(f"未找到包含 '{url_pattern}' 的标签页")
            return False

        except Exception as e:
            self.logger.error(f"切换标签页失败: {str(e)}")
            return False

    def list_all_tabs(self):
        """列出所有打开的标签页"""
        try:
            if not self.context:
                print("浏览器上下文不存在")
                return

            pages = self.context.pages
            print(f"\n当前打开的标签页 ({len(pages)} 个):")
            for i, page in enumerate(pages):
                current = "【当前】" if page == self.page else ""
                print(f"  {i+1}. {page.url} {current}")

        except Exception as e:
            self.logger.error(f"列出标签页失败: {str(e)}")

    def test_tab_functionality(self):
        """
        测试标签页功能
        """
        try:
            print("\n[测试] 测试标签页功能...")

            # 创建几个测试标签页
            test_urls = [
                "https://www.baidu.com",
                "https://www.example.com",
                "https://www.python.org"
            ]

            for url in test_urls:
                print(f"  创建标签页: {url}")
                self.create_new_tab(url)
                time.sleep(1)  # 短暂等待

            # 列出所有标签页
            self.list_all_tabs()

            # 切换到不同标签页测试
            for url in test_urls:
                domain = url.split("//")[1].split("/")[0]
                if self.switch_to_tab_by_url(domain):
                    print(f"  [成功] 成功切换到: {domain}")
                    time.sleep(1)

            print("[完成] 标签页功能测试完成")
            return True

        except Exception as e:
            self.logger.error(f"测试标签页功能失败: {str(e)}")
            return False

    def close_browser(self):
        """关闭浏览器"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.logger.info("浏览器已关闭")
        except Exception as e:
            self.logger.error(f"关闭浏览器时出错: {str(e)}")

    def login(self) -> bool:
        """
        登录WorldCat系统或验证当前登录状态
        Returns:
            是否登录成功
        """
        try:
            self.logger.info("检查WorldCat登录状态...")

            # 首先检查当前页面是否已经在高级检索页面
            if self.is_already_in_advanced_search():
                self.logger.info("检测到已在高级检索页面，直接使用")
                return True

            # 检查是否在WorldCat系统内但未进入高级检索
            if self.is_in_worldcat_system():
                self.logger.info("检测到已在WorldCat系统内，尝试进入高级检索")
                if self.goto_advanced_search():
                    self.save_login_state()
                    return True
                else:
                    self.logger.error("进入高级检索页面失败")
                    return False

            # 简化的快速启动：直接询问用户是否要手动登录
            return self.handle_simplified_login()

        except Exception as e:
            self.logger.error(f"登录检查失败: {str(e)}")
            return False

    def handle_simplified_login(self) -> bool:
        """
        处理简化的登录流程
        Returns:
            是否登录成功
        """
        try:
            print("\n" + "="*60)
            print("           WorldCat快速登录")
            print("="*60)
            print("正在打开登录页面...")

            # 直接打开指定的URL
            target_url = "https://z.library.sh.cn/next/resource/databases/search?searchTerm=worldcat&searchFacet=&sortOrder=relevance&t=1765196022231"

            try:
                self.page.goto(target_url, timeout=self.page_load_timeout)
                print(f"✅ 已打开页面: {target_url}")
            except Exception as e:
                self.logger.warning(f"打开页面失败: {str(e)}")
                print(f"⚠️  无法自动打开页面，请手动访问: {target_url}")
                input("请在浏览器中手动打开上述地址后按回车继续...")

            print("\n" + "="*60)
            print("请在浏览器中完成以下步骤:")
            print("1. 点击 WorldCat 链接")
            print("2. 如果需要，选择 '馆外访问'（通常会在新tab中打开）")
            print("3. 完成登录认证")
            print("4. 点击 '高级检索' 进入检索页面")
            print("="*60)

            while True:
                print("\n请选择操作:")
                print("  y - 我已进入高级检索页面，开始爬取")
                print("  r - 重新检查当前页面状态")
                print("  l - 列出所有打开的标签页")
                print("  w - 切换到WorldCat相关的标签页")
                print("  t - 跳过检查，直接在当前页面检索")
                print("  n - 在新标签页中打开WorldCat")
                print("  q - 退出程序")
                print("-"*40)

                choice = input("请输入选项: ").strip().lower()

                if choice == "q":
                    print("👋 程序退出")
                    return False
                elif choice == "t":
                    print("⚡ 跳过页面检查，准备开始爬取...")
                    self.save_login_state()
                    return True
                elif choice == "y":
                    print("✅ 验证页面状态...")
                    if self.is_already_in_advanced_search():
                        print("✅ 检测到高级检索页面，可以开始爬取!")
                        self.save_login_state()
                        return True
                    else:
                        print("❌ 当前页面不是高级检索页面")
                        print("   请确认已点击进入高级检索页面")
                        continue
                elif choice == "r":
                    print("🔍 检查当前页面状态...")
                    current_url = self.page.url
                    print(f"当前URL: {current_url}")

                    if self.is_already_in_advanced_search():
                        print("✅ 当前是高级检索页面!")
                        choice2 = input("是否直接开始爬取? (y/n): ").strip().lower()
                        if choice2 == "y":
                            self.save_login_state()
                            return True
                        else:
                            continue
                    elif self.is_in_worldcat_system():
                        print("✅ 检测到WorldCat系统")
                        if self.goto_advanced_search():
                            print("✅ 成功进入高级检索页面")
                            self.save_login_state()
                            return True
                        else:
                            print("❌ 请手动点击 '高级检索' 链接")
                            continue
                    else:
                        print("❌ 未检测到WorldCat系统，请完成登录")
                        continue
                elif choice == "l":
                    self.list_all_tabs()
                    continue
                elif choice == "w":
                    print("🔍 查找WorldCat相关标签页...")
                    worldcat_patterns = ["worldcat", "oclc.org", "firstsearch"]
                    found = False
                    for pattern in worldcat_patterns:
                        if self.switch_to_tab_by_url(pattern):
                            found = True
                            break

                    if not found:
                        print("❌ 未找到WorldCat相关标签页")
                        print("   您可能需要先手动点击WorldCat链接")
                    continue
                elif choice == "n":
                    worldcat_url = "https://www.worldcat.org/"
                    print(f"🌐 在新标签页中打开WorldCat: {worldcat_url}")
                    if self.create_new_tab(worldcat_url):
                        print("✅ 已在新标签页中打开WorldCat")
                        # 询问是否切换到新标签页
                        switch = input("是否切换到新标签页? (y/n): ").strip().lower()
                        if switch == "y":
                            self.switch_to_tab_by_url("worldcat")
                    else:
                        print("❌ 创建新标签页失败")
                    continue
                else:
                    print("❌ 无效输入，请输入 y、r、l、w、t、n 或 q")
                    continue

        except KeyboardInterrupt:
            print("\n👋 用户中断程序")
            return False
        except Exception as e:
            self.logger.error(f"简化登录流程失败: {str(e)}")
            return False

    def perform_manual_login_flow(self) -> bool:
        """
        执行手动登录流程
        Returns:
            是否登录成功
        """
        try:
            print("\n" + "="*60)
            print("           手动登录流程")
            print("="*60)
            print("正在打开登录页面...")

            # 尝试打开基础URL
            try:
                self.page.goto(self.base_url, timeout=10000)  # 减少超时时间
                print("✅ 页面已打开")
            except Exception as e:
                self.logger.warning(f"打开页面失败: {str(e)}")
                print("⚠️  无法自动打开页面，请手动在浏览器中访问以下地址:")
                print(f"   {self.base_url}")

            print("\n" + "-"*50)
            print("请按以下步骤完成登录:")
            print("1. 在浏览器中点击 'WorldCat' 链接")
            print("2. 选择 '馆外访问' (如需要)")
            print("3. 完成登录认证")
            print("4. 点击 '高级检索' 按钮进入检索页面")
            print("-"*50)
            print("\n📝 注意：")
            print("- 如果在新标签页中打开WorldCat，请切换到该标签页")
            print("- 确保最终进入有检索输入框的页面")
            print("-"*50)

            while True:
                print("\n请选择操作:")
                print("  y - 我已进入高级检索页面，开始爬取")
                print("  r - 重新检查当前页面")
                print("  t - 仅在当前页面尝试检索 (跳过检查)")
                print("  q - 退出程序")
                print("-"*30)

                user_input = input("请输入选项: ").strip().lower()

                if user_input == "q":
                    print("👋 程序退出")
                    return False
                elif user_input == "y":
                    print("✅ 开始验证页面状态...")
                    if self.is_already_in_advanced_search():
                        print("✅ 检测到高级检索页面!")
                        self.save_login_state()
                        return True
                    else:
                        print("❌ 当前页面不是高级检索页面，请确认已正确登录")
                        continue
                elif user_input == "r":
                    print("正在检查当前页面...")
                    current_url = self.page.url
                    print(f"当前URL: {current_url}")

                    if self.is_already_in_advanced_search():
                        print("✅ 检测到高级检索页面!")
                        choice = input("是否直接开始爬取? (y/n): ").strip().lower()
                        if choice == "y":
                            self.save_login_state()
                            return True
                        else:
                            continue
                    elif self.is_in_worldcat_system():
                        print("✅ 检测到WorldCat系统")
                        if self.goto_advanced_search():
                            print("✅ 成功进入高级检索页面")
                            self.save_login_state()
                            return True
                        else:
                            print("❌ 无法自动进入高级检索，请手动点击高级检索链接")
                            continue
                    else:
                        print("❌ 未检测到WorldCat系统，请完成登录")
                        continue
                elif user_input == "t":
                    print("⚡ 跳过检查，直接尝试检索...")
                    self.save_login_state()
                    return True
                else:
                    print("❌ 无效输入，请输入 y、r、t 或 q")
                    continue

        except KeyboardInterrupt:
            print("\n👋 用户中断程序")
            return False
        except Exception as e:
            self.logger.error(f"手动登录流程失败: {str(e)}")
            print(f"❌ 登录流程出错: {str(e)}")
            return False

    def check_current_page_for_worldcat(self) -> bool:
        """
        检查当前页面是否包含WorldCat特征
        Returns:
            是否检测到WorldCat特征
        """
        try:
            current_url = self.page.url.lower()

            # 检查URL特征
            worldcat_url_indicators = ['worldcat', 'firstsearch.oclc.org', 'oclc.org']
            if any(indicator in current_url for indicator in worldcat_url_indicators):
                self.logger.info(f"URL检测到WorldCat特征: {self.page.url}")
                return True

            # 检查页面内容特征
            try:
                page_content = self.page.content()
                worldcat_content_indicators = ['WorldCat', '高级检索', '世界各地拥有馆藏的图书馆']
                if any(indicator in page_content for indicator in worldcat_content_indicators):
                    self.logger.info("页面内容检测到WorldCat特征")
                    return True
            except:
                pass

            return False
        except Exception as e:
            self.logger.warning(f"检查页面WorldCat特征失败: {str(e)}")
            return False

    def is_already_in_advanced_search(self) -> bool:
        """
        检查是否已经在高级检索页面
        Returns:
            是否在高级检索页面
        """
        try:
            # 简化检查：只检查最关键的特征
            key_indicators = [
                'input[name="term1"]',      # 检索输入框
                '#term1',                   # ID选择器
                'input[placeholder*="检索"]' # 包含"检索"的placeholder
            ]

            # 快速检查，避免长时间等待
            for indicator in key_indicators:
                try:
                    locator = self.page.locator(indicator)
                    if locator.count() > 0 and locator.is_visible():
                        self.logger.info(f"检测到高级检索页面特征: {indicator}")
                        return True
                except:
                    continue

            # 备选检查：检查URL是否包含高级检索特征
            current_url = self.page.url.lower()
            if 'firstsearch.oclc.org' in current_url and 'search' in current_url:
                self.logger.info("URL检测到WorldCat检索页面特征")
                # 再检查页面是否有检索相关的表单元素
                try:
                    if self.page.locator('form').count() > 0:
                        return True
                except:
                    pass

            return False

        except Exception as e:
            self.logger.debug(f"检查高级检索页面状态时出错: {str(e)}")
            return False

    def is_in_worldcat_system(self) -> bool:
        """
        检查是否在WorldCat系统内（可能未进入高级检索）
        Returns:
            是否在WorldCat系统内
        """
        try:
            current_url = self.page.url.lower()

            # 简化URL检查
            worldcat_domains = ['worldcat', 'firstsearch.oclc.org', 'oclc.org']
            if any(domain in current_url for domain in worldcat_domains):
                self.logger.info(f"检测到WorldCat系统URL")
                return True

            # 快速内容检查
            try:
                # 只检查最明显的WorldCat特征
                if self.page.locator('text="WorldCat"').count() > 0:
                    self.logger.info("页面内容检测到WorldCat")
                    return True
            except:
                pass

            return False

        except Exception as e:
            self.logger.debug(f"检查WorldCat系统状态时出错: {str(e)}")
            return False

    # 移除复杂的自动登录方法，使用简化的手动登录流程
    # perform_full_login 方法已被 handle_simplified_login 替代

    def load_saved_state(self) -> bool:
        """
        加载已保存的登录状态
        Returns:
            是否成功加载状态
        """
        try:
            if not os.path.exists(self.cookie_file):
                self.logger.info("未找到已保存的Cookie文件")
                return False

            # 加载Cookie
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                self.context.add_cookies(cookies)

            # 加载状态（如果存在）
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    # 可以根据需要恢复其他状态信息

            self.logger.info(f"成功加载已保存的登录状态，Cookie数量: {len(cookies)}")
            return True

        except Exception as e:
            self.logger.error(f"加载登录状态失败: {str(e)}")
            return False

    def save_login_state(self):
        """
        保存登录状态
        """
        try:
            # 保存Cookie
            cookies = self.context.cookies()
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)

            # 保存额外状态信息
            state = {
                'url': self.page.url,
                'timestamp': time.time(),
                'user_agent': self.config.get('user_agent', 'default')
            }

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            self.logger.info(f"登录状态已保存，Cookie数量: {len(cookies)}")

        except Exception as e:
            self.logger.error(f"保存登录状态失败: {str(e)}")

    # 移除复杂的自动状态检查方法，改用简化流程
    # try_saved_login 方法已被 handle_simplified_login 替代

    def clear_saved_state(self) -> bool:
        """
        清理已保存的登录状态
        Returns:
            是否成功清理
        """
        try:
            cleared_files = []

            if os.path.exists(self.cookie_file):
                os.remove(self.cookie_file)
                cleared_files.append(self.cookie_file)

            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                cleared_files.append(self.state_file)

            if cleared_files:
                self.logger.info(f"已清理登录状态文件: {', '.join(cleared_files)}")
                return True
            else:
                self.logger.info("没有找到需要清理的登录状态文件")
                return True

        except Exception as e:
            self.logger.error(f"清理登录状态失败: {str(e)}")
            return False

    # 移除复杂的登录检查和手动处理方法
    # check_if_login_needed, handle_manual_login, verify_login_success 方法已被简化的方法替代

    def goto_advanced_search(self) -> bool:
        """
        导航到高级检索页面
        Returns:
            是否成功导航
        """
        try:
            # 查找高级检索链接
            advanced_link = self.page.locator('a:has-text("高级检索")')
            if advanced_link.count() == 0:
                self.logger.warning("未找到高级检索链接")
                return False

            # 尝试点击
            advanced_link.first.click()

            # 短暂等待，不使用长时间的超时
            try:
                self.page.wait_for_load_state('networkidle', timeout=self.page_load_timeout)
            except:
                pass  # 忽略超时错误

            # 简单等待
            time.sleep(2)

            # 验证是否成功进入高级检索页面
            if self.is_already_in_advanced_search():
                self.logger.info("成功进入高级检索页面")
                return True
            else:
                self.logger.warning("点击高级检索链接后未检测到高级检索页面")
                return False

        except Exception as e:
            self.logger.error(f"进入高级检索页面失败: {str(e)}")
            return False

    def build_query(self, search_term: str, search_type: str = "auto") -> str:
        """
        构建检索表达式
        Args:
            search_term: 搜索词
            search_type: 搜索类型 (auto, isbn, title)
        Returns:
            检索表达式
        """
        # 自动判断搜索类型
        if search_type == "auto":
            if self.is_isbn(search_term):
                search_type = "isbn"
            else:
                search_type = "title"

        if search_type == "isbn":
            return f"bn: {search_term}"
        elif search_type == "title":
            return f"ti: {search_term}"
        else:
            return f"kw: {search_term}"

    def is_isbn(self, term: str) -> bool:
        """
        判断是否为ISBN
        Args:
            term: 待判断的字符串
        Returns:
            是否为ISBN
        """
        # 移除所有非数字字符
        clean_term = ''.join(c for c in term if c.isdigit())
        return len(clean_term) in [10, 13] and clean_term.isdigit()

    def perform_search(self, query: str) -> bool:
        """
        执行检索操作
        Args:
            query: 检索表达式
        Returns:
            是否成功执行检索
        """
        try:
            self.logger.info(f"执行检索: {query}")
            current_url = self.page.url
            self.logger.info(f"检索前页面URL: {current_url}")

            # 确保在高级检索页面
            if not self.is_already_in_advanced_search():
                self.logger.warning("当前不在高级检索页面，尝试返回")
                if not self.return_to_advanced_search():
                    self.logger.error("无法返回高级检索页面")
                    return False

            # 查找检索输入框，尝试多种可能的定位器
            input_found = False
            input_selectors = [
                '#term1',
                'input[name="term1"]',
                'input[type="text"]',
                'input[placeholder*="检索"]',
                'input[name*="term"]',
                'textarea[name="term1"]'  # 有时可能是textarea
            ]

            for selector in input_selectors:
                try:
                    locator = self.page.locator(selector)
                    count = locator.count()
                    self.logger.debug(f"选择器 {selector} 找到 {count} 个元素")

                    if count > 0:
                        # 检查是否可见
                        try:
                            is_visible = locator.first.is_visible()
                            self.logger.debug(f"选择器 {selector} 可见性: {is_visible}")
                            if is_visible:
                                # 先清空再填入
                                locator.first.clear()
                                locator.first.fill(query)
                                input_found = True
                                self.logger.info(f"使用选择器 {selector} 成功填入检索词")
                                break
                        except:
                            # 如果不可见，尝试等待后重试
                            self.logger.debug(f"选择器 {selector} 不可见，尝试等待")
                            try:
                                locator.first.wait_for(state='visible', timeout=5000)
                                locator.first.clear()
                                locator.first.fill(query)
                                input_found = True
                                self.logger.info(f"等待后使用选择器 {selector} 成功填入检索词")
                                break
                            except:
                                continue
                except Exception as e:
                    self.logger.debug(f"选择器 {selector} 失败: {str(e)}")
                    continue

            if not input_found:
                self.logger.error("未找到可用的检索输入框")
                # 输出页面信息用于调试
                try:
                    self.logger.debug(f"当前页面URL: {self.page.url}")
                    page_inputs = self.page.query_selector_all('input, textarea')
                    self.logger.debug(f"页面中有 {len(page_inputs)} 个输入元素")
                    for i, inp in enumerate(page_inputs[:5]):
                        inp_type = inp.get_attribute('type') or 'unknown'
                        inp_name = inp.get_attribute('name') or 'unknown'
                        inp_placeholder = inp.get_attribute('placeholder') or 'none'
                        self.logger.debug(f"输入框 {i+1}: type={inp_type}, name={inp_name}, placeholder={inp_placeholder}")
                except:
                    pass

                # 当找不到输入框时，尝试自动返回高级检索页面
                self.logger.warning("尝试自动返回高级检索页面以找到输入框")
                if self.return_to_advanced_search():
                    # 返回成功后，重新尝试查找输入框
                    self.logger.info("重新查找检索输入框")
                    for selector in input_selectors:
                        try:
                            locator = self.page.locator(selector)
                            if locator.count() > 0 and locator.first.is_visible():
                                locator.first.clear()
                                locator.first.fill(query)
                                input_found = True
                                self.logger.info(f"返回页面后使用选择器 {selector} 成功填入检索词")
                                break
                        except:
                            continue

                if not input_found:
                    self.logger.error("返回高级检索页面后仍无法找到检索输入框")
                    return False

            # 尝试选择"书"类型（可选）
            try:
                book_checkbox = self.page.locator('#dt-bks, input[value="Book"], input[value="书籍"]')
                if book_checkbox.count() > 0 and not book_checkbox.first.is_checked():
                    book_checkbox.first.check()
                    self.logger.info("已选择书籍类型")
            except:
                pass  # 选择书籍类型不是必须的

            # 查找检索按钮，尝试多种可能的定位器
            search_found = False
            button_selectors = [
                'input[name="action"][value="检索"]',
                'input[value="检索"]',
                'input[type="submit"]',
                'button:has-text("检索")',
                'button:has-text("Search")',
                'input[value*="检索"]',
                'button[type="submit"]'
            ]

            for selector in button_selectors:
                try:
                    button = self.page.locator(selector)
                    count = button.count()
                    self.logger.debug(f"按钮选择器 {selector} 找到 {count} 个元素")

                    if count > 0 and button.first.is_visible():
                        button.first.click()
                        search_found = True
                        self.logger.info(f"使用选择器 {selector} 成功点击检索按钮")
                        break
                except Exception as e:
                    self.logger.debug(f"按钮选择器 {selector} 失败: {str(e)}")
                    continue

            if not search_found:
                self.logger.error("未找到可用的检索按钮")
                return False

            # 等待结果页面加载
            try:
                self.page.wait_for_load_state('networkidle', timeout=self.page_load_timeout)
            except:
                pass  # 忽略超时，继续执行

            time.sleep(3)  # 给页面额外时间加载

            # 验证页面是否发生变化
            new_url = self.page.url
            if new_url != current_url:
                self.logger.info(f"页面已跳转，当前URL: {new_url}")
            else:
                self.logger.warning("页面URL未发生变化，可能检索未执行")

            return True

        except Exception as e:
            self.logger.error(f"执行检索失败: {str(e)}")
            return False

    def process_search_results(self) -> List[LibraryInfo]:
        """
        处理检索结果
        Returns:
            图书馆信息列表
        """
        try:
            # 检查是否无结果
            no_results_locator = self.page.locator('text="没有和检索相配的记录"')
            if no_results_locator.is_visible():
                self.logger.info("没有找到匹配的记录")
                return []

            # 查找"世界各地拥有馆藏的图书馆"链接
            holdings_links = self.page.locator('a:has-text("世界各地拥有馆藏的图书馆")')

            if holdings_links.count() == 0:
                self.logger.warning("未找到馆藏信息链接")
                return []

            if holdings_links.count() == 1:
                # 单结果情况
                self.logger.info("检测到单一结果")
                holdings_links.first.click()
                self.page.wait_for_load_state('networkidle')
                time.sleep(2)
                return self.extract_libraries_from_page()

            else:
                # 多结果情况 - 选择图书馆数量最多的结果
                self.logger.info(f"检测到多个结果: {holdings_links.count()} 个")
                return self.process_multiple_results(holdings_links)

        except Exception as e:
            self.logger.error(f"处理检索结果失败: {str(e)}")
            return []

    def process_multiple_results(self, holdings_links) -> List[LibraryInfo]:
        """
        处理多个检索结果
        Args:
            holdings_links: 馆藏信息链接列表
        Returns:
            图书馆信息列表
        """
        try:
            max_count = 0
            best_link = None

            for i, link in enumerate(holdings_links.all()):
                try:
                    # 获取链接元素本身
                    text = link.text_content()
                    self.logger.debug(f"链接 {i+1} 文本: {text}")

                    # 由于数字在链接外部，我们需要通过JavaScript获取完整的文本
                    # 或者通过查找父级nobr元素来获取包含数字的完整文本
                    try:
                        # 尝试找到包含链接和数字的父级元素（nobr标签）
                        nobr_parent = link.locator('xpath=./ancestor::nobr[1]')
                        if nobr_parent.count() > 0:
                            full_text = nobr_parent.first.text_content()
                            self.logger.debug(f"完整文本: {full_text}")

                            if ":" in full_text:
                                # 提取数量，如 "世界各地拥有馆藏的图书馆: 15"
                                count_part = full_text.split(":")[1].strip()
                                # 清理可能的空白字符
                                count_str = ''.join(count_part.split())
                                try:
                                    count = int(count_str)
                                    self.logger.debug(f"提取到数量: {count}")
                                    if count > max_count:
                                        max_count = count
                                        best_link = link
                                except ValueError:
                                    # 如果直接转换失败，尝试从文本中提取数字
                                    import re
                                    numbers = re.findall(r'\d+', count_str)
                                    if numbers:
                                        count = int(numbers[0])
                                        self.logger.debug(f"正则提取到数量: {count}")
                                        if count > max_count:
                                            max_count = count
                                            best_link = link
                        else:
                            # 回退方案：使用JavaScript获取完整文本
                            js_code = """
                            var link = arguments[0];
                            var parent = link.parentElement;
                            return parent ? parent.textContent : link.textContent;
                            """
                            full_text = link.evaluate(js_code)
                            self.logger.debug(f"JS获取完整文本: {full_text}")

                            if full_text and ":" in full_text:
                                count_part = full_text.split(":")[1].strip()
                                import re
                                numbers = re.findall(r'\d+', count_part)
                                if numbers:
                                    count = int(numbers[0])
                                    self.logger.debug(f"JS正则提取到数量: {count}")
                                    if count > max_count:
                                        max_count = count
                                        best_link = link
                    except Exception as extract_error:
                        self.logger.debug(f"提取数量失败: {str(extract_error)}")
                        # 如果提取数字失败，仍然可以使用这个链接（作为备选）
                        if best_link is None:
                            best_link = link
                            max_count = 1  # 给一个默认值

                except Exception as e:
                    self.logger.debug(f"处理链接 {i+1} 失败: {str(e)}")
                    continue

            if best_link:
                self.logger.info(f"选择图书馆数量最多的结果: {max_count} 个")
                best_link.click()

                # 等待页面加载
                try:
                    self.page.wait_for_load_state('networkidle', timeout=self.page_load_timeout)
                except:
                    pass  # 忽略超时错误

                time.sleep(2)
                return self.extract_libraries_from_page()
            else:
                self.logger.warning("未找到有效的结果链接")
                return []

        except Exception as e:
            self.logger.error(f"处理多个结果失败: {str(e)}")
            return []

    def extract_libraries_from_page(self) -> List[LibraryInfo]:
        """
        从页面提取图书馆信息
        Returns:
            图书馆信息列表
        """
        libraries = []

        try:
            # 等待馆藏表格加载，增加更多可能的选择器
            selectors_to_try = [
                'table tbody tr',
                'table tr',
                'tbody tr',
                'tr[valign="top"]'
            ]

            rows = []
            for selector in selectors_to_try:
                try:
                    rows = self.page.query_selector_all(selector)
                    if len(rows) > 0:
                        self.logger.info(f"使用选择器 '{selector}' 找到 {len(rows)} 行")
                        break
                except:
                    continue

            if not rows:
                self.logger.warning("未找到馆藏信息表格行")
                return []

            # 过滤掉分隔行和无效行
            data_rows = []
            for row in rows:
                try:
                    # 检查是否是分隔行（包含colspan属性）
                    colspan_cells = row.query_selector_all('td[colspan]')
                    if len(colspan_cells) > 0:
                        continue

                    # 检查是否有有效的图书馆数据（至少有3个td）
                    cells = row.query_selector_all('td')
                    if len(cells) >= 3:
                        # 进一步验证是否为有效的图书馆行
                        # 检查第一个td是否包含地理位置信息（通常是2-3个字母的代码）
                        first_td_text = ""
                        try:
                            first_td_elem = row.query_selector('td:nth-child(1)')
                            if first_td_elem:
                                first_td_text = first_td_elem.text_content().strip()
                        except:
                            continue

                        # 验证第一个td内容是否像地理位置（如CN, US, HK等）
                        # 排除明显不是地理位置的文本
                        invalid_patterns = [
                            "详细书目", "记录", "电子邮件", "馆际互借", "打印", "返回", "帮助",
                            "主题", "获此文献", "求借信息", "检查", "外部資源", "引用",
                            "查找相关", "其它类似记录", "题名", "著者", "目前所选", "数据库"
                        ]

                        is_valid_location = True
                        for pattern in invalid_patterns:
                            if pattern in first_td_text:
                                is_valid_location = False
                                break

                        # 检查是否包含常见的地理位置格式（如CN, US, HK或带有逗号格式）
                        if is_valid_location:
                            # 如果内容很短（2-10个字符）且不包含中文，可能是地理位置
                            if len(first_td_text) <= 10 and not any('\u4e00' <= char <= '\u9fff' for char in first_td_text):
                                data_rows.append(row)
                            # 或者包含逗号分隔的地理位置（如US,CO）
                            elif ',' in first_td_text and len(first_td_text.split(',')) >= 2:
                                data_rows.append(row)
                            # 或者是明确的位置代码
                            elif first_td_text in ['CN', 'US', 'HK', 'TW', 'SG', 'JP', 'KR', 'GB', 'DE', 'FR', 'CA', 'AU']:
                                data_rows.append(row)

                except:
                    continue

            self.logger.info(f"找到 {len(data_rows)} 行有效的图书馆信息")

            for row in data_rows:
                try:
                    # 更通用的提取方法，尝试多种选择器
                    location = ""
                    library_name = ""
                    code = ""
                    library_url = ""

                    # 尝试提取位置信息（第1个td中的文本）
                    location_elem = row.query_selector('td:nth-child(1) font, td:nth-child(1)')
                    if location_elem:
                        location = location_elem.text_content().strip()
                        # 如果位置包含逗号，只取第一部分（如US,CO -> US）
                        if ',' in location:
                            location = location.split(',')[0]

                    # 尝试提取图书馆名称（第2个td中的文本）
                    # 尝试多种选择器来获取图书馆名称
                    library_selectors = [
                        'td:nth-child(2) b font',
                        'td:nth-child(2) b',
                        'td:nth-child(2) font',
                        'td:nth-child(2)'
                    ]

                    for selector in library_selectors:
                        library_elem = row.query_selector(selector)
                        if library_elem:
                            library_name = library_elem.text_content().strip()
                            if library_name:
                                break

                    # 尝试提取图书馆代码（第3个或第4个td）
                    code_selectors = [
                        'td:nth-child(3) font',
                        'td:nth-child(3)',
                        'td:nth-child(4) font',
                        'td:nth-child(4)'
                    ]

                    for selector in code_selectors:
                        code_elem = row.query_selector(selector)
                        if code_elem:
                            code = code_elem.text_content().strip()
                            # 清理代码中的多余空白和特殊字符
                            code = ' '.join(code.split())
                            if code:
                                break

                    # 尝试提取图书馆链接
                    library_link_selectors = [
                        'td:nth-child(2) b font a',
                        'td:nth-child(2) b a',
                        'td:nth-child(2) a'
                    ]

                    for selector in library_link_selectors:
                        library_link_elem = row.query_selector(selector)
                        if library_link_elem:
                            library_url = library_link_elem.get_attribute('href') or ""
                            if library_url:
                                break

                    # 只添加有效的图书馆信息
                    if library_name and location:
                        libraries.append(LibraryInfo(
                            name=library_name,
                            location=location,
                            code=code,
                            url=library_url
                        ))
                        self.logger.info(f"提取到图书馆: {library_name} ({location}) - {code}")

                except Exception as e:
                    self.logger.debug(f"提取单行图书馆信息失败: {str(e)}")
                    continue

            self.logger.info(f"成功提取 {len(libraries)} 个图书馆信息")

            # 输出所有提取的图书馆信息用于调试
            for i, lib in enumerate(libraries):
                self.logger.info(f"图书馆 {i+1}: {lib.name} ({lib.location}) - {lib.code}")

            return libraries

        except Exception as e:
            self.logger.error(f"提取图书馆信息失败: {str(e)}")
            return []

    def filter_libraries(self, libraries: List[LibraryInfo]) -> List[str]:
        """
        过滤非CN地区的图书馆并去重
        Args:
            libraries: 图书馆信息列表
        Returns:
            过滤去重后的海外图书馆名称列表
        """
        filtered = []
        seen_names = set()
        cn_count = 0
        overseas_count = 0

        for library in libraries:
            # 统计CN和海外图书馆数量
            if library.location == "CN":
                cn_count += 1
                self.logger.debug(f"过滤掉CN图书馆: {library.name}")
            else:
                overseas_count += 1
                # 过滤位置不是CN的图书馆，并去重
                if library.name not in seen_names:
                    filtered.append(library.name)
                    seen_names.add(library.name)
                    self.logger.debug(f"保留海外图书馆: {library.name} ({library.location})")

        self.logger.info(f"图书馆统计 - 总计: {len(libraries)}, CN地区: {cn_count}, 海外地区: {overseas_count}")
        self.logger.info(f"过滤去重后得到 {len(filtered)} 个海外图书馆")

        # 输出过滤后的图书馆列表用于验证
        if filtered:
            self.logger.debug(f"海外图书馆列表: {', '.join(filtered[:10])}{'...' if len(filtered) > 10 else ''}")

        return filtered

    def return_to_advanced_search(self) -> bool:
        """
        返回高级检索页面 - 通过点击"检索"链接
        Returns:
            是否成功返回
        """
        try:
            self.logger.info("尝试点击'检索'链接返回高级检索页面")
            current_url = self.page.url
            self.logger.info(f"当前页面URL: {current_url}")

            # 尝试点击"检索"链接
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    self.logger.info(f"第 {attempt + 1} 次尝试查找并点击'检索'链接")

                    # 多种可能的"检索"链接选择器
                    search_link_selectors = [
                        'a:has-text("检索")',
                        'a[title*="检索"]',
                        'a[href*="advanced"]',
                        'td.subOption a:has-text("检索")',
                        'font a:has-text("检索")',
                        'a[href*="FSPage"]',
                        'x:has-text("检索")',  # 针对 <x> 标签
                        'a font:has-text("检索")'
                    ]

                    link_found = False
                    for selector in search_link_selectors:
                        try:
                            links = self.page.locator(selector)
                            count = links.count()
                            self.logger.debug(f"选择器 {selector} 找到 {count} 个链接")

                            if count > 0:
                                # 查找包含"检索"文本的链接
                                for i in range(count):
                                    link = links.nth(i)
                                    try:
                                        link_text = link.text_content() or ""
                                        if "检索" in link_text:
                                            href = link.get_attribute('href') or ""
                                            self.logger.info(f"找到'检索'链接: {link_text}, href: {href}")

                                            # 点击链接
                                            link.click()
                                            link_found = True
                                            self.logger.info(f"已点击'检索'链接")
                                            break
                                    except:
                                        continue

                                if link_found:
                                    break

                        except Exception as e:
                            self.logger.debug(f"选择器 {selector} 查找失败: {str(e)}")
                            continue

                    if link_found:
                        # 等待页面加载
                        try:
                            self.page.wait_for_load_state('networkidle', timeout=self.page_load_timeout)
                        except:
                            pass  # 忽略超时，继续执行

                        time.sleep(3)  # 给页面额外时间加载

                        # 检查是否已经进入高级检索页面
                        if self.is_already_in_advanced_search():
                            self.logger.info("点击'检索'链接后成功进入高级检索页面")
                            return True
                        else:
                            self.logger.warning(f"点击'检索'链接后未检测到高级检索页面，当前URL: {self.page.url}")
                            if attempt < max_attempts - 1:
                                time.sleep(2)
                                continue
                    else:
                        self.logger.warning(f"第 {attempt + 1} 次未找到'检索'链接")

                        # 如果是最后一次尝试，等待用户手动确认
                        if attempt == max_attempts - 1:
                            self.logger.warning("自动点击'检索'链接失败，等待用户手动确认")
                            print("\n" + "="*50)
                            print("⚠️  自动返回检索页面失败")
                            print("请手动完成以下步骤:")
                            print("1. 在页面中查找并点击 '检索' 链接")
                            print("2. 确保页面显示检索输入框")
                            print("3. 检索链接通常在导航栏或菜单中")
                            print("="*50)

                            while True:
                                user_input = input("完成后请输入 'y' 继续，或输入 'r' 重试点击: ").strip().lower()
                                if user_input == 'y':
                                    # 再次检查页面状态
                                    if self.is_already_in_advanced_search():
                                        self.logger.info("用户确认后检测到高级检索页面")
                                        return True
                                    else:
                                        self.logger.warning("用户确认后仍未检测到高级检索页面")
                                        print("❌ 当前页面仍不是高级检索页面，请检查是否已完成操作")
                                        continue
                                elif user_input == 'r':
                                    # 重试点击
                                    break
                                else:
                                    print("请输入 'y' 或 'r'")
                                    continue

                except Exception as click_error:
                    self.logger.error(f"第 {attempt + 1} 次点击'检索'链接失败: {str(click_error)}")
                    if attempt < max_attempts - 1:
                        continue

            # 如果所有尝试都失败
            self.logger.error("所有返回高级检索页面的尝试都失败了")
            return False

        except Exception as e:
            self.logger.error(f"返回高级检索页面失败: {str(e)}")
            # 出现异常时也等待用户确认
            try:
                print("\n" + "="*50)
                print("⚠️  返回检索页面时出现异常")
                print("请手动点击'检索'链接返回检索页面")
                print("="*50)

                while True:
                    user_input = input("完成后请输入 'y' 继续: ").strip().lower()
                    if user_input == 'y':
                        if self.is_already_in_advanced_search():
                            self.logger.info("用户确认后检测到高级检索页面")
                            return True
                        else:
                            print("❌ 当前页面仍不是高级检索页面")
                            continue
                    else:
                        print("请输入 'y'")
                        continue
            except KeyboardInterrupt:
                self.logger.info("用户中断操作")
                return False

    def scrape(self, search_term: str) -> WorldCatResult:
        """
        执行单次爬取操作
        Args:
            search_term: 搜索词
        Returns:
            爬取结果
        """
        search_url = self.page.url if self.page else ""

        try:
            self.logger.info(f"开始爬取: {search_term}")

            # 构建查询
            query = self.build_query(search_term)

            # 执行检索
            if not self.perform_search(query):
                return WorldCatResult(
                    success=False,
                    search_term=search_term,
                    libraries=[],
                    libraries_count=0,
                    all_libraries=[],
                    error_message="检索执行失败",
                    search_url=search_url
                )

            # 处理检索结果
            all_libraries = self.process_search_results()

            # 过滤图书馆
            overseas_libraries = self.filter_libraries(all_libraries)

            success = len(overseas_libraries) > 0

            self.logger.info(f"爬取完成: {search_term}, 海外图书馆数量: {len(overseas_libraries)}")

            return WorldCatResult(
                success=success,
                search_term=search_term,
                libraries=overseas_libraries,
                libraries_count=len(overseas_libraries),
                all_libraries=all_libraries,
                search_url=search_url,
                detail_url=self.page.url if self.page else ""
            )

        except Exception as e:
            self.logger.error(f"爬取失败: {search_term}, 错误: {str(e)}")
            return WorldCatResult(
                success=False,
                search_term=search_term,
                libraries=[],
                libraries_count=0,
                all_libraries=[],
                error_message=str(e),
                search_url=search_url
            )

    def save_results_to_excel(self, results: List[WorldCatResult], output_file: str):
        """
        保存结果到Excel文件 - 每个海外图书馆占据一列（横向排列）
        Args:
            results: 爬取结果列表
            output_file: 输出文件路径
        """
        try:
            data = []

            # 首先找到最大的海外图书馆数量，用于确定列数
            max_libraries = max((r.libraries_count for r in results), default=0)

            # 创建列名
            columns = ['检索词', '海外图书馆总数', '检索成功', '错误信息']
            for i in range(1, max_libraries + 1):
                columns.append(f'海外图书馆{i}')

            # 为每个结果创建一行数据
            for result in results:
                row_data = {
                    '检索词': result.search_term,
                    '海外图书馆总数': result.libraries_count,
                    '检索成功': '是' if result.success else '否',
                    '错误信息': result.error_message if not result.success else ''
                }

                # 添加海外图书馆到各自的列中
                if result.success and result.libraries:
                    for i, library in enumerate(result.libraries):
                        column_name = f'海外图书馆{i + 1}'
                        row_data[column_name] = library

                # 如果没有足够的图书馆，其他列留空
                data.append(row_data)

            # 创建DataFrame
            df = pd.DataFrame(data, columns=columns)

            # 确保输出目录存在
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存到Excel
            df.to_excel(output_file, index=False, engine='openpyxl')

            # 输出统计信息
            total_search_terms = len(results)
            successful_searches = sum(1 for r in results if r.success)
            total_libraries = sum(r.libraries_count for r in results)

            self.logger.info(f"结果已保存到 {output_file}")
            self.logger.info(f"Excel统计 - 搜索词总数: {total_search_terms}, 成功检索: {successful_searches}, "
                           f"海外图书馆总数: {total_libraries}, Excel列数: {4 + max_libraries}")

        except Exception as e:
            self.logger.error(f"保存结果到Excel失败: {str(e)}")
            raise

    def batch_scrape(self, search_terms: List[str], output_file: str) -> List[WorldCatResult]:
        """
        批量爬取
        Args:
            search_terms: 搜索词列表
            output_file: 输出文件路径
        Returns:
            爬取结果列表
        """
        results = []

        try:
            for i, search_term in enumerate(search_terms):
                try:
                    self.logger.info(f"正在处理第 {i+1}/{len(search_terms)} 个: {search_term}")

                    # 执行搜索
                    result = self.scrape(search_term)
                    results.append(result)

                    # 随机延时避免被封
                    delay = random.uniform(*self.delay_range)
                    self.logger.debug(f"等待 {delay:.1f} 秒...")
                    time.sleep(delay)

                    # 返回高级检索页面进行下一次搜索
                    if i < len(search_terms) - 1:
                        if not self.return_to_advanced_search():
                            self.logger.warning("无法返回高级检索页面，可能影响后续搜索")

                except Exception as e:
                    self.logger.error(f"处理 {search_term} 时出错: {str(e)}")
                    # 添加失败结果
                    results.append(WorldCatResult(
                        success=False,
                        search_term=search_term,
                        libraries=[],
                        libraries_count=0,
                        all_libraries=[],
                        error_message=str(e)
                    ))

            # 保存结果
            self.save_results_to_excel(results, output_file)

            # 输出统计信息
            successful_count = sum(1 for r in results if r.success)
            total_libraries = sum(r.libraries_count for r in results)

            self.logger.info(f"批量爬取完成!")
            self.logger.info(f"总计: {len(results)} 个搜索词, 成功: {successful_count}, 总图书馆数: {total_libraries}")

            return results

        except Exception as e:
            self.logger.error(f"批量爬取失败: {str(e)}")
            raise