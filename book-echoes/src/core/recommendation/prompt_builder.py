from typing import Dict, List
from .config import recommend_quota

def build_book_block(book: Dict) -> str:
    lines = [
        f"书目条码id:{book.get('书目条码','')}",
        f"书名:{book.get('书名','')}",
        f"副标题:{book.get('豆瓣副标题','')}",
        f"作者:{book.get('豆瓣作者','')}",
        f"丛书:{book.get('豆瓣丛书','')}",
        f"内容简介:{book.get('豆瓣内容简介','')}",
        f"作者简介:{book.get('豆瓣作者简介','')}",
        f"目录:{book.get('豆瓣目录','')}",
    ]
    return "\n".join(lines)

def build_initial_prompt(theme: str, books: List[Dict]) -> str:
    quota = recommend_quota(len(books))
    header = f"主题:{theme}\n在所有符合条件的书籍中，请精中选优，最终推荐的书目数量不得超过 {quota} 本。"
    blocks = [build_book_block(b) for b in books]
    return header + "\n\n" + "\n---\n".join(blocks)

def build_final_prompt(books_with_reason: List[Dict], top_n: int = 10) -> str:
    header = f"终评阶段，请在以下初评通过的书目中再次精中选优，最终推荐的书目数量不得超过 {top_n} 本。"
    blocks = []
    for b in books_with_reason:
        block = build_book_block(b)
        # 添加初评理由
        if b.get('初评理由'):
            block += f"\n初评理由:{b.get('初评理由')}"
        # 添加主题内决选理由（如果有）
        if b.get('主题内决选理由'):
            block += f"\n主题内决选理由:{b.get('主题内决选理由')}"
        blocks.append(block)
    return header + "\n\n" + "\n---\n".join(blocks)

def build_runoff_prompt(theme: str, books: List[Dict], quota: int) -> str:
    """
    构建主题内决选提示词

    示例:
    主题: T(工业技术)
    当前有 15 本候选书已通过初评,请从中评选出 **不超过 8 本** 最具代表性、
    最值得推荐的书籍。请综合考虑其深度、影响力、可读性和独特性。
    """
    header = (
        f"主题: {theme}\n"
        f"当前有 {len(books)} 本候选书已通过初评,请从中评选出 **不超过 {quota} 本** "
        f"最具代表性、最值得推荐的书籍。请综合考虑其深度、影响力、可读性和独特性。"
    )
    blocks = []
    for b in books:
        block = build_book_block(b)
        # 添加初评理由(主题内决选需要参考初评理由)
        if b.get('初评理由'):
            block += f"\n初评理由:{b.get('初评理由')}"
        blocks.append(block)
    return header + "\n\n" + "\n---\n".join(blocks)

def build_semifinal_prompt(books: List[Dict], quota: int) -> str:
    """
    构建锦标赛半决赛提示词
    """
    header = (
        f"半决赛阶段,请对以下 {len(books)} 本候选书进行评选,"
        f"选出 **不超过 {quota} 本** 最优秀的书籍晋级决赛。"
    )
    blocks = []
    for b in books:
        block = build_book_block(b)
        # 添加初评理由(半决赛需要参考初评理由)
        if b.get('初评理由'):
            block += f"\n初评理由:{b.get('初评理由')}"
        # 添加主题内决选理由(如果有)
        if b.get('主题内决选理由'):
            block += f"\n主题内决选理由:{b.get('主题内决选理由')}"
        blocks.append(block)
    return header + "\n\n" + "\n---\n".join(blocks)