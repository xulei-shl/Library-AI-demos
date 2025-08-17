import time
import threading
import random
from playwright.sync_api import sync_playwright
from datetime import datetime
import pandas as pd
import os
from unit.log_crawl import log_crawl_info
from config_manager import ConfigManager

# 全局变量管理浏览器会话和状态
_browser_session = None
_search_completed = False
_search_results_count = 0
_session_lock = threading.Lock()

def get_browser_config():
    """生成随机的浏览器配置"""
    # 常见的用户代理列表
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"
    ]
    
    # 常见的视口尺寸
    viewports = [
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1440, 'height': 900},
        {'width': 1536, 'height': 864},
        {'width': 1680, 'height': 1050}
    ]
    
    # 随机选择
    user_agent = random.choice(user_agents)
    viewport = random.choice(viewports)
    
    return {
        'user_agent': user_agent,
        'viewport': viewport
    }

def random_sleep(base_time=1, variance=0.5):
    """随机等待时间，基于基础时间加减一定变化量"""
    sleep_time = base_time + random.uniform(-variance, variance)
    # 确保不会出现负数
    sleep_time = max(0.1, sleep_time)
    time.sleep(sleep_time)

def natural_click(page, selector):
    """模拟自然的点击行为"""
    # 先移动到元素上
    element = page.locator(selector)
    if element.count() > 0:
        # 获取元素的边界框
        box = element.bounding_box()
        if box:
            # 移动到元素中心位置
            page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
            # 短暂停顿
            random_sleep(0.3, 0.2)
            # 点击
            element.click()
            return True
    return False

def reset_global_state():
    """重置全局状态"""
    global _browser_session, _search_completed, _search_results_count
    with _session_lock:
        _cleanup_browser_session()
        _search_completed = False
        _search_results_count = 0
        print("全局状态已重置")

def cnki_pre_search(keyword, start_year=None, end_year=None, check_core=False, stop_check=None, output_path="data"):
    """预检索函数：执行搜索并返回结果数量，但不保持会话"""
    global _browser_session, _search_completed, _search_results_count
    
    with _session_lock:
        # 从配置文件获取默认设置
        config_manager = ConfigManager()
        default_settings = config_manager.get_default_settings()
        
        # 优先使用传入的参数，如果参数为None才使用配置文件
        if start_year is None and end_year is None:
            time_range = default_settings.get('time_range', 'recent_year')
            
            if time_range == 'recent_year':
                start_year = None
                end_year = None
                print("使用配置: 最近一年")
            else:
                start_year = default_settings.get('start_year')
                end_year = default_settings.get('end_year')
                print(f"使用配置: 自定义年份范围 {start_year}-{end_year}")
        else:
            if start_year or end_year:
                print(f"使用传入参数: 自定义年份范围 {start_year}-{end_year}")
            else:
                print("使用传入参数: 最近一年")
        
        if check_core is False and 'check_core' in default_settings:
            check_core = default_settings.get('check_core', False)
        
        # 重置状态并清理之前的会话
        _search_completed = False
        _search_results_count = 0
        _cleanup_browser_session()
        
        # Initialize browser
        try:
            page, browser, context, playwright = webserver()
        except Exception as e:
            print(f"初始化浏览器失败: {e}")
            _search_completed = False
            _search_results_count = 0
            raise e
        
        try:
            # 检查停止标志
            if stop_check and stop_check():
                raise Exception("用户停止操作")
            
            # 打开页面并搜索，只执行到获取计数
            # ### MODIFIED ###: 传入 set_per_page=False 来跳过设置每页条数的步骤
            res_unm = open_page_with_stop(page, keyword, start_year, end_year, check_core, stop_check, set_per_page=False)
            
            if res_unm == 0:
                print("没有找到相关结果")
                _search_results_count = 0
                _search_completed = True
                return 0
            
            _search_results_count = res_unm
            _search_completed = True
            print(f"预检索完成，找到 {res_unm} 条结果")
            return res_unm
            
        except Exception as e:
            # 如果出错，重置状态
            _search_completed = False
            _search_results_count = 0
            raise e
        finally:
            # 总是清理浏览器会话，不保持会话
            try:
                context.close()
                browser.close()
                playwright.stop()
            except Exception as e:
                print(f"清理浏览器会话时出错: {e}")

def cnki_continue_crawl(stop_check=None, output_path="data", max_results=100):
    """继续爬取函数：重新创建浏览器会话并完成爬取"""
    global _browser_session, _search_completed, _search_results_count
    
    with _session_lock:
        if not _search_completed:
            raise Exception("请先执行预检索")
        
        # 清理旧的浏览器会话
        _cleanup_browser_session()
        
        try:
            # 检查停止标志
            if stop_check and stop_check():
                raise Exception("用户停止操作")
            
            # 从配置文件获取默认设置
            config_manager = ConfigManager()
            default_settings = config_manager.get_default_settings()
            
            if max_results is None:
                max_results = default_settings.get('max_results', 60)
            
            # 获取保存的搜索参数
            keyword = default_settings.get('keyword', '')
            time_range = default_settings.get('time_range', 'recent_year')
            check_core = default_settings.get('check_core', False)
            
            if time_range == 'recent_year':
                start_year = None
                end_year = None
            else:
                start_year = default_settings.get('start_year')
                end_year = default_settings.get('end_year')
            
            print(f"🔄 继续爬取过程...")
            print(f"重新创建浏览器会话...")
            
            # 重新初始化浏览器
            page, browser, context, playwright = webserver()
            
            # 重新执行搜索到结果页面
            # ### MODIFIED ###: 传入 set_per_page=True 和 max_results 参数
            res_unm = open_page_with_stop(page, keyword, start_year, end_year, check_core, stop_check, set_per_page=True, max_results=max_results)
            
            if res_unm == 0:
                print("重新搜索时没有找到结果")
                return 0
            
            # 继续爬取流程：选择所有结果并导出
            selected_count = select_all_and_export_with_stop(
                page, res_unm, "继续爬取", max_results, stop_check, output_path
            )
            print(f"成功选择 {selected_count} 条结果并导出")
            
            # 记录日志到输出文件夹下
            if output_path:
                log_folder = output_path
            else:
                log_folder = os.path.join(os.path.dirname(__file__), 'data')
            os.makedirs(log_folder, exist_ok=True)
            log_crawl_info(keyword, start_year, end_year, res_unm, selected_count, log_folder)
            
            return selected_count
            
        except Exception as e:
            print(f"继续爬取过程中出现错误: {e}")
            raise e
        finally:
            # 清理浏览器会话
            try:
                if 'context' in locals():
                    context.close()
                if 'browser' in locals():
                    browser.close()
                if 'playwright' in locals():
                    playwright.stop()
            except Exception as e:
                print(f"清理浏览器会话时出错: {e}")

def _cleanup_browser_session():
    """清理浏览器会话"""
    global _browser_session, _search_completed, _search_results_count
    
    if _browser_session:
        try:
            if 'context' in _browser_session and _browser_session['context']:
                _browser_session['context'].close()
        except Exception as e:
            print(f"关闭浏览器上下文时出错: {e}")
        try:
            if 'browser' in _browser_session and _browser_session['browser']:
                _browser_session['browser'].close()
        except Exception as e:
            print(f"关闭浏览器时出错: {e}")
        try:
            if 'playwright' in _browser_session and _browser_session['playwright']:
                _browser_session['playwright'].stop()
        except Exception as e:
            print(f"停止Playwright时出错: {e}")
        
        _browser_session = None

def webserver():
    """初始化浏览器"""
    p = sync_playwright().start()
    
    # 获取随机浏览器配置
    browser_config = get_browser_config()
    
    browser = p.chromium.launch(
        headless=True,
        slow_mo=random.randint(800, 1200),  # 随机慢动作时间
        devtools=False
    )
    context = browser.new_context(
        accept_downloads=True,
        viewport=browser_config['viewport'],  # 随机视口尺寸
        user_agent=browser_config['user_agent'],  # 设置随机UA
        # 添加常见的浏览器headers
        extra_http_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
    )
    context.route("**/*.{png,jpg,jpeg}", lambda route: route.abort())
    page = context.new_page()
    page.set_default_timeout(30000)
    return page, browser, context, p

# ### MODIFIED ###: 添加新参数 set_per_page，默认为 True，以及 max_results 参数用于判断
def open_page_with_stop(page, keyword, start_year=None, end_year=None, check_core=False, stop_check_func=None, set_per_page=True, max_results=None):
    """带停止检查功能的页面打开函数"""
    try:
        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")
            
        page.goto("https://kns.cnki.net/kns8s/AdvSearch?classid=YSTT4HG0", wait_until="domcontentloaded")
        random_sleep(2, 0.5)

        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")

        keyword_input = page.locator('//*[@id="gradetxt"]/dd[1]/div[2]/input')
        keyword_input.fill(keyword)
        
        synonym_checkbox = page.locator('//input[@data-id="TY"]')
        synonym_checkbox.check()

        use_recent_year = not start_year and not end_year
        
        if use_recent_year:
            try:
                natural_click(page, '.tit-dropdown-box .sort-default')
                random_sleep(1, 0.3)
                page.evaluate('''() => {
                    const links = document.querySelectorAll('.sort-list li a');
                    for (const link of links) {
                        if (link.textContent.trim() === '最近一年') {
                            link.click();
                            break;
                        }
                    }
                }''')
            except Exception as e:
                print(f"设置最近一年选项失败: {e}")
        else:
            if start_year:
                start_year_input = page.locator("input[placeholder='起始年']")
                start_year_input.fill(str(start_year))
            if end_year:
                end_year_input = page.locator("input[placeholder='结束年']")
                end_year_input.fill(str(end_year))

        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")

        if check_core:
            try:
                checkboxes = [
                    ('//label/input[@key="SI"]', 'SCI'),
                    ('//label/input[@key="EI"]', 'EI'),
                    ('//label/input[@key="CSD"]', 'CSCD'),
                    ('//label/input[@key="AMI"]', 'AMI'),
                    ('//label/input[@key="HX"]', '北大核心'),
                    ('//label/input[@key="CSI"]', 'CSSCI')
                ]
                for selector, name in checkboxes:
                    try:
                        checkbox = page.locator(selector)
                        if checkbox.count() > 0:
                            checkbox.check()
                    except Exception as e:
                        print(f"勾选{name}失败: {e}")
            except Exception as e:
                print(f"设置核心期刊选项失败: {e}")

        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")

        search_button = page.locator('//input[@class="btn-search"]')
        natural_click(page, '//input[@class="btn-search"]')
        print("正在搜索，请稍后...")
        
        try:
            random_sleep(2, 0.5)
            popup = page.locator('.layui-layer-dialog')
            if popup.count() > 0:
                print("检测到弹窗，正在处理...")
                confirm_button = page.locator('.layui-layer-btn0')
                if confirm_button.count() > 0:
                    natural_click(page, '.layui-layer-btn0')
                    print("已点击确认按钮关闭弹窗")
                    random_sleep(1, 0.3)
        except Exception as e:
            print(f"处理弹窗时出错: {e}")
        
        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")
        
        random_sleep(3, 0.7)
        
        try:
            no_content = page.locator('#ModuleSearchResult .no-content')
            if no_content.count() > 0:
                content_text = no_content.inner_text()
                if "暂无数据" in content_text:
                    print("搜索结果为空：暂无数据，请稍后重试。")
                    return 0
        except Exception as e:
            pass
        
        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")
        
        # 获取总结果数 (先获取结果数量，用于判断是否需要设置每页条数)
        res_unm = 0
        try:
            random_sleep(2, 0.5)
            selectors = [
                '//*[@id="countPageDiv"]/span[1]/em',
                '.pagerTitleCell em',
                '#countPageDiv em',
                '.pagerTitleCell .countPageMark',
                '.pagerTitleCell span em'
            ]
            
            for selector in selectors:
                try:
                    res_unm_element = page.locator(selector)
                    if res_unm_element.count() > 0:
                        res_unm_text = res_unm_element.inner_text().replace(",", "").replace("，", "").strip()
                        if res_unm_text.isdigit():
                            res_unm = int(res_unm_text)
                            break
                except:
                    continue
            
            if res_unm == 0:
                if page.locator('.result-table-list').count() > 0 or page.locator('.fz14').count() > 0:
                    print("检测到搜索结果列表，但无法获取精确数量")
                    res_unm = 1
                else:
                    print("未检测到搜索结果")
                    return 0
                    
        except Exception as e:
            print(f"获取结果数量时出错: {e}")
            return 0
        
        # 获取最大结果数用于判断
        if max_results is None:
            try:
                config_manager = ConfigManager()
                max_results = config_manager.get_setting("default_settings", "max_results", 60)
            except:
                max_results = 60
        
        # 判断是否需要设置每页显示50条：只有当结果数量和最大下载数量都大于20时才设置
        need_set_per_page = set_per_page and res_unm > 20 and max_results > 20
        
        if need_set_per_page:
            print(f"检索结果 {res_unm} 条，最大下载 {max_results} 条，正在设置每页显示50条...")
            try:
                page.wait_for_selector('#perPageDiv', timeout=10000)
                random_sleep(1, 0.3)
                
                dropdown_clicked = False
                try:
                    natural_click(page, '#perPageDiv .sort-default')
                    dropdown_clicked = True
                    random_sleep(1, 0.3)
                except:
                    print("点击每页显示下拉框失败，尝试其他方法")
                
                if dropdown_clicked:
                    selectors_50 = [
                        'ul.sort-list li[data-val="50"] a',
                        'ul.sort-list li a:has-text("50")',
                        '.sort-list a[data-val="50"]'
                    ]
                    
                    selected = False
                    for selector in selectors_50:
                        try:
                            element = page.locator(selector)
                            if element.count() > 0:
                                natural_click(page, selector)
                                selected = True
                                print("成功设置每页显示50条")
                                random_sleep(2, 0.5)
                                break
                        except:
                            continue
                    
                    if not selected:
                        print("无法找到50条选项，使用默认设置")
                
            except Exception as e:
                print(f"设置每页显示条数失败: {e}")
        elif set_per_page:
            print(f"检索结果 {res_unm} 条，最大下载 {max_results} 条，数量较少，跳过设置每页显示条数")
        
        # 计算并显示页数信息
        if res_unm > 0:
            if need_set_per_page:
                page_unm = int(res_unm / 50) + 1
                print(f"共找到 {res_unm} 条结果，{page_unm} 页（每页50条）。")
            else:
                page_unm = int(res_unm / 20) + 1  # 默认每页20条
                print(f"共找到 {res_unm} 条结果，{page_unm} 页（每页20条）。")
        
        return res_unm
            
    except Exception as e:
        print(f"页面操作出错: {e}")
        raise e

def select_all_and_export_with_stop(page, total_results, selected_topic, max_results=None, stop_check_func=None, output_path=None):
    """带停止检查功能的选择和导出函数"""
    try:
        # 从配置文件获取最大结果数
        if max_results is None:
            config_manager = ConfigManager()
            max_results = config_manager.get_setting("default_settings", "max_results", 60)
        
        selected_count = 0
        current_page = 1
        
        while selected_count < total_results and selected_count < max_results:
            # 检查停止标志
            if stop_check_func and stop_check_func():
                raise Exception("用户停止操作")
                
            # 等待页面加载完成
            try:
                page.wait_for_selector('#selectCheckAll1', timeout=10000)
                random_sleep(2, 0.5)
            except:
                print("等待全选按钮超时")
                break
            
            # 检查停止标志
            if stop_check_func and stop_check_func():
                raise Exception("用户停止操作")
            
            # 点击全选
            try:
                natural_click(page, '#selectCheckAll1')
                random_sleep(1, 0.3)
            except Exception as e:
                print(f"点击全选失败: {e}")
                break
            
            # 获取当前选中数量
            try:
                select_count_text = page.locator('#selectCount').inner_text()
                selected_count = int(select_count_text)
                print(f"当前已选择 {selected_count} 条")
            except:
                selected_count += 50  # 估算值
                print(f"估算已选择 {selected_count} 条")
            
            # 如果已选数量超过最大限制，直接退出循环
            if selected_count >= max_results:
                print(f"已达到最大选择数量 {max_results} 条，停止翻页")
                break
                
            # 如果还有下一页且未选择完所有结果
            if selected_count < total_results and selected_count < max_results:
                try:
                    next_page = page.locator("//a[@id='PageNext']")
                    if next_page.count() > 0 and "disabled" not in next_page.get_attribute("class"):
                        # 检查停止标志
                        if stop_check_func and stop_check_func():
                            raise Exception("用户停止操作")
                            
                        natural_click(page, "//a[@id='PageNext']")
                        current_page += 1
                        print(f"翻到第 {current_page} 页")
                        random_sleep(3, 0.7)  # 等待页面加载
                    else:
                        break
                except Exception as e:
                    print(f"翻页失败: {e}")
                    break
        
        # 检查停止标志
        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")
        
        # 导出流程
        return _export_results(page, selected_count, output_path, stop_check_func)
        
    except Exception as e:
        print(f"选择和导出过程出错: {e}")
        raise e

def _export_results(page, selected_count, output_path, stop_check_func):
    """导出结果的具体实现"""
    try:
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
        random_sleep(1, 0.3)
        
        # 检查停止标志
        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")
        
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
        random_sleep(1, 0.3)
        
        # 检查停止标志
        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")
        
        # 点击自定义
        page.evaluate('''() => {
            const exportLinks = document.querySelectorAll('a[exporttype="selfDefine"]');
            if (exportLinks.length > 0) {
                exportLinks[0].click();
            }
        }''')
        print("准备下载论文元数据")
        random_sleep(2, 0.5)
        
        # 检查停止标志
        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")
        
        # 等待新页面加载并处理导出
        return _handle_export_popup(page, output_path, stop_check_func)
        
    except Exception as e:
        print(f"导出过程出错: {e}")
        raise e

def _handle_export_popup(page, output_path, stop_check_func):
    """处理导出弹窗"""
    max_retries = 3
    retry_count = 0
    new_page = None
    
    while retry_count < max_retries:
        try:
            # 检查停止标志
            if stop_check_func and stop_check_func():
                raise Exception("用户停止操作")
                
            # 等待弹窗出现，增加超时时间
            with page.expect_popup(timeout=20000) as popup_info:
                random_sleep(3, 0.7)
            
            # 获取新页面并等待加载完成
            new_page = popup_info.value
            
            # 确保新页面完全加载
            new_page.wait_for_load_state('domcontentloaded', timeout=20000)
            random_sleep(2, 0.5)
            new_page.wait_for_load_state('networkidle', timeout=20000)
            
            # 在新页面中等待并点击全选按钮
            new_page.wait_for_selector('.check-labels', timeout=20000)
            random_sleep(2, 0.5)
            break
            
        except Exception as e:
            if stop_check_func and stop_check_func():
                raise Exception("用户停止操作")
            retry_count += 1
            print(f"等待导出页面加载超时，正在进行第 {retry_count} 次重试...")
            if retry_count >= max_retries:
                raise Exception("重试次数已达上限，导出页面加载失败") from e
            random_sleep(3, 0.7)
    
    try:
        # 检查停止标志
        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")
        
        # 确保页面元素可用
        if not new_page:
            raise Exception("导出页面未正确加载")
            
        # 点击全选按钮
        new_page.evaluate('''() => {
            const allButton = document.querySelector('.check-labels .row-btns a');
            if (allButton && allButton.textContent.trim() === '全选') {
                allButton.click();
                return true;
            }
            return false;
        }''')
        random_sleep(2, 0.5)
        
        # 检查停止标志
        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")
        
        # 监听下载事件并点击导出xls，增加超时时间
        try:
            with new_page.expect_download(timeout=45000) as download_info:
                new_page.evaluate('''() => {
                    const xlsButton = document.querySelector('#litoexcel');
                    if (xlsButton) {
                        xlsButton.click();
                        return true;
                    }
                    return false;
                }''')
            
            # 等待下载完成
            download = download_info.value
            print("正在下载文件...")
            
            # 使用GUI设置的输出路径，如果没有设置则使用默认路径
            if output_path:
                output_folder = output_path
            else:
                output_folder = os.path.join(os.path.dirname(__file__), 'data')
            
            os.makedirs(output_folder, exist_ok=True)
            
            # 保存文件
            filename = f'CNKI_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xls'
            filepath = os.path.join(output_folder, filename)
            download.save_as(filepath)
            print(f"文件下载完成！保存在: {filepath}")
            
            return 1  # 返回成功导出的标志
            
        except Exception as download_error:
            print(f"下载过程出错: {download_error}")
            raise download_error
        
    except Exception as e:
        print(f"处理导出弹窗出错: {e}")
        raise e
    finally:
        # 确保关闭新页面
        try:
            if new_page:
                new_page.close()
        except:
            pass

# 保持向后兼容的函数
def select_all_and_export(page, total_results, selected_topic, max_results=None, output_path=None):
    """原始的选择和导出函数，保持向后兼容"""
    return select_all_and_export_with_stop(page, total_results, selected_topic, max_results, None, output_path)

def open_page(page, keyword, start_year=None, end_year=None, check_core=False):
    """原始的页面打开函数，保持向后兼容"""
    # 默认行为是设置每页条数
    return open_page_with_stop(page, keyword, start_year, end_year, check_core, None, set_per_page=True)

def cnki_spider_with_stop(selected_topic, start_year=None, end_year=None, check_core=False, stop_check_func=None, output_path=None):
    """带停止检查功能的CNKI爬虫"""
    keyword = selected_topic
    
    config_manager = ConfigManager()
    default_settings = config_manager.get_default_settings()
    
    if start_year is None and end_year is None:
        time_range = default_settings.get('time_range', 'recent_year')
        if time_range == 'recent_year':
            start_year = None
            end_year = None
            print("使用配置: 最近一年")
        else:
            start_year = default_settings.get('start_year')
            end_year = default_settings.get('end_year')
            print(f"使用配置: 自定义年份范围 {start_year}-{end_year}")
    else:
        if start_year or end_year:
            print(f"使用传入参数: 自定义年份范围 {start_year}-{end_year}")
        else:
            print("使用传入参数: 最近一年")
    
    if check_core is False and 'check_core' in default_settings:
        check_core = default_settings.get('check_core', False)
    
    page, browser, context, playwright = webserver()
    
    try:
        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")
        
        # ### MODIFIED ###: 传入 set_per_page=True 和 max_results 参数
        max_results = default_settings.get('max_results', 60)
        res_unm = open_page_with_stop(page, keyword, start_year, end_year, check_core, stop_check_func, set_per_page=True, max_results=max_results)
        if res_unm == 0:
            print("没有找到相关结果")
            if output_path:
                log_folder = output_path
            else:
                log_folder = os.path.join(os.path.dirname(__file__), 'data')
            os.makedirs(log_folder, exist_ok=True)
            log_crawl_info(selected_topic, start_year, end_year, 0, 0, log_folder)
            return
            
        if stop_check_func and stop_check_func():
            raise Exception("用户停止操作")
            
        max_results = default_settings.get('max_results', 60)
        selected_count = select_all_and_export_with_stop(page, res_unm, selected_topic, max_results, stop_check_func, output_path)
        print(f"成功选择 {selected_count} 条结果并导出")
        
        if output_path:
            log_folder = output_path
        else:
            log_folder = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(log_folder, exist_ok=True)
        log_crawl_info(selected_topic, start_year, end_year, res_unm, selected_count, log_folder)
        
    finally:
        try:
            context.close()
            browser.close()
            playwright.stop()
        except:
            pass

def cnki_spider(selected_topic, start_year=None, end_year=None, check_core=False, output_path=None):
    """原始的CNKI爬虫函数，保持向后兼容"""
    return cnki_spider_with_stop(selected_topic, start_year, end_year, check_core, None, output_path)

if __name__ == "__main__":
    config_manager = ConfigManager()
    default_settings = config_manager.get_default_settings()
    
    selected_topic = default_settings.get('keyword', '智能体 图书馆')
    start_year = default_settings.get('start_year', '2024')
    end_year = default_settings.get('end_year', '2025')
    check_core = default_settings.get('check_core', False)
    
    print(f"使用配置文件设置: 关键词='{selected_topic}', 年份={start_year}-{end_year}, 核心期刊={check_core}")
    cnki_spider(selected_topic, start_year, end_year, check_core)