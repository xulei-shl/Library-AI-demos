#!/usr/bin/env python3
import json
import sys
import argparse
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Force UTF-8 stdout/stderr (Windows safe)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

DEFAULT_URL = "https://www.zgbk.com/ecph/words?SiteID=1&ID=124008"


def extract_entry(url: str, headless: bool = True, timeout: int = 30000) -> dict:
    """
    访问中国大百科全书（zgbk.com）条目页面，提取两类信息：
    - basic_info: 条目作者、最后更新、浏览、英文名称、成立时间、成立地点、所属学科
    - entry_content: 条目正文段落（不包含“相关条目”“精选发现”等）
    返回结构化字典。
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/119.0.0.0 Safari/537.36")
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        try:
            page.wait_for_load_state("networkidle", timeout=timeout)
        except PlaywrightTimeoutError:
            pass

        # 等待页面关键内容出现（多重兜底）
        for sel in [
            "text=条目作者",
            "text=英文名称",
            "text=成立时间",
            "text=所属学科",
            "h1"
        ]:
            try:
                page.wait_for_selector(sel, timeout=4000)
                break
            except PlaywrightTimeoutError:
                continue

        # 使用页面脚本提取“基本信息”
        labels_js = r"""
 () => {
   // 通用工具
   const text = (el) => (el && (el.innerText || el.textContent) || '').replace(/\s+/g, ' ').trim();
   const found = {};
   const addPair = (k, v) => {
     if (!k) return;
     k = k.replace(/[：:]\s*$/, '').trim();
     if (!k) return;
     // 过滤不需要的字段
     if (k.includes('条目作者') || k === '浏览' || k.startsWith('浏览')) return;
     if (!v) return;
     // 过滤明显的导航/模板噪声
     const navRe = /个人中心|机构中心|登录|注册|专题|板块|高级搜索|退出|返回|{{#for|{{\/for}}|{{item/i;
     if (navRe.test(v)) return;
     // 避免超长段落误入（如正文内容误判为“英文名称”等）
     if (v.length > 200) {
       const sCount = (v.match(/[。！？]/g) || []).length;
       if (sCount >= 2) return; // 更像正文，跳过
     }
     found[k] = v.trim();
   };

   // 1) 解析所有 dl/dt/dd 结构
   document.querySelectorAll('dl').forEach(dl => {
     Array.from(dl.children).forEach((node, idx, arr) => {
       if (node.tagName && node.tagName.toLowerCase() === 'dt') {
         const k = text(node);
         const nxt = arr[idx + 1];
         if (nxt && nxt.tagName && nxt.tagName.toLowerCase() === 'dd') {
           addPair(k, text(nxt));
         }
       }
     });
   });

   // 2) 解析表格：每行前一列为键，后一列为值
   document.querySelectorAll('table').forEach(t => {
     Array.from(t.rows).forEach(tr => {
       const cells = Array.from(tr.cells || []);
       if (cells.length >= 2) {
         const k = text(cells[0]);
         const v = text(cells[1]);
         if (k && v && k.length <= 10) addPair(k, v);
       }
     });
   });

   // 3) 解析列表项中使用 冒号 分隔的键值
   document.querySelectorAll('ul,ol').forEach(list => {
     list.querySelectorAll('li').forEach(li => {
       const t = text(li);
       if (!t) return;
       const m = t.match(/^(.{1,12}?)[：:]\s*(.+)$/);
       if (m) addPair(m[1], m[2]);
     });
   });

   // 4) 解析相邻元素作为 键/值 的布局（常见于自定义布局）
   document.querySelectorAll('div,section').forEach(container => {
     const children = Array.from(container.children || []);
     for (let i = 0; i < children.length - 1; i++) {
       const a = children[i], b = children[i + 1];
       if (!a || !b || !a.tagName || !b.tagName) continue;
       const ka = text(a);
       const vb = text(b);
       // 中文2-8字的键，后面紧跟一个值
       if (/^[\u4e00-\u9fa5]{2,12}$/.test(ka) && vb && vb.length <= 120) {
         addPair(ka, vb);
       }
     }
   });

   // 标题提取：h1 优先，其次 og:title，最后 document.title 去站点后缀
   let title = '';
   const titleEl =
     document.querySelector('h1.wordTitle, .wordTitle h1, .detail-title h1, .detail_title h1, .conTit h1, .conTitle h1, .title h1, h1');
   if (titleEl) title = text(titleEl);
   if (!title) {
     const og = document.querySelector('meta[property="og:title"]');
     if (og) title = (og.getAttribute('content') || '').trim();
   }
   if (!title) {
     let dt = (document.title || '').replace(/[\s\u00A0]+/g, ' ').trim();
     dt = dt.replace(/\s*[-—|｜]\s*中国大百科全书.*$/,'')
            .replace(/\s*[-—|｜]\s*百科.*$/,'')
            .replace(/\s*[_-]\s*zgbk.*$/i,'')
            .trim();
     title = dt;
   }
   return {found, title};
 }
 """

        bi = page.evaluate(labels_js)

        # 使用页面脚本提取“条目内容”段落
        content_js = r"""
 () => {
   const stopHeadings = ["相关条目","精选发现","条目图册","目录","条目引用","参考资料","参考文献","注释","查看更多"];
   const navRe = /个人中心|机构中心|登录|注册|专题|板块|高级搜索|退出|返回|{{#for|{{\/for}}|{{item|分享到|微信|QQ空间|微博/i;
   const isStop = (t) => stopHeadings.some(h => t.includes(h));
   const text = (el) => (el && (el.innerText || el.textContent) || '').replace(/\s+/g,' ').trim();
   const isVisible = (el) => {
     if (!el) return false;
     const style = window.getComputedStyle(el);
     if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
     if (el.offsetParent === null && style.position !== 'fixed') return false;
     return true;
   };
   const inExcludedContainer = (el) => {
     while (el) {
       if (!el.tagName) break;
       const tn = el.tagName.toLowerCase();
       const cls = (el.className || '').toString();
       if (['nav','header','footer','aside'].includes(tn)) return true;
       if (/(side|sidebar|right|aside|nav|menu)/i.test(cls)) return true;
       el = el.parentElement;
     }
     return false;
   };

   // 候选容器（包含常见正文类名），无匹配时回退 body
   const candidateSelector = [
     'article',
     '.article','[class*="article"]',
     '.detail, .detail-con, .detail_con, [class*="detail"]',
     '.word-con, .word_con, .wordContent, [class*="word"]',
     '.content, .con, .conTxt, .con_text, .left-con, .leftContent, .mainContent, [class*="content"], [class*="con"]',
     '#content, #main, #left, #leftContent'
   ].join(',');
   let candidates = Array.from(document.querySelectorAll(candidateSelector));
   if (!candidates.length) candidates = [document.body];

   // 评分：正文样的段落越多越好，含导航词的容器惩罚，忽略不可见或侧栏等容器
   let best = null;
   let bestScore = -1;
   for (const c of candidates) {
     if (!c || inExcludedContainer(c)) continue;
     const ps = c.querySelectorAll('p, section, div');
     let len = 0, cnt = 0, navPenalty = 0;
     ps.forEach(p => {
       if (!isVisible(p)) return;
       const t = text(p);
       if (!t) return;
       if (isStop(t)) return;
       if (navRe.test(t)) { navPenalty += 50; return; }
       const hasPunct = /[。！？；]/.test(t);
       const zh = /[\u4e00-\u9fa5]/.test(t);
       if ((hasPunct && zh && t.length >= 20) || t.length >= 60) { len += t.length; cnt++; }
     });
     const score = len + cnt * 50 - navPenalty;
     if (score > bestScore) { bestScore = score; best = c; }
   }

   const paras = [];
   if (best) {
     const nodes = best.querySelectorAll('p, div, section');
     for (const el of nodes) {
       if (!isVisible(el)) continue;
       if (inExcludedContainer(el)) continue;
       const tn = el.tagName.toLowerCase();
       if (!["p","section","div"].includes(tn)) continue;
       const t = text(el);
       if (!t) continue;
       if (isStop(t)) continue; // 到达“相关条目”等标题则停止
       if (navRe.test(t)) continue;
       if (/^(最后更新|浏览\s*\d+|条目作者)/.test(t)) continue; // 过滤基本信息行
       // 仅保留像正文的中文段落
       const zh = /[\u4e00-\u9fa5]/.test(t);
       const hasPunct = /[。！？；]/.test(t);
       if ((zh && t.length >= 20) || (hasPunct && t.length >= 20)) {
         paras.push(t);
       }
     }
   }

   const out = [];
   const seen = new Set();
   for (const p of paras) {
     const k = p.slice(0, 60);
     if (seen.has(k)) continue;
     seen.add(k);
     out.push(p);
     if (out.length >= 200) break;
   }
   return out;
 }
 """

        paragraphs = page.evaluate(content_js)

        result = {
            "url": url,
            "title": (bi.get("title") or "").strip() if isinstance(bi, dict) else "",
            "basic_info": {},
            "entry_content": paragraphs if isinstance(paragraphs, list) else []
        }

        if isinstance(bi, dict) and isinstance(bi.get("found"), dict):
            # 过滤掉不需要的键：条目作者、浏览
            found = dict(bi["found"])
            for k in list(found.keys()):
                if ("条目作者" in k) or k.startswith("浏览"):
                    found.pop(k, None)

            # basic_info 子节点噪音数据处理：
            # (1) 只要出现“条目图册”，不管是键还是值，该节点删除
            # (2) 同样，出现“首页”的也全部删除
            # (3) 键名中包含特殊符号（如书名号、全角点号、各类标点等）的子节点删除（例如：“田本相．曹禺剧作论．北京”）
            cleaned = {}
            # 定义“特殊符号”识别的正则：匹配常见中文/全角/半角标点
            _special_key_re = re.compile(r"[．。，、；：:《》“”\"'（）()【】—\-·!！?？]")
            for k, v in list(found.items()):
                # 删除键或值中包含“条目图册”
                if ("条目图册" in k) or (isinstance(v, str) and ("条目图册" in v)):
                    continue
                # 删除键或值中包含“首页”
                if ("首页" in k) or (isinstance(v, str) and ("首页" in v)):
                    continue
                # 删除“键名”含特殊符号的子节点（多为文献信息/噪音）
                if isinstance(k, str) and _special_key_re.search(k):
                    continue
                cleaned[k] = v
            found = cleaned

            # 规则 (1)：如果连续1个子节点的取值与后一个子节点的名称相同，则这两个节点全部删除
            items = list(found.items())
            to_delete = set()
            for i in range(len(items) - 1):
                k1, v1 = items[i]
                k2, v2 = items[i + 1]
                if isinstance(v1, str) and v1.strip() == k2.strip():
                    to_delete.add(i)
                    to_delete.add(i + 1)
            items = [items[j] for j in range(len(items)) if j not in to_delete]

            # 从第一个取值为 "." 的节点开始，删除直到 basic_info 末尾
            cut_idx = next((i for i, (_, v) in enumerate(items) if isinstance(v, str) and v.strip() == "."), None)
            if cut_idx is not None:
                items = items[:cut_idx]
            found = dict(items)
            result["basic_info"] = found

        # 强化清洗：移除空段落、导航/模板噪声、版权与面包屑、纯链接列表、以及误混入的基本信息行
        cleaned = []
        nav_noise = [
            "个人中心","机构中心","登录","注册","专题","板块","高级搜索","退出","返回",
            "首页","总编委会","学科编委会","关于我们","三版介绍"
        ]
        template_noise = ["{{#for","{{/for}}","{{item"]
        copyright_noise = ["版权所有","Copyrights","京ICP备","京公网安备"]
        basic_info_keys = ["条目作者","英文名称","成立时间","成立地点","所属学科"]

        def is_link_list(s: str) -> bool:
            # 无标点、以空格分隔的词条列表，且词条数量较多时判为噪声
            if re.search(r"[。！？；，,.;:]", s):
                return False
            tokens = [t for t in s.split() if t]
            if len(tokens) >= 6:
                zh_chars = len(re.findall(r"[\u4e00-\u9fa5]", s))
                return zh_chars >= 20
            return False

        for ptxt in result["entry_content"]:
            pt = (ptxt or "").strip()
            if not pt:
                continue
            low = pt.lower()
            # 版权与备案信息
            if low.startswith("copyrights") or any(x in pt for x in copyright_noise):
                continue
            # 导航与模板噪声
            if any(x in pt for x in nav_noise):
                continue
            if any(x in pt for x in template_noise):
                continue
            # 多义词提示噪声
            if "是一个多义词" in pt:
                continue
            # 误混入的基本信息键值
            if any(x in pt for x in basic_info_keys):
                continue
            # 纯链接/标签列表
            if is_link_list(pt):
                continue
            cleaned.append(pt)

        # 额外清洗：若首段以“·”开头（多为学科标签的导航），移除首段
        if cleaned and re.match(r'^[\s\u00A0]*[·]', cleaned[0]):
            cleaned.pop(0)

        result["entry_content"] = cleaned

        # 规范化标题：去除站点后缀
        if result.get("title"):
            t = result["title"]
            t = re.sub(r"\s*[-—|｜]\s*《?中国大百科全书[^》]*》?第三版网络版$", "", t).strip()
            t = re.sub(r"\s*[-—|｜]\s*中国大百科全书.*$", "", t).strip()
            result["title"] = t

        browser.close()
        return result


def main():
    parser = argparse.ArgumentParser(description="抓取zgbk条目页面的基本信息与正文内容，并输出为JSON。")
    parser.add_argument("--url", default=DEFAULT_URL, help="条目URL")
    parser.add_argument("--headed", action="store_true", help="以可见窗口模式运行（默认无头）")
    parser.add_argument("--timeout", type=int, default=30000, help="页面操作超时时间(ms)")
    parser.add_argument("--out", type=str, help="将结果保存到指定JSON文件（UTF-8）")

    args = parser.parse_args()
    try:
        data = extract_entry(args.url, headless=(not args.headed), timeout=args.timeout)
        text = json.dumps(data, ensure_ascii=False, indent=2)

        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(text)
        print(text)
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()