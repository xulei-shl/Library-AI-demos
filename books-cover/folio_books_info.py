from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()


# Database connection details
DB_CONFIG = {
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}


def sql_results_to_markdown(results):
    """Converts the SQL query results to a Markdown table format."""
    headers = ["题名", "责任者", "备注信息", "主题"]
    markdown = "| " + " | ".join(headers) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    
    for row in results:
        title, responsibility, other_info = row
        # Extract 3XX and 6XX fields from other_info
        other_info_list = other_info.strip('[]').split('", "')
        notes_info = "\\n".join([info for info in other_info_list if info.startswith('3')])
        subject_info = "\\n".join([info for info in other_info_list if info.startswith('6') and not info.startswith('690')])
        
        markdown += f"| {title} | {responsibility} | {notes_info} | {subject_info} |\n"
    
    return markdown

def item_folio_sql_search(barcode):
    conn = psycopg2.connect(**DB_CONFIG)
    with conn:
        with conn.cursor() as cursor:
            sql = """
            SELECT
                bd.jsonb ->> 'instanceId' AS instanceId
            FROM
                shlibrary_mod_shl_inventory.bookduplicate bd
            WHERE
                LOWER(f_unaccent(bd.JSONB ->> 'barcode')) = LOWER(f_unaccent(%s))
                AND bd.JSONB ->> 'deleted' = 'false'
            """
            cursor.execute(sql, (str(barcode),))
            instanceID = cursor.fetchall()
            print(f"\n-----------instanceID----------------\n")
            print(instanceID)
            # Extract the first value from the tuple
            instance_id = instanceID[0][0] if instanceID else None
            if instance_id:
                book_info = instance_folio_sql_search(instance_id)
                print(f"\n------------instanceInfo-table---------------\n")
                print(book_info)
                return book_info

def instance_folio_sql_search(id):
    conn = psycopg2.connect(**DB_CONFIG)
    with conn:
        with conn.cursor() as cursor:
            sql = """
            SELECT
                bl.jsonb ->> 'title' AS 题名,
                bl.jsonb ->> 'responsibility' AS 责任者,
                bl.jsonb ->> 'sourceRecord' AS 其他信息
            FROM
                shlibrary_mod_shl_inventory.booklist bl
            WHERE
                id = %s
                AND bl.JSONB ->> 'deleted' = 'false'
            """
            cursor.execute(sql, (id,))  # Change (str(barcode),) to (id,)
            results = cursor.fetchall()
            print(f"\n------------instanceInfo---------------\n")
            print(results)
            markdown_table = sql_results_to_markdown(results)
            return markdown_table

# # 测试代码
# if __name__ == "__main__":
#     barcode = '54121110919263'
#     item_folio_sql_search(barcode)