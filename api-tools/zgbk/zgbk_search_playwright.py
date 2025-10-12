import json
import sys
import argparse
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Force UTF-8 output to reduce Windows console mojibake
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def perform_search(query: str, headless: bool = True, timeout: int = 20000):
    """
    Search https://www.zgbk.com for the given query, and return a list of dicts:
    { "title": str, "url": str, "summary": str }
    """
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://www.zgbk.com", wait_until="domcontentloaded", timeout=timeout)
        # Wait for network quiescence to ensure page scripts are ready
        try:
            page.wait_for_load_state("networkidle", timeout=timeout)
        except PlaywrightTimeoutError:
            pass

        # Try desktop search input first (#search2), then mobile (#search1)
        search_selector = None
        try:
            page.wait_for_selector("input#search2.search-query", timeout=3000, state="visible")
            search_selector = "input#search2.search-query"
        except PlaywrightTimeoutError:
            page.wait_for_selector("input#search1.search-query", timeout=3000, state="visible")
            search_selector = "input#search1.search-query"

        # Ensure input is focused before submitting
        page.focus(search_selector)
        page.fill(search_selector, query)

        # Prefer clicking the visible desktop search button; fall back to Enter
        clicked = False
        for selector in [
            ".searchbox .search .search-submit[alias='all']",
            "span.search-submit.enterclick[alias='all']",
            "span.search-submit[alias='all']"
        ]:
            try:
                btn = page.locator(selector).first
                btn.scroll_into_view_if_needed()
                try:
                    btn.wait_for(state="visible", timeout=1500)
                except PlaywrightTimeoutError:
                    pass
                btn.click(timeout=2000, force=True)
                clicked = True
                break
            except Exception:
                continue

        if not clicked:
            # Try element-scoped Enter press first, then global as fallback
            try:
                page.press(search_selector, "Enter")
                clicked = True
            except Exception:
                page.keyboard.press("Enter")

        # Allow navigation/render to proceed
        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except PlaywrightTimeoutError:
            pass

        # Wait for results page to render with multiple fallbacks
        # Use several stable signals commonly present on the results page
        for sel in [
            "body.search_result",
            "div.search-wrap",
            "span.searchlen",
            "ul#test li",
            "ul.part-list li"
        ]:
            try:
                page.wait_for_selector(sel, timeout=5000)
                break
            except PlaywrightTimeoutError:
                continue

        # Additional guard: wait until URL or DOM indicates search results
        try:
            page.wait_for_function(
                "document.body.classList.contains('search_result') || document.querySelector('ul#test li') !== null",
                timeout=timeout
            )
        except PlaywrightTimeoutError:
            pass

        # Fallback: if results container still not present, try direct navigation with common query param names
        if not page.query_selector("ul#test li"):
            try:
                from urllib.parse import quote
                base = "https://www.zgbk.com/ecph/advanceSearch/result?SiteID=1&Alias=all"
                candidates = [
                    f"{base}&Query={quote(query)}",
                    f"{base}&searchWord={quote(query)}",
                    f"{base}&q={quote(query)}",
                    f"{base}&keyword={quote(query)}",
                ]
                for url in candidates:
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                        try:
                            page.wait_for_load_state("networkidle", timeout=timeout)
                        except PlaywrightTimeoutError:
                            pass
                        try:
                            page.wait_for_selector("ul#test li", timeout=5000)
                            break
                        except PlaywrightTimeoutError:
                            continue
                    except Exception:
                        continue
            except Exception:
                pass

        # Debug: capture the current URL after attempting to submit search
        try:
            current_url = page.url
        except Exception:
            current_url = ""
        # Emit URL to stderr for troubleshooting when zero results occur
        try:
            sys.stderr.write(f"[zgbk] current_url={current_url}\n")
        except Exception:
            pass

        # Fallback: if results container isn't present, navigate to Advanced Search page and submit there
        if not page.query_selector("ul#test li"):
            try:
                # Navigate to advanced search result page (all aliases)
                page.goto("https://www.zgbk.com/ecph/advanceSearch/result?SiteID=1&Alias=all", wait_until="domcontentloaded", timeout=timeout)
                try:
                    page.wait_for_load_state("networkidle", timeout=timeout)
                except PlaywrightTimeoutError:
                    pass

                # Path A: Header search box on advanced search results page
                try:
                    page.wait_for_selector("input#search.search-query", timeout=3000, state="visible")
                    page.fill("input#search.search-query", query)
                    # Click header search submit
                    try:
                        page.click("span.search-submit[alias='all']", timeout=2000)
                    except PlaywrightTimeoutError:
                        # Force click if needed
                        page.locator("span.search-submit[alias='all']").first.click(timeout=2000, force=True)
                except PlaywrightTimeoutError:
                    pass

                # Path B: Right-side "在结果中搜索" box as backup
                if not page.query_selector("ul#test li"):
                    try:
                        page.wait_for_selector("input#searchIpt.searchIpt", timeout=3000, state="visible")
                        page.fill("input#searchIpt.searchIpt", query)
                        # Click the '确定' button inside the right-side search box
                        try:
                            page.click(".search.input-group .searchbox .search-submit", timeout=2000)
                        except PlaywrightTimeoutError:
                            page.locator(".search.input-group .searchbox .search-submit").first.click(timeout=2000, force=True)
                    except PlaywrightTimeoutError:
                        pass

                # Final wait for results list
                page.wait_for_selector("ul#test li", timeout=timeout)
            except Exception:
                # If any step fails, continue to extraction (may yield empty)
                pass

        # Extract results from the list
        for li in page.query_selector_all("ul#test li"):
            a = li.query_selector("a.font20.search-title")
            title = a.inner_text().strip() if a else ""
            href = a.get_attribute("href") if a else ""
            href = urljoin(page.url, href) if href else ""
            content = li.query_selector("div.content")
            summary = content.inner_text().strip() if content else ""
            results.append({"title": title, "url": href, "summary": summary})

        # Fallback: if no results captured from #test, try generic container
        if not results:
            for li in page.query_selector_all("ul.part-list li"):
                a = li.query_selector("a.font20.search-title")
                title = a.inner_text().strip() if a else ""
                href = a.get_attribute("href") if a else ""
                href = urljoin(page.url, href) if href else ""
                content = li.query_selector("div.content")
                summary = content.inner_text().strip() if content else ""
                if title or href or summary:
                    results.append({"title": title, "url": href, "summary": summary})

        # If still empty, capture artifacts for diagnostics
        if not results:
            try:
                page.screenshot(path="scripts/zgbk_search.png", full_page=True)
            except Exception:
                pass
            try:
                html = page.content()
                with open("scripts/zgbk_search.html", "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception:
                pass

        browser.close()
    return results
def main():
    parser = argparse.ArgumentParser(description="Search zgbk.com and extract title, url, summary.")
    parser.add_argument("--query", "-q", default="卡尔登大戏院", help="Search query text")
    parser.add_argument("--headed", action="store_true", help="Run in headed (non-headless) mode")
    parser.add_argument("--timeout", type=int, default=20000, help="Timeout in ms for page operations")
    parser.add_argument("--out", type=str, help="Save JSON output to the specified file path (UTF-8)")
    args = parser.parse_args()

    try:
        data = perform_search(args.query, headless=(not args.headed), timeout=args.timeout)
        output = {"query": args.query, "count": len(data), "results": data}
        text = json.dumps(output, ensure_ascii=False, indent=2)

        # Write to file if requested
        if args.out:
            try:
                with open(args.out, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception:
                # Even if file write fails, still print to stdout
                pass

        # Always print to stdout
        print(text)
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()