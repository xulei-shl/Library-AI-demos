"""
登录处理模块
负责检测和处理登录相关的问题
"""

import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.json") -> dict:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"配置文件 {config_path} 不存在，使用默认配置")
            return {}
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}


class LoginHandler:
    """登录处理类"""
    
    def __init__(self, page, headless: bool = False):
        """
        初始化登录处理器
        
        Args:
            page: Playwright页面对象
            headless: 是否使用无头模式
        """
        self.page = page
        self.headless = headless
        
    def check_login_page(self, page_type: str = "normal") -> bool:
        """
        改进的登录页面检测（更加宽松）
        
        Args:
            page_type: 页面类型 ('normal', 'search', 'detail')，不同类型有不同的检测标准
            
        Returns:
            是否需要登录
        """
        try:
            current_url = self.page.url
            title = self.page.title()
            
            logger.debug(f"当前URL: {current_url}")
            logger.debug(f"页面标题: {title}")
            
            # 获取页面内容
            content = self.page.content()
            content_lower = content.lower()
            
            # 1. 优先检查是否包含登录跳转标题 - 这种页面通常只需要点击链接跳转
            if '<h1>登录跳转</h1>' in content:
                logger.info("检测到登录跳转标题页面，尝试自动点击登录链接")
                # 尝试自动点击登录链接
                if self._auto_click_login_link():
                    logger.info("成功点击登录链接，等待跳转...")
                    # 等待页面跳转
                    time.sleep(3)
                    
                    # 检查跳转结果
                    new_url = self.page.url
                    new_content = self.page.content().lower()
                    
                    # 如果跳转到了真正的登录页面
                    if 'accounts.douban.com/passport/login' in new_url:
                        logger.info("成功跳转到登录页面，需要登录")
                        return True
                    elif 'book.douban.com' in new_url and not self._has_login_form(new_content):
                        logger.info("成功跳转回正常页面，无需登录")
                        return False
                    else:
                        logger.info("点击链接后等待跳转...")
                        return False  # 暂时认为不需要登录，等待跳转完成
                else:
                    logger.warning("无法自动点击登录链接，跳过处理")
                    return False  # 无法点击时跳过
            
            # 2. 检查是否跳转到明确的登录/验证页面（保持严格）
            login_url_patterns = [
                'login', 'captcha', 'unusual', 'sec.douban.com',
                'accounts.google.com', 'verification'
            ]
            if any(pattern in current_url.lower() for pattern in login_url_patterns):
                logger.warning("检测到明确的登录/验证页面跳转")
                return True
            
            # 3. 检查页面内容中的登录跳转标识
            if self._check_login_redirect(content_lower, current_url):
                return True
            
            # 4. 根据页面类型进行不同的检测（调整严格程度）
            if page_type == "search":
                # 搜索页面：更宽松的检测
                return self._check_search_login(content_lower, current_url)
            elif page_type == "detail":
                # 详情页面：中等严格程度
                return self._check_detail_login(content_lower, current_url)
            else:
                # 首页/常规页面：中等严格程度
                return self._check_normal_login(content_lower, current_url)
                
        except Exception as e:
            logger.error(f"登录检测时发生错误: {e}")
            return False
    
    def auto_login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        自动登录豆瓣账号
        
        Args:
            username: 用户名（如果为None则从配置文件读取）
            password: 密码（如果为None则从配置文件读取）
            
        Returns:
            是否成功登录
        """
        logger.info("开始自动登录流程...")
        
        if self.headless:
            logger.error("当前为无头模式，无法进行自动登录。请设置为headless=False")
            return False
            
        # 从配置文件加载用户名和密码
        if username is None or password is None:
            config = load_config()
            douban_config = config.get('douban', {})
            username = username or douban_config.get('username', '')
            password = password or douban_config.get('password', '')
        
        if not username or not password:
            logger.error("无法从配置文件中获取登录凭据，请检查 config.json 文件中的 douban 配置")
            return False
            
        try:
            # 等待页面加载
            time.sleep(2)
            
            # 1. 点击"密码登录"标签
            if not self._click_password_login_tab():
                logger.error("无法点击密码登录标签")
                return False
                
            # 2. 等待密码登录表单加载
            time.sleep(2)
            
            # 3. 输入用户名和密码
            if not self._fill_login_form(username, password):
                logger.error("无法填写登录表单")
                return False
                
            # 4. 点击登录按钮
            if not self._click_login_button():
                logger.error("无法点击登录按钮")
                return False
                
            # 5. 等待登录结果
            time.sleep(3)
            
            # 6. 检查是否需要人工滑动验证
            if self._requires_captcha():
                logger.info("检测到滑动验证，需要人工操作")
                logger.info("请手动完成滑动验证，然后在终端输入 'y' 继续")
                
                try:
                    while True:
                        user_input = input("滑动验证完成后请输入 'y' 继续 (或输入 'n' 跳过): ").strip().lower()
                        if user_input == 'y':
                            logger.info("用户确认滑动验证完成")
                            return self._check_login_success()
                        elif user_input == 'n':
                            logger.info("用户选择跳过")
                            return False
                        else:
                            logger.info("请输入 'y' 继续或 'n' 跳过")
                except (EOFError, KeyboardInterrupt):
                    # 处理 EOF 错误或用户中断，不抛出异常
                    logger.warning("检测到滑动验证但无法获取用户输入，登录流程被中断")
                    return False
            else:
                # 没有滑动验证，检查登录是否成功
                return self._check_login_success()
                
        except Exception as e:
            logger.error(f"自动登录过程中发生错误: {e}")
            return False
    
    def _click_password_login_tab(self) -> bool:
        """点击密码登录标签"""
        try:
            # 等待页面加载完成
            time.sleep(1)
            
            # 查找密码登录标签 - 使用更精确的选择器
            password_tab_selectors = [
                'li.account-tab-account',  # 基于HTML结构的选择器
                '.account-tab-account',
                'a:has-text("密码登录")',
                'text=密码登录'
            ]
            
            for selector in password_tab_selectors:
                try:
                    logger.debug(f"尝试使用选择器找到密码登录标签: {selector}")
                    element = self.page.locator(selector).first
                    
                    # 检查元素是否可见
                    if element.is_visible(timeout=5000):
                        element.click()
                        logger.info(f"成功点击密码登录标签，使用选择器: {selector}")
                        # 等待标签切换完成
                        time.sleep(2)
                        return True
                    else:
                        logger.debug(f"选择器 {selector} 找到但不可见")
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue
                    
            # 如果直接选择器失败，尝试通过文本内容查找
            try:
                # 查找包含"密码登录"文本的li元素
                all_li_elements = self.page.locator('li.account-tab-phone').locator('xpath=../li').all()
                
                for li in all_li_elements:
                    text_content = li.inner_text()
                    if '密码登录' in text_content:
                        li.click()
                        logger.info("通过文本内容成功点击密码登录标签")
                        time.sleep(2)
                        return True
            except Exception as e:
                logger.debug(f"通过文本内容查找失败: {e}")
            
            logger.warning("未找到密码登录标签")
            return False
            
        except Exception as e:
            logger.error(f"点击密码登录标签时发生错误: {e}")
            return False
    
    def _fill_login_form(self, username: str, password: str) -> bool:
        """填写登录表单"""
        try:
            # 1. 输入用户名
            username_selectors = [
                '#username[name="username"]',
                'input[name="username"]',
                '#username'
            ]
            
            username_filled = False
            for selector in username_selectors:
                try:
                    username_field = self.page.locator(selector).first
                    if username_field.is_visible(timeout=3000):
                        username_field.fill(username)
                        logger.info(f"成功输入用户名: {username}")
                        username_filled = True
                        break
                except:
                    continue
                    
            if not username_filled:
                logger.error("无法找到用户名输入框")
                return False
                
            # 2. 输入密码
            password_selectors = [
                '#password[type="password"]',
                'input[name="password"]',
                '#password'
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    password_field = self.page.locator(selector).first
                    if password_field.is_visible(timeout=3000):
                        password_field.fill(password)
                        logger.info("成功输入密码")
                        password_filled = True
                        break
                except:
                    continue
                    
            if not password_filled:
                logger.error("无法找到密码输入框")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"填写登录表单时发生错误: {e}")
            return False
    
    def _click_login_button(self) -> bool:
        """点击登录按钮"""
        try:
            login_button_selectors = [
                '.btn.btn-account',
                'a.btn.btn-account',
                '登录豆瓣',
                'button[type="submit"]'
            ]
            
            for selector in login_button_selectors:
                try:
                    login_button = self.page.locator(selector).first
                    if login_button.is_visible(timeout=3000):
                        login_button.click()
                        logger.info("成功点击登录按钮")
                        return True
                except:
                    continue
                    
            logger.warning("未找到登录按钮")
            return False
            
        except Exception as e:
            logger.error(f"点击登录按钮时发生错误: {e}")
            return False
    
    def _requires_captcha(self) -> bool:
        """检查是否需要滑动验证"""
        try:
            # 检查页面是否包含滑动验证相关元素
            captcha_indicators = [
                '滑块验证',
                'captcha',
                '验证码',
                'geetest',
                '滑动',
                'slider'
            ]
            
            content = self.page.content().lower()
            
            for indicator in captcha_indicators:
                if indicator in content:
                    logger.info(f"检测到可能的滑动验证: {indicator}")
                    return True
                    
            # 检查是否还有登录表单（如果还有，说明登录可能失败或需要验证）
            remaining_forms = self.page.locator('input[type="password"]').count()
            if remaining_forms > 0:
                current_url = self.page.url
                if 'login' in current_url.lower() or 'captcha' in current_url.lower():
                    logger.info("仍在登录页面，可能需要滑动验证")
                    return True
                    
            return False
            
        except Exception as e:
            logger.debug(f"检查滑动验证时发生错误: {e}")
            return False
    
    def _check_login_success(self) -> bool:
        """检查登录是否成功"""
        try:
            time.sleep(2)  # 等待页面响应
            
            current_url = self.page.url
            
            # 检查URL是否已跳转离开登录页面
            if 'login' not in current_url.lower() and 'accounts.douban.com' not in current_url:
                logger.info(f"登录成功，已跳转到: {current_url}")
                return True
                
            # 检查页面内容是否包含登录成功标识
            content = self.page.content()
            success_indicators = [
                '欢迎', '个人中心', '我的豆瓣', 'logout', '退出',
                'settings', 'profile'
            ]
            
            for indicator in success_indicators:
                if indicator in content.lower():
                    logger.info(f"检测到登录成功标识: {indicator}")
                    return True
                    
            # 如果还在登录页面，检查是否有错误信息
            error_indicators = [
                '密码错误', '用户名不存在', '验证码错误', '登录失败',
                'error', 'incorrect'
            ]
            
            for indicator in error_indicators:
                if indicator in content.lower():
                    logger.error(f"检测到登录错误: {indicator}")
                    return False
                    
            logger.warning("无法确定登录状态，可能需要人工确认")
            return False
            
        except Exception as e:
            logger.error(f"检查登录状态时发生错误: {e}")
            return False
    
    def handle_login(self, auto: bool = True, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        处理登录（支持自动和手动模式）
        
        Args:
            auto: 是否使用自动登录（True=自动，False=手动）
            username: 用户名（仅自动登录时使用）
            password: 密码（仅自动登录时使用）
            
        Returns:
            是否登录成功
        """
        if auto:
            logger.info("尝试自动登录...")
            return self.auto_login(username, password)
        else:
            logger.info("等待手动登录...")
            return self.wait_for_manual_login()
    
    def _check_login_redirect(self, content: str, url: str) -> bool:
        """检查页面中的登录跳转标识（仅处理真正需要登录的页面）"""
        try:
            # 1. 检查域名是否正确（豆瓣相关）
            valid_domains = ['douban.com', 'sec.douban.com', 'accounts.douban.com']
            if not any(domain in url for domain in valid_domains):
                logger.debug(f"URL不在豆瓣域名范围内: {url}")
                return False
            
            # 2. 如果页面中没有登录表单，则跳过处理（只处理真正的登录页面）
            if not self._has_login_form(content):
                logger.debug("页面中没有登录表单，跳过登录处理")
                return False
            
            # 3. 检查是否有登录跳转相关标识且确实有登录表单
            login_redirect_patterns = [
                '登录跳转', 'login redirect', 'redirect to login',
                '请先登录', '需要验证', 'access verification'
            ]
            
            for pattern in login_redirect_patterns:
                if pattern in content:
                    logger.warning(f"检测到登录跳转模式且包含登录表单: {pattern}")
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"登录跳转检测出错: {e}")
            return False

    def _check_login_required_after_redirect(self, content: str, url: str) -> bool:
        """检查跳转后的页面是否真正需要登录处理"""
        try:
            # 1. 检查是否仍在登录页面
            if 'accounts.douban.com/passport/login' in url:
                logger.debug("跳转到真正的登录页面，需要登录处理")
                # 检查是否有实际的登录表单
                if self._has_login_form(content):
                    logger.info("登录页面包含登录表单，需要用户登录")
                    return True
                else:
                    logger.info("登录页面没有登录表单，可能页面加载中...")
                    return False
            
            # 2. 检查是否跳转到其他登录相关页面
            if any(pattern in url.lower() for pattern in ['captcha', 'verification', 'sec.douban.com']):
                if self._has_login_form(content):
                    logger.warning("检测到验证页面需要处理")
                    return True
            
            # 3. 检查是否成功跳转回正常页面
            if 'book.douban.com' in url and not self._has_login_form(content):
                logger.info("成功跳转回正常页面，无需登录")
                return False
            
            # 4. 默认情况下，如果页面包含登录表单则需要处理
            return self._has_login_form(content)
            
        except Exception as e:
            logger.debug(f"跳转后登录检查出错: {e}")
            return False
    
    def _check_normal_login(self, content: str, url: str) -> bool:
        """检查首页/常规页面是否需要登录"""
        # 1. 先检查是否有明确的登录表单（最高优先级）
        login_forms = [
            '<form', 'type="password"', 'name="form_login"',
            'recaptcha', 'geetest', '验证码输入框', 'captcha_input'
        ]
        
        for form_element in login_forms:
            if form_element in content:
                logger.warning(f"检测到登录表单元素: {form_element}")
                return True
        
        # 2. 检查关键登录提示（需要登录的内容）- 但要结合表单验证
        critical_login_patterns = [
            '请先登录', '需要登录', '登录验证', 'unusual traffic',
            '访问限制', '验证失败', '请稍后重试'
        ]
        
        for keyword in critical_login_patterns:
            if keyword in content:
                # 关键提示需要有实际表单支持
                if not self._has_login_form(content):
                    logger.info(f"检测到'{keyword}'提示，但页面中没有登录表单，跳过处理")
                    return False
                logger.warning(f"检测到关键登录提示: {keyword}")
                return True
        
        # 3. 检查是否被重定向到登录URL（但内容必须正常）
        login_url_indicators = ['accounts.douban.com/login', 'accounts.google.com/login']
        if any(indicator in url.lower() for indicator in login_url_indicators):
            if not self._has_login_form(content):
                logger.info(f"检测到登录页面URL但没有登录表单: {url}")
                return False
            logger.warning(f"检测到登录页面URL: {url}")
            return True
        
        # 4. 简化处理：如果只有基本的导航栏登录链接，认为是正常的
        # 检查是否在导航区域
        if '登录' in content or 'login' in content:
            # 检查是否在主要内容区域
            nav_login_in_main = self._is_keyword_in_main_content('登录', content)
            if not nav_login_in_main:
                logger.info("仅在导航区域检测到登录链接，这是正常的")
                return False
            else:
                # 在主要内容区域发现登录，需要进一步判断
                form_keywords = ['登录按钮', '注册按钮', '用户名', '密码']
                if not any(kw in content for kw in form_keywords):
                    logger.info("主要内容区域的'登录'可能只是普通文本，不算登录提示")
                    return False
        
        # 5. 最终检查：页面验证（降低重要性）
        if not self._validate_page_load(content, url):
            logger.warning("页面加载验证失败，可能为非标准页面")
            # 不直接返回True，而是继续检查其他指标
        
        return False
    
    def _validate_page_load(self, content: str, url: str) -> bool:
        """验证页面是否正常加载"""
        try:
            # 1. 基本内容长度检查（大幅降低要求）
            if len(content) < 100:  # 从500降低到100
                logger.warning("页面内容过短，可能未正常加载")
                return False
            
            # 2. 检查是否包含基本的HTML结构
            basic_elements = ['<title>', '<html', '<head>', '<body>']
            has_basic_structure = any(element in content for element in basic_elements)
            
            if not has_basic_structure:
                logger.warning("页面缺少基本HTML结构")
                return False
            
            # 3. 检查是否被重定向到错误页面（这些是真正需要拒绝的）
            error_indicators = [
                '404', '502', '503', '页面不存在', '服务器错误',
                'Error 404', 'Error 502', 'Internal Server Error'
            ]
            
            if any(indicator in content for indicator in error_indicators):
                logger.warning("检测到错误页面")
                return False
            
            # 4. 特殊处理：如果是登录页面或导航栏页面，即使没有豆瓣元素也认为正常
            if ('登录' in content and 'form' in content) or \
               ('login' in content.lower() and 'form' in content.lower()) or \
               ('nav' in content.lower() and '登录' in content):
                logger.info("检测到登录页面或导航页面，跳过元素检查")
                return True
            
            # 5. 对于正常页面，检查是否包含豆瓣相关元素（降低要求）
            douban_elements = ['豆瓣', 'douban', '读书', 'book', 'search', '搜索']
            element_count = sum(1 for element in douban_elements if element in content)
            
            # 只在内容很长时才要求豆瓣元素
            if len(content) > 2000 and element_count < 1:
                logger.warning("长页面缺少豆瓣元素，可能未正常加载")
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"页面验证出错: {e}")
            return True  # 出错时默认返回正常
    
    def _is_keyword_in_main_content(self, keyword: str, content: str) -> bool:
        """检查关键词是否在主要内容区域而非导航栏"""
        try:
            # 尝试找到主要内容区域
            main_content_selectors = [
                '#content', '.subject', '.grid-16-8',
                '.article', '.main', '.book-info'
            ]
            
            for selector in main_content_selectors:
                if selector in content and keyword in content:
                    # 检查关键词是否在主要内容区域
                    start_pos = content.find(selector)
                    if start_pos != -1:
                        # 提取主要内容区域
                        main_section = content[start_pos:start_pos+5000]  # 限制范围
                        if keyword in main_section:
                            return True
            
            # 如果没有找到主要内容区域，检查是否在script或style标签内
            if '<script' in content and keyword in content:
                script_section = content[content.find('<script'):content.find('</script>')+9]
                if keyword in script_section:
                    return False  # 在script中，可能不是真正的登录提示
            
            return True  # 默认认为在主要内容区域
            
        except Exception as e:
            logger.debug(f"主要内容检测出错: {e}")
            return True  # 出错时保守处理
    
    def _check_search_login(self, content: str, url: str) -> bool:
        """检查搜索页面是否需要登录"""
        # 搜索页面的特殊检测
        if '没有找到相关搜索结果' in content or 'not found' in content:
            return False  # 正常搜索结果为空
        
        # 检查是否被重定向到登录
        if 'login' in url.lower() or 'captcha' in url.lower():
            return True
            
        # 搜索页面的登录检测
        search_login_keywords = ['验证码', 'captcha', '请先登录', 'unusual traffic']
        if any(keyword in content for keyword in search_login_keywords):
            return True
            
        return False
    
    def _check_detail_login(self, content: str, url: str) -> bool:
        """检查详情页面是否需要登录"""
        # 详情页面登录检测
        detail_login_keywords = ['登录', '请先登录', '验证码']
        if any(keyword in content for keyword in detail_login_keywords):
            # 进一步检查是否真的无法访问内容
            if '内容简介' not in content and '评分' not in content:
                return True
                
        return False
    
    def wait_for_manual_login(self) -> bool:
        """等待用户手动登录"""
        logger.info("=" * 50)
        logger.info("检测到豆瓣要求登录！")
        logger.info("解决方案:")
        logger.info("1. 浏览器窗口已打开")
        logger.info("2. 请手动登录豆瓣账号")
        logger.info("3. 登录完成后在终端输入 'y' 继续")
        logger.info("=" * 50)
        
        if self.headless:
            logger.error("当前为无头模式，无法进行手动登录。请设置为headless=False")
            return False
            
        try:
            # 保持浏览器窗口打开
            while True:
                try:
                    user_input = input("请确认登录完成后输入 'y' 继续 (或输入 'n' 跳过): ").strip().lower()
                    if user_input == 'y':
                        logger.info("用户确认已完成登录")
                        return True
                    elif user_input == 'n':
                        return False
                    else:
                        logger.info("请输入 'y' 继续或 'n' 跳过")
                except (EOFError, KeyboardInterrupt):
                    # 处理 EOF 错误或用户中断
                    logger.warning("无法获取用户输入，登录流程被中断")
                    return False
                    
        except Exception as e:
            logger.debug(f"手动登录等待过程中发生错误: {e}")
            return False

    def _has_login_form(self, content: str) -> bool:
        """检查页面是否包含登录表单"""
        try:
            login_form_indicators = [
                '<form',
                'type="password"',
                'name="username"',
                'name="password"',
                'name="form_login"',
                'recaptcha',
                'geetest',
                '验证码输入框',
                'captcha_input',
                '用户名',
                '密码'
            ]
            
            for indicator in login_form_indicators:
                if indicator in content:
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"登录表单检测出错: {e}")
            return False

    def _auto_click_login_link(self) -> bool:
        """自动点击登录链接跳转到登录页面"""
        try:
            # 等待页面完全加载
            time.sleep(1)
            
            # 定义可能的登录链接选择器
            login_link_selectors = [
                'a[href*="accounts.douban.com/passport/login"]',
                'a[href*="login"]',
                'text=登录',
                'a:has-text("登录")'
            ]
            
            # 尝试不同的选择器来点击登录链接
            for selector in login_link_selectors:
                try:
                    link = self.page.locator(selector).first
                    if link.is_visible(timeout=3000):
                        logger.info(f"找到登录链接，选择器: {selector}")
                        link.click()
                        logger.info("成功点击登录链接")
                        
                        # 等待页面跳转到登录页面
                        time.sleep(3)
                        
                        # 检查是否成功跳转到登录页面
                        current_url = self.page.url
                        if 'accounts.douban.com/passport/login' in current_url:
                            logger.info(f"成功跳转到登录页面: {current_url}")
                            return True
                        else:
                            logger.warning(f"点击链接后未跳转到预期页面: {current_url}")
                            
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue
            
            logger.warning("无法找到或点击登录链接")
            return False
            
        except Exception as e:
            logger.error(f"自动点击登录链接时发生错误: {e}")
            return False