import asyncio
import json
from playwright.async_api import async_playwright, TimeoutError

async def get_paper_info(page, paper_element):
    """
    从单个文献元素中提取标题和链接
    """
    try:
        link_element = await paper_element.query_selector('h4 > a')
        if not link_element:
            return None, None
        
        title = await link_element.inner_text()
        relative_url = await link_element.get_attribute('href')
        
        if not relative_url:
            return title, None

        full_url = f"https://openreview.net{relative_url}"
        return title, full_url
        
    except Exception as e:
        print(f"提取标题和链接时出错: {e}")
        return None, None

async def get_abstract(page, url):
    """
    打开文献详情页并提取摘要 (更健壮的版本)
    """
    try:
        # 增加页面加载超时时间
        await page.goto(url, wait_until='domcontentloaded', timeout=15000)
        
        # 方法1: 尝试通过XPath定位摘要
        abstract_locator = page.locator('//div[contains(@class, "note-content-field") and contains(., "Abstract:")]/following-sibling::div[contains(@class, "note-content-value")]')
        
        # 方法2: 备用定位策略
        backup_locator = page.locator('div.note-content-value.markdown-rendered')
        
        # 等待任一元素出现
        try:
            await abstract_locator.or_(backup_locator).wait_for(timeout=15000)
        except TimeoutError:
            return "无法找到摘要元素（超时）。"
        
        # 尝试获取摘要文本
        if await abstract_locator.is_visible():
            abstract_text = await abstract_locator.inner_text()
        elif await backup_locator.is_visible():
            abstract_text = await backup_locator.inner_text()
        else:
            return "摘要元素不可见。"
        
        return abstract_text.strip()
            
    except Exception as e:
        return f"无法提取摘要: {e}"

async def main():
    """
    主函数，用于执行爬虫任务
    """
    papers_data = []
    url = "https://openreview.net/group?id=wikimedia.it/Wikidata_and_Research/2025/Conference"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context() # 使用context来管理页面
        page = await context.new_page()
        
        try:
            print(f"正在访问: {url}")
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_selector('ul.list-unstyled.list-paginated li', timeout=10000)
            
            paper_elements = await page.query_selector_all('ul.list-unstyled.list-paginated > li')
            print(f"找到 {len(paper_elements)} 篇文献。")

            for i, paper_element in enumerate(paper_elements):
                title, paper_url = await get_paper_info(page, paper_element)
                
                if title and paper_url:
                    print(f"\n正在处理第 {i+1} 篇: {title}")
                    print(f"链接: {paper_url}")
                    
                    paper_page = await context.new_page()
                    abstract = await get_abstract(paper_page, paper_url)
                    await paper_page.close()
                    
                    print(f"摘要: {abstract[:100].replace(chr(10), ' ')}...") # 打印摘要前100个字符预览, 并替换换行符
                    
                    papers_data.append({
                        "title": title,
                        "url": paper_url,
                        "abstract": abstract
                    })

        except Exception as e:
            print(f"处理主页面时发生错误: {e}")
        finally:
            await browser.close()
            
    with open('wikidata_research_papers_updated.json', 'w', encoding='utf-8') as f:
        json.dump(papers_data, f, ensure_ascii=False, indent=4)
        
    print("\n爬取完成！数据已保存至 'wikidata_research_papers_updated.json'")

if __name__ == "__main__":
    asyncio.run(main())