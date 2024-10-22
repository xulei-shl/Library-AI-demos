from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
print(f"\n-----------API----------------\n")
print(f"API Key: {api_key}, Base URL: {base_url}")

# 生成HTML卡片
def book_card(content):
    llm = ChatOpenAI(
        model="deepseek-chat",  
        temperature=0, 
        api_key=api_key,
        base_url=base_url
    )

    messages = [
        SystemMessage(content="""
            # 图书营销专家

            ## 系统角色

            你是一个洞察敏锐的阅读爱好者,善于提炼图书精髓,创作引人深思的宣传语。

            - 风格参考: 余华、村上春树、加西亚·马尔克斯
            - 擅长: 提炼主题
            - 表达: 简洁有力
            - 内容: 引人深思

            ## 主要功能

            ### Slogan生成

            为用户输入的图书信息生成一句富有洞察力的Slogan。

            处理步骤:
            1. 解析图书信息
            2. 融合信息
            3. 提取核心思想
            4. 凝练主题

            参考示例:
            - "百年孤独" -> "魔幻现实中的人性寓言"
            - "挪威的森林" -> "青春迷失的心灵地图"

            ### SVG卡片生成

            创建富有洞察力且具有审美的SVG概念可视化。

            处理步骤:
            1. 提取书名和责任者
            2. 如果书名和责任者是长文本，使用示例代码1；如果是短文本，则使用示例代码2
            3. 创建极简图书意象
            4. 布局元素(书名、分隔线、责任者、图形、Slogan)
            5. 根据图书主题，设置页面元素的颜色，但要确保元素颜色的协调

            ## SVG代码示例

            严格按照以下SVG代码示例生成，仅替换书名、责任者、Slogan和图形信息，以及各自元素的颜色
                      
            样例1：长文本书名和责任者，使用tspan进行换行处理。其他页面元素位置进行调整
            ```
            <svg width="310" height="406" xmlns="http://www.w3.org/2000/svg">
                <style>
                    .title {
                    font-family: '上图东观体';
                    font-size: 24px;
                    fill: #1e90ff;
                    text-anchor: middle;
                    }
                    .author {
                    font-family: '仓耳玉楷';
                    font-size: 17px;
                    fill: #4169e1;
                    text-anchor: middle;
                    }
                    .slogan {
                    font-family: '又又意宋';
                    font-size: 22px;
                    fill: #1e90ff;
                    text-anchor: middle;
                    }
                </style>

                <rect width="100%" height="100%" fill="#f0f8ff"/>

                <text x="155" y="40" class="title">
                    <tspan x="155" dy="0">阴影</tspan>
                    <tspan x="155" dy="28">西方艺术中对投影的描绘</tspan>
                </text>

                <line x1="20" y1="90" x2="290" y2="90" stroke="#1e90ff" stroke-width="2"/> <!-- Adjusted y1 and y2 to 90 -->

                <text x="155" y="120" class="author"> <!-- Adjusted y to 120 -->
                    <tspan x="155" dy="0">(英)E.H. 贡布里希(E.H. Gombrich)著</tspan>
                    <tspan x="155" dy="24">王立秋译</tspan>
                </text>

                <g transform="translate(55, 200)"> <!-- Adjusted y-translation to 200 -->
                    <path d="M0,0 Q50,100 100,0 T200,0" stroke="#4169e1" stroke-width="2" fill="none"/>
                    <circle cx="50" cy="50" r="20" fill="none" stroke="#1e90ff" stroke-width="2"/>
                    <circle cx="150" cy="50" r="20" fill="none" stroke="#1e90ff" stroke-width="2"/>
                    <line x1="30" y1="50" x2="70" y2="50" stroke="#4169e1" stroke-width="2"/>
                    <line x1="130" y1="50" x2="170" y2="50" stroke="#4169e1" stroke-width="2"/>
                    <line x1="100" y1="20" x2="100" y2="80" stroke="#4169e1" stroke-width="2"/>
                </g>

                <text x="155" y="360" class="slogan"> <!-- Adjusted y to 360 -->
                    <tspan x="155" dy="0">光影之间，</tspan>
                    <tspan x="155" dy="28">艺术之眼的舞步</tspan>
                </text>
                </svg>
            ```
                      
            样例代码2：短文本书名和责任者
            ```
            <svg width="310" height="406" xmlns="http://www.w3.org/2000/svg">
                <style>
                    .title {
                    font-family: '上图东观体';
                    font-size: 24px;
                    fill: #1e90ff;
                    text-anchor: middle;
                    }
                    .author {
                    font-family: '仓耳玉楷';
                    font-size: 17px;
                    fill: #4169e1;
                    text-anchor: middle;
                    }
                    .slogan {
                    font-family: '又又意宋';
                    font-size: 22px;
                    fill: #1e90ff;
                    text-anchor: middle;
                    }
                </style>

                <rect width="100%" height="100%" fill="#f0f8ff"/>

                <text x="155" y="40" class="title">
                    <tspan x="155" dy="0">万事万物史典</tspan>
                </text>

                <line x1="20" y1="60" x2="290" y2="60" stroke="#1e90ff" stroke-width="2"/>

                <text x="155" y="90" class="author">
                    <tspan x="155" dy="0">李雁翎,顾太主编</tspan>
                </text>

                <g transform="translate(55, 140)">
                    <rect x="0" y="0" width="200" height="100" fill="none" stroke="#4169e1" stroke-width="2"/>
                    <line x1="0" y1="50" x2="200" y2="50" stroke="#1e90ff" stroke-width="2"/>
                    <circle cx="100" cy="50" r="20" fill="#1e90ff"/>
                </g>

                <text x="155" y="300" class="slogan">
                    <tspan x="155" dy="0">穿越时空，</tspan>
                    <tspan x="155" dy="28">万物有迹</tspan>
                </text>
            </svg>                      
                      
            ```
            ## 使用说明

            1. 根据用户提供图书的题名、责任者、摘要附注等信息
            2. 系统提取，书名和责任者
            3. 系统根据图书信息生成Slogan       
            4. 根据图书主题设置合理的元素颜色
            5. 输出SVG代码,不再提供额外文本解释

            ## 注意事项

            - 严格按照SVG代码示例进行生成，仅替换书名、责任者、Slogan和图形信息，以及各自元素的颜色
            - 直接SVG代码, 不要有任何多余的内容或者符号    
        """),
        HumanMessage(content=content),
    ]
    
    llm_result = llm.invoke(messages)
    print(f"\n-----------开始文本svg----------------\n")
    slogan_result = extract_json_content(llm_result.content)
    combined_content = f"图书原始信息：\n\n{content}\n\n原始svg代码：\n\n{slogan_result}"
    print(f"\n-----------开始图形svg----------------\n")
    book_svg = book_depiction(combined_content)
    return book_svg

# 生成图书图形
def book_depiction(content):
    llm = ChatOpenAI(
        model="deepseek-chat",  
        temperature=0, 
        api_key=api_key,
        base_url=base_url
    )

    messages = [
        SystemMessage(content="""
            # 图书营销专家

            ## 系统角色

            你是一个洞察敏锐的阅读爱好者,善于提炼图书精髓,创建富有洞察力且具有审美的概念可视化图形。
                      
            ### SVG卡片生成

            创建富有洞察力且具有审美的SVG概念可视化图形。

            处理步骤:
            1. 解析图书原始信息
            2. 提取核心思想
            3. 凝练主题
            4. 根据主题，创建合适的可视化图形代码，代码格式参考原始svg代码的 `<g transform="translate(55, 140)">`部分
            5. 生成的新代码替换原始svg代码的 `<g transform="translate(55, 140)">`部分
            6. 输出替换后的完整代码                          

            ## 注意事项

            - 严格按照SVG代码示例进行生成替换
            - 生成的<g transform="translate(55, 140)">`部分代码，不能有任务文本信息
            - 直接SVG代码, 不要有任何多余的内容或者符号    
        """),
        HumanMessage(content=content),
    ]
    
    result = llm.invoke(messages)
    svg_content = extract_json_content(result.content)
    print(svg_content)
    return svg_content

def extract_json_content(result):
    if '```svg' in result:
        json_start = result.find('```svg') + len('```svg')
        json_end = result.find('```', json_start)
        return result[json_start:json_end].strip()
    elif '```' in result:
        json_start = result.find('```') + len('```')
        json_end = result.find('```', json_start)
        return result[json_start:json_end].strip()
    return result

# # 测试代码
# if __name__ == "__main__":
#    content = """
# | --- | --- | --- | --- |
# | 汽车摩托车大百科 | 博识百科系列编委会编 | 300   $a博识百科系列\n330   $a本书选取了近代世界各国所研发的近500种汽车与摩托车，包括轿车和轿跑车、跑车、运动休旅车、皮卡以 及摩托车等，针对每种汽车与摩托车都介绍了制造商、车体设计、内饰配置、车身性能等知识并配有参数表格，使读者对汽车与摩托车有更全面了解。 | 606   $a汽车$j通俗读物 |
# """
# book_card(content)