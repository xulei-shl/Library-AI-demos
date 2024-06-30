import os
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import Qdrant
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import sys
from tools.topic_path import get_file_path
import re
from langchain.docstore.document import Document
from tools.log_vector_info import log_vector_info

def load_and_split_document(file_path, separators=["---"], chunk_size=1000, chunk_overlap=100):
    try:
        loader = TextLoader(file_path, encoding='utf-8')
        documents = loader.load()
    except UnicodeDecodeError:
        print("UTF-8 encoding failed. Trying with 'gbk' encoding...")
        loader = TextLoader(file_path, encoding='gbk')
        documents = loader.load()
    except Exception as e:
        raise Exception(f"Error loading file: {e}")

    text_splitter = RecursiveCharacterTextSplitter(
        separators=separators,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    
    docs = text_splitter.create_documents([documents[0].page_content])
    return docs

def custom_split(text):
    h2_pattern = r'^## .+$'
    h3_pattern = r'^### .+$'
    chunks = text.split("---")
    result = []
    current_h2 = ""
    
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        
        lines = chunk.split('\n')
        h2_match = re.match(h2_pattern, lines[0], re.MULTILINE)
        
        if h2_match:
            current_h2 = lines[0]
            chunk = '\n'.join(lines[1:])
        
        if len(chunk) > 1000:
            sub_chunks = re.split(h3_pattern, chunk, flags=re.MULTILINE)
            for i, sub_chunk in enumerate(sub_chunks):
                if i > 0:
                    sub_chunk = "### " + sub_chunk
                if current_h2:
                    sub_chunk = current_h2 + "\n\n" + sub_chunk
                result.append(sub_chunk.strip())
        else:
            if current_h2:
                chunk = current_h2 + "\n\n" + chunk
            result.append(chunk.strip())
    
    return result

def get_split_examples(docs):
    if not docs:
        return "No documents found after splitting."
    return f"First chunk:\n{docs[0].page_content}\n\nLast chunk:\n{docs[-1].page_content}"

def process_md_file(selected_topic, selected_file, separators=["---"], chunk_size=1000, chunk_overlap=100):
    folder_path = get_file_path(selected_topic)
    md_file_path = os.path.join(folder_path, selected_file)

    qdrant_path = os.path.join(folder_path, "local_qdrant")
    if not os.path.exists(qdrant_path):
        os.makedirs(qdrant_path)
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, '.env')

    if env_path:
        load_dotenv(env_path, override=True)
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_api_base = os.getenv("OPENAI_API_BASE")
    else:
        raise Exception(".env file not found")

    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

    docs = load_and_split_document(md_file_path, separators, chunk_size, chunk_overlap)
    
    final_docs = []
    for doc in docs:
        final_docs.extend([Document(page_content=chunk) for chunk in custom_split(doc.page_content)])

    qdrant = Qdrant.from_documents(
        final_docs,
        embeddings,
        path=qdrant_path,
        collection_name="my_documents",
    )

    # 记录向量化日志
    log_vector_info(selected_topic, selected_file, folder_path)

    return "🎉 文本向量化已完成。"

if __name__ == "__main__":
    selected_topic = "图书馆"  # 示例主题词
    selected_file = "example.md"  # 示例文件名
    print(process_md_file(selected_topic, selected_file))