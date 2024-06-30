import os
from dotenv import load_dotenv
import chainlit as cl
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_qdrant import Qdrant
from langchain.chains import RetrievalQA
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from tools.kill_qdrant import kill_qdrant_instances_one, kill_qdrant_instances_two

# Load environment variables
load_dotenv()

# Retrieve API keys
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_api_base = os.getenv("OPENAI_API_BASE")

# System template
system_template = """Use the following pieces of context to answer the user's question.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Begin!
----------------
{context}"""

messages = [
    SystemMessagePromptTemplate.from_template(system_template),
    HumanMessagePromptTemplate.from_template("{question}"),
]
prompt = ChatPromptTemplate.from_messages(messages)
chain_type_kwargs = {"prompt": prompt}

# Path to your existing local Qdrant SQLite database
QDRANT_PATH = os.getenv("QDRANT_PATH")
COLLECTION_NAME = "my_documents"

kill_qdrant_instances_one()
kill_qdrant_instances_two()

# Create a global Qdrant client instance
global_qdrant_client = QdrantClient(path=QDRANT_PATH)

def initialize_qdrant_client():
    try:
        collections = global_qdrant_client.get_collections().collections
        if not any(collection.name == COLLECTION_NAME for collection in collections):
            global_qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
    except Exception as e:
        print(f"Error initializing Qdrant client: {e}")

@cl.on_chat_start
async def init():
    # Terminate any existing Qdrant instances
    kill_qdrant_instances_one()

    # Initialize embeddings
    embeddings = OpenAIEmbeddings(
        openai_api_key=openai_api_key,
        openai_api_base=openai_api_base
    )

    initialize_qdrant_client()
    
    # Load the existing Qdrant database
    docsearch = Qdrant(
        client=global_qdrant_client,
        collection_name=COLLECTION_NAME,
        embeddings=embeddings
    )

    # Create a chain that uses the Qdrant vector store
    chain = RetrievalQA.from_chain_type(
        ChatOpenAI(
            temperature=0,
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base
        ),
        chain_type="stuff",
        retriever=docsearch.as_retriever(),
    )

    cl.user_session.set("chain", chain)

    # Let the user know that the system is ready
    await cl.Message(content="已加载现有的本地 Qdrant 向量数据库。您现在可以提出问题了!").send()

@cl.on_message
async def main(message: cl.Message):
    chain = cl.user_session.get("chain")
    cb = cl.AsyncLangchainCallbackHandler(
        stream_final_answer=True, answer_prefix_tokens=["FINAL", "ANSWER"]
    )
    cb.answer_reached = True
    res = await chain.acall(message.content, callbacks=[cb])

    answer = res["result"]

    if cb.has_streamed_final_answer:
        await cb.final_stream.update()
    else:
        await cl.Message(content=answer).send()