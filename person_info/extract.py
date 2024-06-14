import streamlit as st
import pandas as pd
from openpyxl.utils.dataframe import dataframe_to_rows
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Optional, List
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
import warnings
from langchain_core._api.beta_decorator import LangChainBetaWarning
import requests
import traceback
import os
from dotenv import load_dotenv

load_dotenv()


#v0.6 读取本地excel文件执行json提取，并把结果写回。添加示例；分任务多次提取，不同任务不同的 examples；streamlit页面；提取到的信息再调用上图人名规范库，得到URI[只匹配返回结果为1的]

# 忽略LangChainBetaWarning
warnings.filterwarnings(action="ignore", category=LangChainBetaWarning)

class Person(BaseModel):
    """Information about a person."""
    # The name of the person.
    name: Optional[str] = Field(default=None, description="The name of the person.")
    # The gender of the person.
    gender: Optional[str] = Field(default=None, description="The gender of the person.")
    # The educational background of the person.
    education: Optional[str] = Field(default=None, description="The educational background of the person.")
    # The ethnicity of the person.
    ethnicity: Optional[str] = Field(default=None, description="The ethnicity of the person.")
    # The birth date of the person.
    birth_date: Optional[str] = Field(default=None, description="The birth date of the person.")
    # The profession of the person.
    profession: Optional[str] = Field(default=None, description="The profession or occupation of the person.")
    # The achievements or awards received by the person.
    achievements: Optional[str] = Field(default=None, description="The achievements or awards received by the person.")
    # The native place of the person.
    native_place: Optional[str] = Field(default=None, description="The native place of the person.")
    # List of publications by the person.
    publications: Optional[List[str]] = Field(default=None, description="List of publications related to the person.")
    # List of institutions related to the person.
    institutions: Optional[List[str]] = Field(default=None, description="List of institutions related to the person.")
    # The research focus of the person.
    research_focus: Optional[str] = Field(default=None, description="The research focus of the person.")

class Data(BaseModel):
    """Extracted data about people."""
    people: List[Person]

class PersonName(BaseModel):
    """Information about a person's name."""
    name: Optional[str] = Field(default=None, description="The name of the person.")
    nickname: Optional[List[str]] = Field(default=None, description="The person's nickname or name in another language or any other form of names")

class PersonNameData(BaseModel):
    people: List[PersonName]

# Define separate prompts for different schemas
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert extraction algorithm. Only extract relevant information about a person from the text. If you do not know the value of an attribute asked to extract, return null for the attribute's value."),
    MessagesPlaceholder("examples"),
    ("human", "{text}"),
])

# 定义不同的 examples
person_examples = [
    ("human", "罗伯特·诺奇克(Robert Nozick，1938—2002)，别名诺克，原名Nozick，美国哈佛大学哲学教授。先后在北京大学、武昌师大、广东大学任教。20世纪70、80年代与罗尔斯齐名的政治哲学家，因其在《无政府、国家与乌托邦》一书中对自由至上主义做辩护而为国内外学者广泛关注，主要著作有：《无政府、国家与乌托邦》、《合理性的本质》、《反思生活》等。其他代表作有：《沉沦》、《故都的秋》、《春风沉醉的晚上》、《过去》、《迟桂花》等。也发表了《小说论》、《戏剧论》"),
    ("ai", "people=[Person(name='罗伯特·诺奇克', birth_date='1938—2002', profession='美国哈佛大学哲学教授', publications=['无政府、国家与乌托邦', '合理性的本质', '反思生活', '沉沦', '故都的秋', '春风沉醉的晚上', '过去', '迟桂花', '小说论', '戏剧论'], institutions=['哈佛大学', '北京大学', '武昌师大', '广东大学'], research_focus='政治哲学')]")
]

personname_examples = [
    ("human", "王夫之，别名青红居士，原名王洋月，字月之。美国哈佛大学哲学教授。先后在北京大学、武昌师大、广东大学任教。20世纪70、80年代与罗尔斯齐名的政治哲学家，因其在《无政府、国家与乌托邦》一书中对自由至上主义做辩护而为国内外学者广泛关注，主要著作有：《无政府、国家与乌托邦》、《合理性的本质》、《反思生活》等。其他代表作有：《沉沦》、《故都的秋》、《春风沉醉的晚上》、《过去》、《迟桂花》等。也发表了《小说论》、《戏剧论》"),
    ("ai", "people=[PersonName(name='王夫之', nickname=['青红居士', '王洋月', '月之'])]")
]

llm = ChatOpenAI(
    temperature=0,
    model_name="gpt-4o",
    openai_api_base=os.environ.get("OPENAI_API_BASE"),
    openai_api_key=os.environ.get("OPENAI_API_KEY"),
)

def extract_info(text, prompt, schema, examples):
    try:
        print(f"---------------------------------------------")
        print(f"Invoking LLM with text: {text[:50]}...")  # 打印输入文本的前 50 个字符
        runnable = prompt | llm.with_structured_output(schema=schema)
        result = runnable.invoke({
            "examples": examples,
            "text": text
        })
        print(f"---------------------------------------------")
        print(f"LLM output: {result}")  # 打印 LLM 的输出结果
        return result
    except Exception as e:
        print(f"An error occurred: {e}")
        print(traceback.format_exc())
        return None

# 上海图书馆人名规范库URI匹配
def get_person_uri(person_name):
    try:
        url = "http://data1.library.sh.cn/persons/data"
        params = {
            "fname": person_name,
            "key": os.environ.get("LIBRARY_API_KEY"),
            "pageth": 1,
            "pageSize": 10
        }

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

        print(f"---------------------------------------------")
        print(f"Calling API for person '{person_name}'...")  # 打印正在调用 API 的人名
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # 检查响应状态码
        data = response.json()
        print(f"---------------------------------------------")
        print(f"API response for '{person_name}': {data}")  # 打印 API 的响应结果

        if data['result'] == '0' and len(data['data']) == 1:
            return data['data'][0].get('place_uri', '')
        else:
            return ''
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while calling API for person '{person_name}': {e}")
        return ''
    except ValueError as e:
        print(f"Error occurred while parsing API response for person '{person_name}': {e}")
        return ''


def process_excel(uploaded_file):
    data = pd.read_excel(uploaded_file)
    num_rows = len(data)
    print(f"---------------------------------------------")
    print(f"Total rows in the input file: {num_rows}")  # 打印输入文件的总行数
    result_data = data.copy()
    result_data['姓名'] = ''
    result_data['其他名字'] = ''
    result_data['性别'] = ''
    result_data['就职学校'] = ''
    result_data['民族'] = ''
    result_data['日期'] = ''
    result_data['职业'] = ''
    result_data['成就'] = ''
    result_data['籍贯'] = ''
    result_data['相关出版物'] = ''
    result_data['相关机构'] = ''
    result_data['研究领域'] = ''
    result_data['place_uri'] = ''

    for i in range(min(10, num_rows)):
        row = data.iloc[i]
        person_text = row['作者简介']
        st.session_state['current_text_placeholder'].write(f"正在提取🏃‍♂️: {person_text}")  # 更新占位符中的文本
        print(f"---------------------------------------------")
        print(f"\nProcessing row {i+1}:")
        print(f"Input text: {person_text}")

        person_result = extract_info(person_text, prompt, Data, person_examples)
        if person_result and person_result.people:
            person = person_result.people[0]
            result_data.at[i, '姓名'] = person.name
            result_data.at[i, '性别'] = person.gender
            result_data.at[i, '就职学校'] = person.education
            result_data.at[i, '民族'] = person.ethnicity
            result_data.at[i, '日期'] = person.birth_date
            result_data.at[i, '职业'] = person.profession
            result_data.at[i, '成就'] = person.achievements
            result_data.at[i, '籍贯'] = person.native_place
            result_data.at[i, '相关出版物'] = ', '.join(person.publications) if person.publications else ''
            result_data.at[i, '相关机构'] = ', '.join(person.institutions) if person.institutions else ''
            result_data.at[i, '研究领域'] = person.research_focus
            person_uri = get_person_uri(person.name)
            result_data.at[i, 'uri'] = person_uri

        personname_result = extract_info(person_text, prompt, PersonNameData, personname_examples)
        if personname_result and personname_result.people:
            person = personname_result.people[0]
            result_data.at[i, '其他名字'] = ', '.join(person.nickname) if person.nickname else ''

    st.session_state['result_data'] = result_data
    return result_data

def main():
    st.title("人物信息提取")

    uploaded_file = st.file_uploader("上传 Excel 文件", type=["xlsx"])
    
    # 创建占位符
    placeholder = st.empty()
    run_button_placeholder = st.empty()
    
    if uploaded_file is not None:
        with run_button_placeholder:
            run_button = st.button("运行")
        
        # 在"运行"按钮之后显示提示信息
        if run_button:
            process_excel(uploaded_file)
            run_button_placeholder.empty()  # 移除"运行"按钮

            if "result_data" in st.session_state:
                with placeholder:
                    st.write("🥳提取完成,请点击下载提取结果")

                csv = st.session_state['result_data'].to_csv(index=False)
                st.download_button(
                    label="下载 CSV 文件",
                    data=csv,
                    file_name="result.csv",
                    mime="text/csv",
                )
    
    current_text_placeholder = st.empty()
    st.session_state['current_text_placeholder'] = current_text_placeholder

if __name__ == "__main__":
    main()