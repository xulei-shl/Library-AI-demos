from dotenv import load_dotenv
import os
from operator import itemgetter
from langchain_community.chat_models import ChatZhipuAI
from langfuse import Langfuse
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langfuse.callback import CallbackHandler

load_dotenv()

os.environ['DEEPSEEK_API_KEY'] = os.getenv('DEEPSEEK_API_KEY')
os.environ['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')

# #zhipu
os.environ['OPENAI_API_KEY'] = os.getenv('ZHIPU_API_KEY')
os.environ['OPENAI_API_BASE'] = os.getenv('ZHIPU_API_BASE')

# # #modelscope
# os.environ['OPENAI_API_KEY'] = os.getenv('MODELSCOPE_API_KEY')
# os.environ['OPENAI_API_BASE'] = os.getenv('MODELSCOPE_API_BASE')
# # model="openai/LLM-Research/Llama-3.3-70B-Instruct",

# # #siliconflow
# os.environ['OPENAI_API_KEY'] = os.getenv('SILICONFLOW_API_KEY')
# os.environ['OPENAI_API_BASE'] = os.getenv('SILICONFLOW_API_BASE')
# # model="openai/Qwen/Qwen2.5-7B-Instruct",

# #oneapi
# os.environ['OPENAI_API_KEY'] = os.getenv('ONEAPI_API_KEY')
# os.environ['OPENAI_API_BASE'] = os.getenv('ONEAPI_API_BASE')
# #model="openai/step",

os.environ["LANGFUSE_SECRET_KEY"] = os.getenv('LANGFUSE_SECRET_KEY')
os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv('LANGFUSE_PUBLIC_KEY')
os.environ["LANGFUSE_HOST"] = os.getenv('LANGFUSE_HOST')


langfuse_handler = CallbackHandler()

langfuse_prompt = Langfuse().get_prompt('test')
print(langfuse_prompt.prompt)
 
prompt1 = ChatPromptTemplate.from_template("what is the city {person} is from?")
prompt2 = ChatPromptTemplate.from_template(
    "what country is the city {city} in? respond in {language}"
)
model = ChatZhipuAI(
    model="glm-4-flash"  # 如果需要指定模型，取决于你使用的服务商
)
chain1 = prompt1 | model | StrOutputParser()
chain2 = (
    {"city": chain1, "language": itemgetter("language")}
    | prompt2
    | model
    | StrOutputParser()
)
 
chain2.invoke({"person": "obama", "language": "spanish"}, config={"callbacks":[langfuse_handler]})
