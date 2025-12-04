"""Playwright网站抓取模块 - 支持动态加载的文章列表监控"""

import re
import yaml
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from src.utils.logger import get_logger
from src.core.content_extractors.factory import ExtractorFactory
# 导入content_extractors模块以注册所有提取器
from src.core.content_extractors import *  # noqa: F401,F403

logger = get_logger(__name__)


class PlaywrightSiteFetcher:
    """Playwright网站抓取器，支持动态加载和滚动加载更多内容"""
    
    def __init__(self, user_agent: Optional[str] = None, headless: bool = True):
        self.user_agent = user_agent or "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
        self.headless = headless
        self.timeout = 30000  # 30秒超时
        
    def fetch_recent_articles(
        self, 
        site_configs: List[Dict[str, Any]], 
        hours_lookback: int = 24,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        抓取多个网站的最新文章
        
        Args:
            site_configs: 网站配置列表
            hours_lookback: 回看小时数
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            文章列表
        """
        articles = []
        
        # 计算时间过滤条件
        cutoff_time = self._calculate_cutoff_time(hours_lookback, start_time, end_time)
        
        for site_config in site_configs:
            if not site_config.get("enabled", True):
                logger.info(f"跳过禁用的网站: {site_config.get('name', 'Unknown')}")
                continue
                
            try:
                logger.info(f"开始抓取网站: {site_config.get('name', 'Unknown')}")
                site_articles = self._fetch_site_articles(site_config, cutoff_time)
                articles.extend(site_articles)
                logger.info(f"网站 {site_config.get('name', 'Unknown')} 抓取完成，获取 {len(site_articles)} 篇文章")
                
            except Exception as e:
                logger.error(f"抓取网站 {site_config.get('name', 'Unknown')} 时出错: {e}")
                continue
        
        logger.info(f"总共获取 {len(articles)} 篇文章")
        return articles
    
    def _calculate_cutoff_time(
        self, 
        hours_lookback: int, 
        start_time: Optional[datetime], 
        end_time: Optional[datetime]
    ) -> datetime:
        """计算时间过滤的截止时间"""
        if start_time:
            return start_time
        elif end_time:
            return end_time - timedelta(hours=hours_lookback)
        else:
            return datetime.now() - timedelta(hours=hours_lookback)
    
    def _fetch_site_articles(self, site_config: Dict[str, Any], cutoff_time: datetime) -> List[Dict[str, Any]]:
        """抓取单个网站的文章"""
        url = site_config.get("url")
        if not url:
            logger.error(f"网站配置缺少URL: {site_config}")
            return []
        
        # 获取网站特定的选择器配置
        selectors = site_config.get("selectors", {})
        
        articles = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 375, "height": 667}  # 模拟手机屏幕
            )
            page = context.new_page()
            
            try:
                # 访问网站
                logger.info(f"访问网站: {url}")
                page.goto(url, timeout=self.timeout)
                
                # 等待页面加载
                page.wait_for_load_state("networkidle", timeout=self.timeout)
                
                # 滚动加载更多内容（模拟用户行为）
                self._scroll_to_load_content(page, site_config)
                
                # 提取文章信息
                articles = self._extract_articles(page, site_config, selectors, url, cutoff_time)
                
            except PlaywrightTimeoutError:
                logger.warning(f"页面加载超时: {url}")
            except Exception as e:
                logger.error(f"抓取网站 {url} 时出错: {e}")
            finally:
                browser.close()
        
        return articles
    
    def _scroll_to_load_content(self, page, site_config: Dict[str, Any]):
        """滚动页面加载更多内容"""
        max_scrolls = site_config.get("scroll_config", {}).get("max_scrolls", 5)
        scroll_delay = site_config.get("scroll_config", {}).get("scroll_delay", 2000)
        
        for i in range(max_scrolls):
            # 滚动到页面底部
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # 等待新内容加载
            page.wait_for_timeout(scroll_delay)
            
            # 检查是否还有更多内容
            try:
                # 查找加载指示器
                loading_selector = site_config.get("selectors", {}).get("loading", ".loading, .spinner, [class*='loading']")
                if page.locator(loading_selector).count() > 0:
                    page.wait_for_selector(loading_selector, state="detached", timeout=5000)
            except:
                pass  # 忽略加载指示器检查错误
    
    def _extract_articles(
        self, 
        page, 
        site_config: Dict[str, Any], 
        selectors: Dict[str, str], 
        base_url: str, 
        cutoff_time: datetime
    ) -> List[Dict[str, Any]]:
        """从页面提取文章信息"""
        articles = []
        
        # 获取文章容器选择器
        article_container_selector = selectors.get("article_container", ".index_wrapper__9rz3z")
        
        # 查找所有文章容器
        article_elements = page.locator(article_container_selector)
        count = article_elements.count()
        
        logger.info(f"找到 {count} 个文章容器")
        
        # 获取当前时间作为fetch_date
        fetch_date = datetime.now()
        
        # 统计过滤情况
        filtered_count = 0
        
        for i in range(count):
            try:
                element = article_elements.nth(i)
                
                # 提取标题
                title = self._extract_title(element, selectors)
                if not title:
                    continue
                
                # 提取链接
                link = self._extract_link(element, selectors, base_url)
                if not link:
                    continue
                
                # 提取时间 - 必须有时间才能过滤
                publish_time = self._extract_time(element, selectors)
                
                # 根据时间过滤文章
                if publish_time:
                    if publish_time < cutoff_time:
                        filtered_count += 1
                        continue  # 跳过时间过旧的文章
                else:
                    # 如果无法解析时间，跳过该文章
                    logger.debug(f"无法解析文章时间，跳过: {title}")
                    continue
                
                # 获取详情页面的准确时间
                accurate_time = self._fetch_article_detail_time(link, page.context)
                if accurate_time:
                    logger.info(f"获取到准确时间: {accurate_time.strftime('%Y-%m-%d %H:%M:%S')} (替换原来的: {publish_time.strftime('%Y-%m-%d %H:%M:%S')})")
                    publish_time = accurate_time
                    
                    # 重新检查时间过滤
                    if publish_time < cutoff_time:
                        logger.info(f"根据准确时间过滤掉文章: {title}")
                        continue
                
                # 提取来源
                source = site_config.get("name", "Unknown Source")
                
                # 构建符合Excel列要求的文章数据
                article = {
                    "source": source,
                    "title": title,
                    "article_date": publish_time.strftime("%Y-%m-%d") if publish_time else "",
                    "link": link,
                    "published_date": publish_time.strftime("%Y-%m-%d %H:%M:%S") if publish_time else "",
                    "fetch_date": fetch_date.strftime("%Y-%m-%d %H:%M:%S"),
                    # 保留其他字段用于后续处理
                    "fetch_method": "playwright",
                    "category": site_config.get("category", ""),
                    "summary": "",
                    "full_text": "",
                    "author": "",
                    "tags": []
                }
                
                # 如果配置了extractor，调用提取器获取全文
                extractor_name = site_config.get("extractor")
                if extractor_name is not None and extractor_name != "":
                    article = self._apply_extractor(article, extractor_name, source)
                
                articles.append(article)
                
            except Exception as e:
                logger.warning(f"提取第 {i+1} 个文章时出错: {e}")
                continue
        
        if filtered_count > 0:
            logger.info(f"根据时间过滤掉 {filtered_count} 篇文章（早于 {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}）")
        
        return articles
    
    def _extract_title(self, element, selectors: Dict[str, str]) -> Optional[str]:
        """提取文章标题"""
        # 澎湃手机端：标题在 .index_title__aGAqD 中
        title_selector = selectors.get("title", "h3")
        try:
            title_element = element.locator(title_selector).first
            if title_element.count() > 0:
                return title_element.inner_text().strip()
        except:
            pass
        
        # 备用选择器
        fallback_selectors = ["h3", "h2", ".title", "[class*='title']", "a"]
        for selector in fallback_selectors:
            try:
                title_element = element.locator(selector).first
                if title_element.count() > 0:
                    text = title_element.inner_text().strip()
                    if text and len(text) > 3:  # 确保不是空文本
                        return text
            except:
                continue
        
        return None
    
    def _extract_link(self, element, selectors: Dict[str, str], base_url: str) -> Optional[str]:
        """提取文章链接"""
        link_selector = selectors.get("link", "a")
        try:
            link_element = element.locator(link_selector).first
            if link_element.count() > 0:
                href = link_element.get_attribute("href")
                if href:
                    return urljoin(base_url, href)
        except:
            pass
        
        # 备用选择器
        fallback_selectors = ["a[href]", "a"]
        for selector in fallback_selectors:
            try:
                link_element = element.locator(selector).first
                if link_element.count() > 0:
                    href = link_element.get_attribute("href")
                    if href:
                        return urljoin(base_url, href)
            except:
                continue
        
        return None
    
    def _extract_time(self, element, selectors: Dict[str, str]) -> Optional[datetime]:
        """提取文章发布时间"""
        # 澎湃手机端：时间在 .adm-space-item 下的 span 中
        # HTML结构: <div class="adm-space-item"><span>19小时前</span></div>
        time_selector = selectors.get("time", ".adm-space-item span")
        
        logger.debug(f"开始提取时间...")
        
        try:
            # 尝试获取所有span元素，更精确地识别时间信息
            time_elements = element.locator(".adm-space-item span")
            count = time_elements.count()
            
            logger.debug(f"找到 {count} 个 span 元素")
            
            for i in range(count):
                time_text = time_elements.nth(i).inner_text().strip()
                logger.debug(f"检查第 {i+1} 个span元素: '{time_text}'")
                
                # 更精确的时间识别：检查是否包含时间关键词且不是其他信息
                if any(keyword in time_text for keyword in ["小时前", "分钟前", "天前", "刚刚"]):
                    # 排除明显不是时间的文本（如评论数等）
                    if not any(exclude in time_text for exclude in ["评", "评论", "阅读", "次"]):
                        logger.debug(f"识别到时间文本: {time_text}")
                        publish_time = self._parse_relative_time(time_text)
                        if publish_time:
                            logger.debug(f"解析时间成功: {publish_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            return publish_time
                    else:
                        logger.debug(f"跳过非时间文本: {time_text}")
        except Exception as e:
            logger.debug(f"提取时间时出错: {e}")
        
        # 备用方案：使用配置的选择器
        try:
            time_element = element.locator(time_selector).first
            if time_element.count() > 0:
                time_text = time_element.inner_text().strip()
                logger.debug(f"备用方案检查时间文本: '{time_text}'")
                
                if any(keyword in time_text for keyword in ["小时前", "分钟前", "天前", "刚刚"]):
                    publish_time = self._parse_relative_time(time_text)
                    if publish_time:
                        logger.debug(f"备用方案解析时间成功: {publish_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        return publish_time
        except:
            pass
        
        logger.debug("未能提取到有效时间")
        return None
    
    def _parse_relative_time(self, time_text: str) -> Optional[datetime]:
        """解析相对时间文本（如"19小时前"）"""
        if not time_text:
            logger.debug("时间文本为空")
            return None
        
        logger.debug(f"开始解析时间文本: '{time_text}'")
        
        # 使用当前UTC时间作为基准，避免时区问题
        now = datetime.utcnow()
        logger.debug(f"当前UTC时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 匹配小时前
        hour_match = re.search(r'(\d+)小时前', time_text)
        if hour_match:
            hours = int(hour_match.group(1))
            result_time = now - timedelta(hours=hours)
            logger.debug(f"解析为 {hours} 小时前: {result_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return result_time
        
        # 匹配分钟前
        minute_match = re.search(r'(\d+)分钟前', time_text)
        if minute_match:
            minutes = int(minute_match.group(1))
            result_time = now - timedelta(minutes=minutes)
            logger.debug(f"解析为 {minutes} 分钟前: {result_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return result_time
        
        # 匹配天前
        day_match = re.search(r'(\d+)天前', time_text)
        if day_match:
            days = int(day_match.group(1))
            result_time = now - timedelta(days=days)
            logger.debug(f"解析为 {days} 天前: {result_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return result_time
        
        # 匹配"刚刚"
        if "刚刚" in time_text:
            logger.debug("解析为刚刚")
            return now
        
        # 匹配今天、昨天等
        if "今天" in time_text:
            # 假设"今天"就是当前日期的00:00
            result_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            logger.debug(f"解析为今天: {result_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return result_time
        
        if "昨天" in time_text:
            # 假设"昨天"是当前日期前一天的00:00
            result_time = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            logger.debug(f"解析为昨天: {result_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return result_time
        
        logger.debug(f"无法解析时间文本: {time_text}")
        return None
    
    def _fetch_article_detail_time(self, article_url: str, context) -> Optional[datetime]:
        """
        打开文章链接，获取详情页面的准确时间
        
        Args:
            article_url: 文章链接
            context: 浏览器上下文
            
        Returns:
            准确的文章发布时间
        """
        try:
            # 创建新页面
            page = context.new_page()
            
            logger.debug(f"打开文章链接获取准确时间: {article_url}")
            
            # 访问文章页面
            page.goto(article_url, timeout=self.timeout)
            
            # 等待页面加载完成
            page.wait_for_load_state("networkidle", timeout=self.timeout)
            
            # 提取详情页面的准确时间
            accurate_time = self._extract_detail_page_time(page)
            
            # 关闭页面
            page.close()
            
            return accurate_time
            
        except PlaywrightTimeoutError:
            logger.warning(f"文章页面加载超时: {article_url}")
            return None
        except Exception as e:
            logger.warning(f"获取文章详情时间时出错 {article_url}: {e}")
            return None
    
    def _extract_detail_page_time(self, page) -> Optional[datetime]:
        """
        从文章详情页面提取准确的发布时间
        
        Args:
            page: 页面对象
            
        Returns:
            准确的文章发布时间
        """
        try:
            # 根据提供的HTML结构，查找 .ant-space-item span 中的时间
            # 格式类似: "2025-12-03 15:22"
            
            # 尝试多种选择器来获取时间
            time_selectors = [
                ".ant-space-item span",  # 详情页面的时间选择器
                ".index_left__LfzyH .ant-space-item span",  # 更精确的选择器
                "[class*='ant-space'] span",  # 备用选择器
                "span"  # 通用选择器作为最后备选
            ]
            
            for selector in time_selectors:
                try:
                    time_elements = page.locator(selector)
                    count = time_elements.count()
                    
                    for i in range(count):
                        time_text = time_elements.nth(i).inner_text().strip()
                        
                        # 检查是否是时间格式 (YYYY-MM-DD HH:MM)
                        if self._is_valid_date_time_format(time_text):
                            logger.debug(f"在选择器 {selector} 中找到时间: {time_text}")
                            return self._parse_absolute_time(time_text)
                        
                except Exception as e:
                    logger.debug(f"选择器 {selector} 提取时间失败: {e}")
                    continue
            
            logger.debug("未能从详情页面提取到有效时间")
            return None
            
        except Exception as e:
            logger.debug(f"提取详情页时间时出错: {e}")
            return None
    
    def _is_valid_date_time_format(self, time_text: str) -> bool:
        """
        检查文本是否为有效的日期时间格式
        
        Args:
            time_text: 时间文本
            
        Returns:
            是否为有效的时间格式
        """
        if not time_text:
            return False
        
        # 匹配 YYYY-MM-DD HH:MM 格式
        pattern = r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$'
        return bool(re.match(pattern, time_text.strip()))
    
    def _parse_absolute_time(self, time_text: str) -> Optional[datetime]:
        """
        解析绝对时间文本（如"2025-12-03 15:22"）
        
        Args:
            time_text: 绝对时间文本
            
        Returns:
            解析后的datetime对象
        """
        if not time_text:
            return None
        
        try:
            # 解析 YYYY-MM-DD HH:MM 格式
            # 用户提供的例子：2025-12-03 15:22
            dt = datetime.strptime(time_text.strip(), "%Y-%m-%d %H:%M")
            logger.debug(f"成功解析时间: {time_text} -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            return dt
        except ValueError as e:
            logger.debug(f"时间解析失败: {time_text} - {e}")
            return None
    
    def _apply_extractor(self, article: Dict[str, Any], extractor_name: str, source_name: str = "") -> Dict[str, Any]:
        """
        应用提取器获取文章全文
        
        Args:
            article: 文章数据字典
            extractor_name: 提取器名称
            source_name: 源名称，用于匹配提取器
            
        Returns:
            更新后的文章数据字典
        """
        try:
            # 优先使用指定的extractor_name，否则根据source_name自动匹配
            extractor = None
            
            if extractor_name:
                # 直接通过类名查找提取器
                for registered_extractor in ExtractorFactory._extractors:
                    class_name = registered_extractor.__class__.__name__
                    # 移除"Extractor"后缀进行比较
                    if class_name.lower().replace("extractor", "") == extractor_name.lower():
                        extractor = registered_extractor
                        logger.debug(f"通过名称匹配到提取器: {class_name}")
                        break
                
                # 如果名称匹配失败，尝试通过source_name匹配
                if not extractor:
                    logger.warning(f"未找到名称为 '{extractor_name}' 的提取器，尝试通过源名称匹配")
                    extractor = ExtractorFactory.get_extractor(source_name)
            else:
                # 如果没有指定extractor_name，根据source_name自动匹配
                extractor = ExtractorFactory.get_extractor(source_name)
            
            if not extractor:
                logger.warning(f"未找到适合的提取器 (extractor_name: {extractor_name}, source_name: {source_name})")
                return article
            
            logger.info(f"为文章 '{article.get('title')}' 应用提取器: {extractor.__class__.__name__}")
            
            # 调用提取器
            extract_result = extractor.extract(article)
            
            # 更新文章数据
            if extract_result.get("extract_status") == "success":
                article["full_text"] = extract_result.get("full_text", "")
                article["extract_status"] = "success"
                logger.info(f"提取器 {extractor.__class__.__name__} 成功提取全文 (长度: {len(article['full_text'])})")
            else:
                article["extract_status"] = "failed"
                article["extract_error"] = extract_result.get("extract_error", "未知错误")
                logger.warning(f"提取器 {extractor.__class__.__name__} 提取失败: {article['extract_error']}")
                
        except Exception as e:
            logger.error(f"应用提取器时出错: {e}")
            article["extract_status"] = "error"
            article["extract_error"] = str(e)
        
        return article


def load_playwright_sites_config(config_path: str = "config/subject_bibliography.yaml") -> List[Dict[str, Any]]:
    """从配置文件加载playwright网站配置"""
    if not os.path.exists(config_path):
        logger.warning(f"配置文件未找到: {config_path}")
        return []
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        
        return config.get("playwright_sites", [])
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return []