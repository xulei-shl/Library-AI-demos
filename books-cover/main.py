from folio_books_info import item_folio_sql_search
from text_cards import book_card
import os

barcode = '54121107752854'
# 提取书目信息
book_info = item_folio_sql_search(barcode)

if book_info is not None:
    #生成卡片
    result = book_card(book_info)
    if result is not None:
    # 保存结果到文件
        output_dir = os.path.join(os.path.dirname(__file__), 'svgs')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{barcode}.svg")
        with open(output_path, 'w', encoding='utf-8') as f:  # 指定编码为 utf-8
            f.write(result)
    else:
        print("No book-svg information.")
else:
    print("No book information found for the given barcode.")