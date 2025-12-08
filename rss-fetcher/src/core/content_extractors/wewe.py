# -*- coding: utf-8 -*-
"""微信公众号全文提取器"""

import re
import pandas as pd
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from src.utils.logger import get_logger
from .base import BaseContentExtractor

logger = get_logger(__name__)


class WeweExtractor(BaseContentExtractor):
    """微信公众号全文提取器"""

    def __init__(self):
        self.timeout = 30000  # 30秒超时
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    def can_handle(self, source_name: str) -> bool:
        """判断是否能处理该RSS源"""
        # 处理包含微信公众号关键词的源
        wechat_keywords = ["微信公众号", "wewe", "公众号", "weixin", "信睿周刊"]
        return any(keyword in source_name.lower() for keyword in wechat_keywords)

    def extract(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取微信公众号文章全文

        Args:
            article: 包含 source, title, link, content 等字段的字典

        Returns:
            包含以下字段的字典:
            - full_text: 提取的全文内容
            - extract_status: 提取状态 (success/failed/skipped)
            - extract_error: 错误信息(如有)
        """
        link = article.get("link", "")
        title = article.get("title", "")

        if not link:
            return {
                "full_text": "",
                "extract_status": "failed",
                "extract_error": "链接为空"
            }

        try:
            logger.info(f"开始提取微信公众号文章: {title}")
            full_text = self._extract_wechat_content(link)

            if full_text:
                logger.info(f"成功提取文章全文，长度: {len(full_text)} 字符")
                return {
                    "full_text": full_text,
                    "extract_status": "success",
                    "extract_error": ""
                }
            else:
                logger.warning(f"未能提取到文章内容: {title}")
                return {
                    "full_text": "",
                    "extract_status": "failed",
                    "extract_error": "未能提取到文章内容"
                }

        except Exception as e:
            logger.error(f"提取文章时出错 {title}: {e}")
            return {
                "full_text": "",
                "extract_status": "failed",
                "extract_error": str(e)
            }

    def _extract_wechat_content(self, url: str) -> Optional[str]:
        """
        使用Playwright提取微信公众号文章内容

        Args:
            url: 文章链接

        Returns:
            文章全文内容，提取失败返回None
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.user_agent,
                    viewport={"width": 1200, "height": 800}
                )
                page = context.new_page()

                try:
                    logger.info(f"访问微信公众号文章: {url}")
                    page.goto(url, timeout=self.timeout)

                    # 等待页面加载完成
                    page.wait_for_load_state("networkidle", timeout=self.timeout)

                    # 微信公众号文章的主要内容选择器
                    content_selectors = [
                        "#js_content",  # 微信公众号文章主容器
                        ".rich_media_content",  # 备用选择器
                        ".content",  # 通用内容容器
                        "article"  # HTML5 article标签
                    ]

                    content = ""

                    for selector in content_selectors:
                        try:
                            content_element = page.locator(selector)
                            if content_element.count() > 0:
                                content = content_element.inner_text()
                                if content and len(content.strip()) > 100:  # 确保内容足够长
                                    logger.info(f"使用选择器 {selector} 成功提取内容")
                                    break
                        except Exception as e:
                            logger.debug(f"选择器 {selector} 提取失败: {e}")
                            continue

                    # 如果没有找到内容，尝试获取页面所有文本
                    if not content or len(content.strip()) < 100:
                        logger.warning("主要选择器未找到内容，尝试获取页面正文")
                        # 尝试获取body内的文本，排除导航和侧边栏
                        body_text = page.evaluate("""
                            () => {
                                const unwantedSelectors = ['header', 'footer', 'nav', 'aside', '.sidebar', '.menu', '.navigation'];
                                unwantedSelectors.forEach(selector => {
                                    const elements = document.querySelectorAll(selector);
                                    elements.forEach(el => el.style.display = 'none');
                                });
                                return document.body.innerText || document.body.textContent || '';
                            }
                        """)
                        content = body_text

                    # 清理文本内容
                    if content:
                        content = self._clean_content(content)

                    return content if content else None

                except PlaywrightTimeoutError:
                    logger.error(f"页面加载超时: {url}")
                    return None
                except Exception as e:
                    logger.error(f"提取页面内容时出错: {e}")
                    return None
                finally:
                    browser.close()

        except Exception as e:
            logger.error(f"初始化Playwright时出错: {e}")
            return None

    def _clean_content(self, content: str) -> str:
        """
        清理提取的文本内容

        Args:
            content: 原始文本内容

        Returns:
            清理后的文本内容
        """
        if not content:
            return ""

        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content)

        # 移除常见的无用文本
        useless_patterns = [
            r'点击.*?关注.*?[。！]',
            r'长按.*?二维码.*?[。！]',
            r'扫码.*?关注.*?[。！]',
            r'更多.*?请关注.*?[。！]',
            r'本文.*?不代表.*?观点.*?[。！]',
            r'免责声明.*?[。！]',
            r'投稿.*?联系.*?[。！]',
        ]

        for pattern in useless_patterns:
            content = re.sub(pattern, '', content)

        # 清理首尾空白
        content = content.strip()

        return content


def extract_wechat_articles_from_excel(excel_path: str, output_path: Optional[str] = None) -> bool:
    """
    从Excel文件中提取微信公众号文章全文

    Args:
        excel_path: Excel文件路径
        output_path: 输出文件路径，如果为None则覆盖原文件

    Returns:
        是否成功
    """
    try:
        # 读取Excel文件
        logger.info(f"读取Excel文件: {excel_path}")
        df = pd.read_excel(excel_path)

        if df.empty:
            logger.warning("Excel文件为空")
            return False

        # 检查必要列
        if 'link' not in df.columns:
            logger.error("Excel文件缺少 'link' 列")
            return False

        # 初始化提取器
        extractor = WeweExtractor()

        # 统计信息
        total_count = len(df)
        success_count = 0
        failed_count = 0

        logger.info(f"开始处理 {total_count} 篇文章")

        # 处理每一行
        for index, row in df.iterrows():
            link = row.get('link', '')
            title = row.get('title', f'第{index+1}篇文章')
            source = row.get('source', '')

            # 跳过没有链接的文章
            if not link or pd.isna(link):
                logger.info(f"跳过无链接文章: {title}")
                df.at[index, 'extract_status'] = 'skipped'
                df.at[index, 'extract_error'] = '无链接'
                continue

            # 检查是否已经提取过全文
            current_full_text = row.get('full_text', '')
            if current_full_text and len(str(current_full_text).strip()) > 100:
                logger.info(f"跳过已提取全文的文章: {title}")
                df.at[index, 'extract_status'] = 'already_extracted'
                continue

            logger.info(f"处理文章 {index+1}/{total_count}: {title}")

            # 构建文章数据
            article = {
                'source': source,
                'title': title,
                'link': link,
                'content': ''
            }

            # 提取全文
            result = extractor.extract(article)

            # 更新DataFrame
            df.at[index, 'full_text'] = result['full_text']
            df.at[index, 'extract_status'] = result['extract_status']
            df.at[index, 'extract_error'] = result['extract_error']

            # 统计
            if result['extract_status'] == 'success':
                success_count += 1
                logger.info(f"✓ 成功提取: {title} (长度: {len(result['full_text'])})")
            else:
                failed_count += 1
                logger.warning(f"✗ 提取失败: {title} - {result['extract_error']}")

        # 保存结果
        output_file = output_path if output_path else excel_path
        df.to_excel(output_file, index=False)

        logger.info(f"处理完成! 成功: {success_count}, 失败: {failed_count}")
        logger.info(f"结果已保存到: {output_file}")

        return True

    except Exception as e:
        logger.error(f"处理Excel文件时出错: {e}")
        return False


if __name__ == "__main__":
    # 示例用法
    excel_file = "runtime/outputs/2025-12.xlsx"
    extract_wechat_articles_from_excel(excel_file)