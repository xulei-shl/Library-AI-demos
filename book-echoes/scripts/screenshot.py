"""
HTML to PNG Screenshot Script
使用 Playwright 库将 HTML 文件转换为图片（支持完整 CSS，包括 Grid）
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def screenshot_html(
    html_file: str,
    output_file: str = "output.png",
    width: int = 1200,
    height: int = 800,
    device_scale_factor: float = 1.0,
    browser_type: str = "chromium",
    headless: bool = True
):
    """
    使用 Playwright 将 HTML 文件转换为图片

    Args:
        html_file: HTML 文件路径
        output_file: 输出图片路径
        width: 浏览器视口宽度
        height: 浏览器视口高度
        device_scale_factor: 设备像素比 (DPI)，1.0=标准, 2.0=高清
        browser_type: 浏览器类型 'chromium', 'firefox', 'webkit'
    """
    # 获取 HTML 文件的绝对路径
    html_path = Path(html_file).resolve()

    async with async_playwright() as p:
        # 选择浏览器
        browser_launcher = getattr(p, browser_type)

        # 启动浏览器（添加系统字体支持）
        browser = await browser_launcher.launch(
            headless=headless,
            args=[
                '--font-render-hinting=medium',
                '--disable-font-subpixel-positioning',
            ]
        )

        # 创建页面并设置视口大小 + 设备像素比
        page = await browser.new_page(
            viewport={
                'width': width,
                'height': height,
                'device_scale_factor': device_scale_factor
            }
        )

        # 加载 HTML 文件
        await page.goto(f"file:///{html_path}")

        # 等待页面加载完成（包括字体、样式）
        await page.wait_for_load_state('networkidle')
        await page.wait_for_load_state('domcontentloaded')

        # 额外等待确保字体渲染完成
        await page.wait_for_timeout(500)

        # 截图（使用更高画质）
        await page.screenshot(
            path=output_file,
            # full_page=False,  # 只截取视口区域
            # type='png',       # 默认 PNG
        )

        # 关闭浏览器
        await browser.close()

    print(f"Screenshot saved to: {output_file}")


async def screenshot_from_string(
    html_content: str,
    css_content: str = "",
    output_file: str = "output.png",
    width: int = 1200,
    height: int = 800
):
    """
    从 HTML 字符串转换为图片

    Args:
        html_content: HTML 内容字符串
        css_content: CSS 内容字符串（可选）
        output_file: 输出图片路径
        width: 浏览器视口宽度
        height: 浏览器视口高度
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={'width': width, 'height': height}
        )

        # 构建完整的 HTML
        if css_content:
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>{css_content}</style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
        else:
            full_html = html_content

        await page.set_content(full_html)
        await page.wait_for_load_state('networkidle')
        await page.screenshot(path=output_file)
        await browser.close()

    print(f"Screenshot saved to: {output_file}")


async def main():
    """主函数"""
    # 截图指定的 HTML 文件
    html_file = "54121109949172.html"
    output_file = "54121109949172.png"

    # 使用 device_scale_factor=1.0 或 2.0 匹配你的浏览器
    # Windows 通常默认是 1.0，Mac Retina 是 2.0
    # headless=False 可以看到浏览器窗口，方便调试
    await screenshot_html(
        html_file,
        output_file,
        width=1200,
        height=800,
        device_scale_factor=1.0,  # 试试 1.0 或 2.0
        headless=False  # 改为 True 则不显示浏览器窗口
    )


if __name__ == "__main__":
    asyncio.run(main())
