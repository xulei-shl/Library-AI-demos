import requests
import json
from typing import List, Dict, Optional

def google_json_to_markdown(books: List[Dict]) -> str:
    """
    将图书信息转换为Markdown格式
    
    参数:
        books: 图书信息列表
        
    返回:
        格式化的Markdown字符串
    """
    markdown = ""
    for i, book in enumerate(books, 1):
        markdown += f"## {i}. {book.get('title', 'N/A')}\n\n"
        markdown += f"**作者:** {book.get('author', 'N/A')}\n\n"
        markdown += f"**ISBN:** {book.get('identifier-isbn', 'N/A')}\n\n"
        markdown += f"**出版社:** {book.get('publisher', 'N/A')}\n\n"
        markdown += f"**出版日期:** {book.get('publishedDate', 'N/A')}\n\n"
        markdown += f"**描述:** {book.get('description', 'N/A')}\n\n"
        markdown += "---\n\n"
    return markdown

def google_book_api(title: Optional[str] = None, author: Optional[str] = None) -> str:
    """
    使用Google Books API搜索图书
    
    参数:
        title: 图书标题
        author: 作者名称
        
    返回:
        格式化的Markdown字符串，包含搜索结果
    """
    query = ""
    if title:
        query += f"intitle:{title}"
    if author:
        if query:
            query += "+"
        query += f"inauthor:{author}"

    try:
        response = requests.get(f"https://www.googleapis.com/books/v1/volumes?q={query}")
        response.raise_for_status()  # 如果请求失败，抛出异常
        data = response.json()
    except requests.exceptions.RequestException as e:
        return f"请求API时出错: {e}"
    except json.JSONDecodeError:
        return "解析API响应时出错"

    books = []
    for item in data.get('items', [])[:10]:
        volume_info = item.get('volumeInfo', {})
        industry_identifiers = volume_info.get('industryIdentifiers', [])
        
        # 提取ISBN
        isbn_list = [identifier.get('identifier') for identifier in industry_identifiers 
                    if identifier.get('type', '').startswith('ISBN')]
        
        book_info = {
            'title': volume_info.get('title', 'N/A'),
            'author': ', '.join(volume_info.get('authors', [])),
            'identifier-isbn': ', '.join(isbn_list),
            'publisher': volume_info.get('publisher', 'N/A'),
            'publishedDate': volume_info.get('publishedDate', 'N/A'),
            'description': volume_info.get('description', 'N/A')
        }
        books.append(book_info)
    
    if not books:
        return "未找到匹配的图书"
    
    return google_json_to_markdown(books)

def save_to_file(content: str, filename: str = "book_search_results.md") -> None:
    """
    将内容保存到文件
    
    参数:
        content: 要保存的内容
        filename: 文件名
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"结果已保存到 {filename}")

def main():
    """
    主函数，处理用户输入并显示结果
    """
    print("Google Books API 搜索工具")
    print("------------------------")
    
    while True:
        print("\n选择搜索方式:")
        print("1. 按标题搜索")
        print("2. 按作者搜索")
        print("3. 按标题和作者搜索")
        print("4. 退出")
        
        choice = input("请输入选项(1-4): ")
        
        if choice == '1':
            title = input("请输入书名: ")
            result = google_book_api(title=title)
        elif choice == '2':
            author = input("请输入作者名: ")
            result = google_book_api(author=author)
        elif choice == '3':
            title = input("请输入书名: ")
            author = input("请输入作者名: ")
            result = google_book_api(title=title, author=author)
        elif choice == '4':
            print("感谢使用，再见!")
            break
        else:
            print("无效选项，请重新输入")
            continue
        
        print("\n搜索结果:")
        print(result)
        
        save_option = input("\n是否保存结果到文件? (y/n): ")
        if save_option.lower() == 'y':
            save_to_file(result)

if __name__ == "__main__":
    main()