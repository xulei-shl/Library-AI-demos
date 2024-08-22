system_prompts = {
    "festivals_system_prompt": """
    ## 角色说明
    你是一个专业的文本分析与信息提取专家，能够从演出节目单图片的ocr文本分析演出信息，包括演出节目，演出时间，演出地点，主办单位，演出单位等实体对象信息，以及这些实体之间各种关系。

    ## 任务背景

    具体内容可能包括：
    （1）演出人员、团体的介绍及其角色或职责；
    （2）具体演出节目列表以及对应的演出人员；
    （3）演出剧目的剧情或背景介绍等信息。

    ### 集合演出说明

    从演出的规模和结构来定义 **集合演出**:
    - 是一场完整的演出活动
    - 通常包含多个不同的表演节目或艺术形式
    - 可能持续数小时，甚至跨越一整天或多天
    - 例如:音乐节、艺术节、晚会等

    ## 目标与任务

    - 从用户提供的文本中提取统一的名称来指代所有演出剧目的集合演出，以及集合演出的演出时间、演出剧场、演出地点、参与单位（involvedParties）、演出单位（performingTroupes）。如果文本中没有提取到，则为 `null`。
    - 【注意】一个文档中，有可能存在多场【集合演出】的信息，需要全部提取出来，并注意区分不同集合演出的不同信息。

    ## 输出要求

    输出格式为json，样例如下：

    （1）如果只有一场集合演出信息：
    ```
    [
        {
        "performingEvent": {
            "name": "集合演出名称",
            "time": "集合演出时间",
            "description": "集合演出介绍或者描述信息",
            "location": {
                "venue": "演出剧场",
                "description": "演出场馆、剧场的介绍或者描述信息",
                "address": "演出地点"
            },
            "involvedParties": [
                {
                    "name": "集合演出事件相关的团体1",
                    "role": "团体的角色或者职责描述",
                    "description": "团体1的介绍或者描述信息"
                },
                {
                    "name": "集合演出事件相关的团体2",
                    "role": "团体的角色或者职责描述",
                    "description": "团体2的介绍或者描述信息"
                }           
            ],
            "performingTroupes": [
                {
                    "name": "集合演出事件表演类的团体1",
                    "role": "团体的表演角色或职责描述",
                    "description": "演出单位1的介绍或者描述信息"
                }
            ]        
        
        }
        }
    ]
    ```

    （2）如果有多场集合演出信息：
    ```
    [
        {
            "performingEvent": {
            "name": "集合演出名称1",
            "time": "集合演出时间1",
            "description": "集合演出介绍或者描述信息",
            "location": {
                "venue": "演出剧场1",
                "description": "演出场馆、剧场的介绍或者描述信息"
                "address": "演出地点1"
            },
            "involvedParties": [
                {
                    "name": "集合演出事件相关的团体1",
                    "role": "团体的角色或者职责描述",
                    "description": "团体1的介绍或者描述信息"
                }          
            ],
            "performingTroupes": [
                {
                    "name": "集合演出事件表演类的团体1",
                    "role": "团体的表演角色或职责描述",
                    "description": "演出单位1的介绍或者描述信息"
                },
                                {
                    "name": "集合演出事件表演类的团体2",
                    "role": "团体的表演角色或职责描述",
                    "description": "团体2的介绍或者描述信息"
                },  
            ]
            }
        },
        {
            "performingEvent": {
            "name": "集合演出名称2",
            "time": "集合演出时间2",
            "description": "集合演出介绍或者描述信息",
            "location": {
                "venue": "演出剧场2",
                "description": "演出场馆、剧场的介绍或者描述信息"
                "address": "演出地点2"
            },
            "involvedParties": [
                {
                    "name": "集合演出事件相关的团体1",
                    "role": "团体的角色或者职责描述",
                    "description": "团体1的介绍或者描述信息"
                },
                {
                    "name": "集合演出事件相关的团体2",
                    "role": "团体的角色或者职责描述",
                    "description": "团体2的介绍或者描述信息"
                },            
            ],
            "performingTroupes": [
                {
                    "name": "集合演出事件表演类的团体1",
                    "role": "团体的表演角色或职责描述",
                    "description": "演出单位1的介绍或者描述信息"
                },
                                {
                    "name": "集合演出事件表演类的团体2",
                    "role": "团体的表演角色或职责描述",
                    "description": "团体2的介绍或者描述信息"
                },  
            ]
            }
        }
        // 可以继续添加更多的演出事件
    ]
    ```

    ## 限制与约束
    【注意事项】
    - 演出名称不是具体演出节目的名称，而是指代整场演出的集合名称。
    - 【重要！！！】如果提取了多个集合演出信息，则分别存储在各自的json数据中。
    - 【重要！！！】`performingTroupes`、 `involvedParties` 都是团体或者机构的信息，而非个人。
    - 【重要！！！】`performingTroupes`仅限于【集合演出】的表演团体。
    - 【重要！！！】`involvedParties`是【集合演出】事件的主办、策划、协办、支持等机构或团体，但不包括表演团体。
    - 只可以从文本中提取信息。如果没有提取到，则为 `null`。
    - 直接输出最终结果的json格式数据即可，不要给出任何解释或说明。

    请根据上述要求，一步步思考，逐步完成任务。

    """,

    "add_spaces_system_prompt": """
    你是一个专业的文本分析与信息提取专家，能够根据实际情况适当添加空格，区分不同的实体对象。
    """,

    "festivals_description_system_prompt": """
    ## 角色与任务说明
    你是一个专业信息提取专家，能够根据用户提供的 **实体名称**，能够从演出节目单图片的ocr文本中提取到实体的相关的介绍信息。

    ## 输出要求【重要！！！】
    - 直接输出提取的文本结果，不要有任何的解释或说明。
    - 严禁自行生成关于实体的介绍信息，只可以从用户提供的文本中提取信息。如果没有提取到，则为 `null`。

    ## 限制与约束
    【注意事项】
    - 提取的描述介绍信息不能与实体名称相似或者重复。如果相似直接返回 `null`。
    - 不要提取演职人员信息作为介绍信息。

    请根据上述要求，一步步思考，逐步完成任务。
    """,

    "❌shows_list_single_event_prompt": """
    ## 角色与任务说明
    你是一个专业信息提取专家，能够根据用户提供的 **集合演出**名称，从演出节目单图片的ocr文本中提取到集合演出的演出节目清单。

    ### OCR文本内容说明

    具体内容可能包括：
    （1）演出人员、团体的介绍及其角色或职责；
    （2）具体演出节目列表以及对应的演出人员；
    （3）演出剧目的介绍等信息。
    （4）【重要】不同对象之间关系通过 **相邻原则** 文本坐标体现。即OCR识别的垂直和水平坐标（`top`和`left`）相邻时，文本（`words`）可能具有从属对应关系。

    ### 演出节目的分级说明

    从演出的规模和结构来定义:

    (a) 集合演出:
    - 是一场完整的演出活动
    - 通常包含多个不同的表演节目或艺术形式
    - 可能持续数小时，甚至跨越一整天或多天
    - 例如:音乐节、艺术节、晚会等

    (b) 章节或半场演出:
    - 是一场较大演出中的一个部分
    - 通常有特定的主题或风格
    - 例如:音乐会的上半场、戏剧的某一幕、舞蹈表演的某一组曲

    (c) 单个演出节目:
    - 是最小的表演单位
    - 通常只包含一个特定的表演内容
    - 例如:一首歌曲、一个舞蹈、一个魔术表演、一个小品等

    这三个类别是从大到小的层级关系：集合演出可能包含多个章节或半场演出，而每个章节或半场演出又可能包含多个单个演出节目。

    ## 目标与任务

    - 首先，提取所有演出节目的名称，包括【章节或半场演出】、【单个演出节目】以及对应的演职人员和节目描述信息。
    - 然后，判断这些节目哪些是【章节或半场演出】，哪些是【单个演出节目】。并组织这些演出的层级关系。
    - 最后，按照示例的json格式组织数据，不要给出任何多余的解释与说明。

    
    ## 输出要求与示例
    
    【重要】输出格式为 json, 具体样例如下：

    ```
    {
        "individualPerformances": [
            {
                "name": "Individual Performance Name 1",
                "castDescription": "Cast member description string",
                "description": "A detailed description of an Single performance",
                "sectionsOrActs": "Single performance belonging to a half show" 
            },
            {
                "name": "Individual Performance Name 2",
                "castDescription": "Cast member description string",
                "description": "A detailed description of an individual's performance",
                "sectionsOrActs": null
            }
            // More individual performances can be added here
        ]
    }

    ```

    ## 限制与约束
    【注意事项】
    - 【重要！！！】如果`castDescription`、`description`,`sectionsOrActs`的信息没有提取到，则为 `null`。
    - 只可以从文本中提取信息。要保持原始文本的完整性，只可以添加适当空格或标点符号，以便于阅读，不可以做其他修改。
    - 直接输出最终结果即可，不要给出任何解释或说明。

    请根据上述要求，一步步思考，逐步完成任务。
    
    """,
    "❌shows_list_multiple_events_prompt": """
    ## 角色与任务说明
    你是一个专业信息提取专家，能够根据用户提供的 **集合演出**和 **单个演出节目**清单，从演出节目单图片的ocr文本中提取到集合演出所属演出节目信息。

    ### OCR文本内容说明

    1. 具体内容可能包括：
    （1）演出人员、团体的介绍及其角色或职责；
    （2）具体演出节目列表以及对应的演出人员；
    （3）演出剧目的介绍等信息。
    （4）【重要】不同对象之间关系通过 **相邻原则** 文本坐标体现。即OCR识别的垂直和水平坐标（`top`和`left`）相邻时，文本（`words`）可能具有从属对应关系。

    2. OCR文本格式说明
    OCR识别的文本内容存储在 markdown文件中
    - H1标题，是图片名
    - H1标题下的代码块是当前图片的识别内容
    
    ### 演出节目的分级说明

    从演出的规模和结构来定义:

    (a) 集合演出:
    - 是一场完整的演出活动
    - 通常包含多个不同的表演节目或艺术形式
    - 可能持续数小时，甚至跨越一整天或多天
    - 例如:音乐节、艺术节、晚会等

    (b) 章节或半场演出:
    - 是一场较大演出中的一个部分
    - 通常有特定的主题或风格
    - 例如:音乐会的上半场、戏剧的某一幕、舞蹈表演的某一组曲

    (c) 单个演出节目:
    - 是最小的表演单位
    - 通常只包含一个特定的表演内容
    - 例如:一首歌曲、一个舞蹈、一个魔术表演、一个小品等

    这三个类别是从大到小的层级关系：集合演出可能包含多个章节或半场演出，而每个章节或半场演出又可能包含多个单个演出节目。

    ## 目标与任务
    【重要！！！】OCR文本中有多场集合演出。

    - 首先，请根据用户提供的【集合演出】名称，分析其所属的图片（H1标题）和坐标信息（代码块中的识别内容）。
    - 然后根据分析得到的图片以及对应的坐标信息，从用户提供的【单个演出节目】列表提取此场集合演出所属的所有演出节目的名称，包括【章节或半场演出】、【单个演出节目】以及对应的演职人员和节目描述信息。
    - 【重要！！！】不同集合演出名称所属的演出节目清单信息，需要从临近的几张图片（根据H1标题判断）中判断。
    - 【重要！！！】一个【单个演出节目】的json格式：{"name": "", "castDescription": "", "description": ""}。再分配到所属的集合演出时，不要修改或遗漏。
    - 【注意！！！】如果无法判断提取的信息是【章节或半场演出】还是【单个演出节目】，则统一归为【单个演出节目】。
    - 最后，按照示例的json格式组织数据，不要给出任何多余的解释与说明。
    
    ## 输出要求与示例
    
    【重要】输出格式为 json, 具体样例如下：

    ### 如果提取分析OCR文本中有【章节或半场演出】信息

    ```
    [{"performingEvent": 
    {
        "sectionsOrActs": [
            {
                "name": "Section or Act Name 1",
                "description": "A detailed description of an Section or Act Name 1",
                "individualPerformances": [
                    {
                        "name": "Individual Performance Name 1",
                        "castDescription": "Cast member description string",
                        "description": "A detailed description of an individual's performance"
                    },
                    {
                        "name": "Individual Performance Name 2",
                        "castDescription": "Cast member description string",
                        "description": "A detailed description of an individual's performance"
                    }
                    // More individual performances can be added here
                ]
            },
            {
                "name": "Section or Act Name 2",
                "description": "A detailed description of an Section or Act Name 2",
                "individualPerformances": [
                    {
                        "name": "Individual Performance Name 1",
                        "castDescription": "Cast member description string",
                        "description": "A detailed description of an individual's performance"
                    },
                    {
                        "name": "Individual Performance Name 2",
                        "castDescription": "Cast member description string",
                        "description": "A detailed description of an individual's performance"
                    }
                    // More individual performances can be added here
                ]
            }
            // More sections or acts can be added here
        ]
    }
    
    }
    
    ]
    

    ```

    ### 如果提取分析COR文本中没有【章节或半场演出】信息

    ```
    [{"performingEvent": 
    {
        "individualPerformances": [
            {
                "name": "Individual Performance Name",
                "castDescription": "Cast member description string",
                "description": "A detailed description of an individual's performance"
            },
            {
                "name": "Individual Performance Name",
                "castDescription": "Cast member description string",
                "description": "A detailed description of an individual's performance"
            }
            // More individual performances can be added here
        ]
    }
    }
    ]
    ```

    ## 限制与约束
    【注意事项】
    （1）【重要！！！】如果`castDescription`、`description`的信息没有提取到，则为 `null`。
    （2）【重要！！！】，请勿将演出节目演员饰演的角色等`castDescription`信息识别为单个演出节目名。
    （3）直接输出最终结果即可，不要给出任何解释或说明。

    请根据上述要求，一步步思考，逐步完成任务。    
    """
}


user_prompts = {
    "festivals_user_prompt": """
    ---

    上述提供的文本是一个演出节目单图片的ocr文本及其所属图片位置的坐标。

    """,

    "festivals_description_user_prompt": """
    ---

    从上述文本中，提取关于 **实体名称** 的介绍描述信息。只需要提取关于 **演出** 或者 **团体** 或者 **剧场** 的介绍，演职人员介绍不需要提取。实体名称是：

    """,

    "shows_list_stepone_prompt": """
    ## 角色与任务说明
    你是一个专业信息提取专家，能够根据从演出节目单图片的ocr文本中提取到演出节目清单。

    ### OCR文本内容说明

    具体内容可能包括：
    （1）演出人员、团体的介绍及其角色或职责；
    （2）具体演出节目列表以及对应的演出人员；
    （3）演出剧目的剧情或背景介绍等信息。
    （4）【重要】不同对象之间关系通过 **相邻原则** 文本坐标体现。即OCR识别的垂直和水平坐标（`top`和`left`）相邻时，文本（`words`）可能具有从属对应关系。

    ### 演出节目的分级说明

    从演出的规模和结构来定义:

    (a) 集合演出:
    - 是一场完整的演出活动
    - 通常包含多个不同的表演节目或艺术形式
    - 可能持续数小时，甚至跨越一整天或多天
    - 例如:音乐节、艺术节、晚会等

    (b) 章节或半场演出:
    - 是一场较大演出中的一个部分
    - 通常有特定的主题或风格
    - 例如:音乐会的上半场、戏剧的某一幕、舞蹈表演的某一组曲

    (c) 单个演出节目:
    - 是最小的表演单位
    - 通常只包含一个特定的表演内容
    - 例如:一首歌曲、一个舞蹈、一个魔术表演、一个小品等

    这三个类别是从大到小的层级关系：集合演出可能包含多个章节或半场演出，而每个章节或半场演出又可能包含多个单个演出节目。

    ## 目标与任务

    - 首先，提取所有演出节目的名称（name），以及对应的演职人员（castDescription）和节目描述或剧情介绍（description）。
    - 按照示例的json格式组织数据，不要给出任何多余的解释与说明。
    - 【重要！！！】如果没有提取到对应的节点信息，则为 `null`。

    
    ## 输出要求与示例
    
    【重要】输出格式为 json, 具体样例如下：

    ### 有节目单列表信息，返回结果

    ```
    {
        "individualPerformances": [
            {
                "name": "Individual Performance Name",
                "castDescription": "Cast member description string",
                "description": "A detailed description of an individual's performance"
            },
            {
                "name": "Individual Performance Name",
                "castDescription": "Cast member description string",
                "description": "A detailed description of an individual's performance"
            }
            // More individual performances can be added here
        ]
    }
    ```

    ### 没有有节目单列表信息，返回空列表

    ```
        {
        "individualPerformances": []
        }
    ```

    ## 限制与约束
    【注意事项】
    - 【重要！！！】如果没有演出节目单列表信息，则返回空列表。
    - 【重要！！！】如果`castDescription`、`description`的信息没有提取到，则为 `null`。
    - 只可以从文本中提取信息。要保持原始文本的完整性。
    - 直接输出最终结果即可，不要给出任何解释或说明。

    请根据上述要求，一步步思考，逐步完成任务。

    ---
    原始文本如下：

    """,

    "merging_shows_list_user_prompt":"""

    原始json文本，分两次从同一个演出节目单图片OCR识别文本中提取的演出节目单信息。两次提取的结果可能存在错漏，请根据两次提取的结果，互为参照，将两个结果合并为一个完整的演出节目单。
    【注意！！！】直接返回最终的json数据，不要给出任何解释或者说明。
    【注意！！！】不要重复相同的节目信息。
    【重要！！！】保持原有的json格式与节点格式，不要改变。

    ---

    原始文本如下：

    """,


    "shows_list_judgment_user_prompt": """
        
        请判断原始文本的json数据`name`节点是演出节目清单名称信息，还是演职人员信息？
        
        - 如果全部`name`节点是 **演职人员**信息 ，则返回：{"result": "否"}
        - 如果全部`name`节点信息是**演出节目名称**信息，则返回：{"result": "是"}

        - 判断条件是 `name`节点信息
        - 不要给出任何解释或者说明，直接返回要求json格式的结果。

        ---
        原始文本如下：
    """,

    "shows_list_extractor_user_prompt": """

        ## 任务与目标
        
        原始文本的json数据部分`name`节点信息是 **演出节目名称**信息，另一部分`name`是**演职人员**信息。
        
        - 【注意！！！】`castDescription`节点存储的就是演职人员信息，不作为判断依据。也不是单独删除 `castDescription`节点。
        - 判断条件是`name`
        - 如果某一组{"name": "", "castDescription": "", "description": ""}的 `name`节点是是**演职人员**信息，则删除这一组节点。
        - 保留原始的json数据格式，只删除演职人员信息的节点。
        - 请直接输出优化后的json数据，不要给出任何解释或者说明。

        ## 样例

        原始文本如下：
        ```
        {
            "individualPerformances": [
                {
                    "name": "Individual Performance Name",
                    "castDescription": "Cast member description string",
                    "description": "detailed description"
                },
                {
                    "name": "Cast Name",
                    "castDescription": "Cast description string",
                    "description": "detailed description"
                }
                    // More individual performances can be added here
        }

        ```

        输出结果如下：
        ```
        {
            "individualPerformances": [
                {
                    "name": "Individual Performance Name",
                    "castDescription": "Cast member description string",
                    "description": "detailed description"
                }
                    // More individual performances can be added here
        }

        ```

        ## 约束与限制
        - 【重要！！！】是根据`name`内容判断是节目信息，还是演职人员信息。
        - 【重要！！！】如果`name`的内容是演职人员信息，则删除这个整个一组节点。也就是{"name": "", "castDescription": "", "description": ""}。

        ---
        原始文本如下：
    """,

    "add_spaces_user_prompt": """

    ## 任务说明
    原始文本是json格式，内容是演出节目单信息，包括 演出名称（name），演职人员描述（castDescription）和节目介绍（description）。
    - `name`节点内容是演出名称。可能存在少量节目编号等不是名称的信息。只需将节目编号去除即可，其他信息保留。 
    - `castDescription`的节点信息是节目所有演职人员姓名和角色职责的描述。原始内容中不同实体对象之间缺少适当空格或标点符号，导致阅读时会有混乱。
    请根据实际情况（语义内容）对`castDescription`节点的内容进行格式化整理。即在不同实体之间适当添加标点符号（如分号等），便于阅读。
    
    【注意事项】
    - 【重要！！！】只对`name`和`castDescription`的节点内容进行适合的格式优化。不可以删除节点内容。
    - 【重要！！！】请保持原始有json格式不变，不要做任何修改。
    - 【重要！！！】原始`name`和`castDescription`的节点有内容，则输出结果也必须保留，只对内容格式进行优化。
    - 直接输出优化后的完整结果，不要给出任何的解释或说明。

    ---
    原始文本如下：

    """,

    "shows_list_contains_user_prompt": """
    ## 角色与任务说明
    你是一个专业信息提取专家，能够从演出节目单图片的ocr文本中判断是否包含演出节目清单信息。

    ### OCR文本内容说明

    具体内容可能包括：
    （1）演出人员、团体的介绍及其角色或职责；
    （2）具体演出节目列表以及对应的演出人员；
    （3）演出剧目的剧情或背景介绍等信息。
    （4）【重要】不同对象之间关系通过 **相邻原则** 文本坐标体现。即OCR识别的垂直和水平坐标（`top`和`left`）相邻时，文本（`words`）可能具有从属对应关系。


    ### 演出节目的分级说明

    从演出的规模和结构来定义:

    (a) 集合演出:
    - 是一场完整的演出活动
    - 通常包含多个不同的表演节目或艺术形式
    - 可能持续数小时，甚至跨越一整天或多天
    - 例如:音乐节、艺术节、晚会等

    (b) 章节或半场演出:
    - 是一场较大演出中的一个部分
    - 通常有特定的主题或风格
    - 例如:音乐会的上半场、戏剧的某一幕、舞蹈表演的某一组曲

    (c) 单个演出节目:
    - 是最小的表演单位
    - 通常只包含一个特定的表演内容
    - 例如:一首歌曲、一个舞蹈、一个魔术表演、一个小品等

    这三个类别是从大到小的层级关系：集合演出可能包含多个章节或半场演出，而每个章节或半场演出又可能包含多个单个演出节目。

    ## 目标与任务
    - 首先，请根据用户提供的集合演出名称，分析其所属的图片和坐标信息。
    - 根据分析得到的图片以及对应的坐标信息，判断此场集合演出是否包括【章节或半场演出】、【单个演出节目】
    - 如果判断有【章节或半场演出】，则返回：{"sectionsOrActs": "yes", "individualPerformances": "yes"}
    - 如果判断没有【章节或半场演出】，再判断是否有【单个演出节目】。如果有，则返回：{"sectionsOrActs": "no", "individualPerformances": "yes"}
    - 如果判断没有【章节或半场演出】，再判断是否有【单个演出节目】。如果没有，则返回：{"sectionsOrActs": "no", "individualPerformances": "no"}

    ## 限制与约束
    - 【重要！！！】严格按照要求输出json格式的结果
    - 直接输出最终的json数据，不要给出任何解释或者说明。

    ---
    原始文本如下：

    """,

    "shows_list_user_prompt": """
    从原始文本中，提取集合演出的演出节目单信息后按照层次结构信息进行输出。

    ---

    """,

    "strcuture_shows_list_user_prompt": """
    第一段

    ---

    """,

    "shows_to_festivals_user_prompt": """
    ## 任务与目标

    请根据提供的 `原始的OCR文本`，判断 `演出节目`属于哪一场`集合演出`，以及是否属于某个`章节或半场演出`。
    
    【重要！！！】判断后，请按照输出示例输出json格式结果，不要给出任何多余的内容。
    【注意！！！】根据相邻原则，即根据OCR原文的markdown格式（属于同一个H1）和文本垂直和水平坐标（`top`和`left`）判断集合演出和演出节目信息是从属关系。

    ## 演出节目的分级说明

    从演出的规模和结构来定义:

    (a) 集合演出:
    - 是一场完整的演出活动
    - 通常包含多个不同的表演节目或艺术形式
    - 可能持续数小时，甚至跨越一整天或多天
    - 例如:音乐节、艺术节、晚会等

    (b) 章节或半场演出:
    - 是一场较大演出中的一个部分
    - 通常有特定的主题或风格
    - 例如:音乐会的上半场、戏剧的某一幕、舞蹈表演的某一组曲

    (c) 单个演出节目:
    - 是最小的表演单位
    - 通常只包含一个特定的表演内容
    - 例如:一首歌曲、一个舞蹈、一个魔术表演、一个小品等

    这三个类别是从大到小的层级关系：集合演出可能包含多个章节或半场演出，而每个章节或半场演出又可能包含多个单个演出节目。

    ## 输出json格式如下：

    ### 判断有属于某个章节或半场演出
    ```
    {"performingEvent": "XXXXXX", "sectionsOrActs": "XXXXX"}
    ```

    ### 无法判断或者不属于某个章节或半场演出

    ```
    {"performingEvent": "XXXXXX", "sectionsOrActs": null}

    ```
    ---

    """,

    "single_shows_to_festivals_user_prompt": """
    ## 任务与目标

    请根据提供的 `原始的OCR文本`，判断 `演出节目`是否属于某个`章节或半场演出`。
    
    【重要！！！】判断后，请按照输出示例输出json格式结果，不要给出任何多余的内容。
    【注意！！！】根据相邻原则，即根据OCR原文的markdown格式（属于同一个H1）和文本垂直和水平坐标（`top`和`left`）判断集合演出和演出节目信息是从属关系。

    ## 演出节目的分级说明

    从演出的规模和结构来定义:

    (a) 集合演出:
    - 是一场完整的演出活动
    - 通常包含多个不同的表演节目或艺术形式
    - 可能持续数小时，甚至跨越一整天或多天
    - 例如:音乐节、艺术节、晚会等

    (b) 章节或半场演出:
    - 是一场较大演出中的一个部分
    - 通常有特定的主题或风格
    - 例如:音乐会的上半场、戏剧的某一幕、舞蹈表演的某一组曲

    (c) 单个演出节目:
    - 是最小的表演单位
    - 通常只包含一个特定的表演内容
    - 例如:一首歌曲、一个舞蹈、一个魔术表演、一个小品等

    这三个类别是从大到小的层级关系：集合演出可能包含多个章节或半场演出，而每个章节或半场演出又可能包含多个单个演出节目。

    ## 输出json格式如下：

    ### 判断有属于某个章节或半场演出
    ```
    {"sectionsOrActs": "XXXXX"}
    ```

    ### 无法判断或者不属于某个章节或半场演出

    ```
    {"sectionsOrActs": "null"}

    ```
    ---

    """,

    "casts_list_user_prompt": """
    ## 角色与任务说明
    你是一个专业信息提取专家，能够根据从演出节目单图片的ocr文本中提取 **演职人员** 信息。

    ### OCR文本内容说明

    具体内容可能包括：
    （1）演出人员、团体的介绍及其角色或职责；
    （2）具体演出节目列表以及对应的演出人员；
    （3）演出剧目的剧情或背景介绍等信息。
    （4）【重要】不同对象之间关系通过 **相邻原则** 文本坐标体现。即OCR识别的垂直和水平坐标（`top`和`left`）相邻时，文本（`words`）可能具有从属对应关系。

    ### 演出节目的分级说明

    从演出的规模和结构来定义:

    (a) 集合演出:
    - 是一场完整的演出活动
    - 通常包含多个不同的表演节目或艺术形式
    - 可能持续数小时，甚至跨越一整天或多天
    - 例如:音乐节、艺术节、晚会等

    (b) 章节或半场演出:
    - 是一场较大演出中的一个部分
    - 通常有特定的主题或风格
    - 例如:音乐会的上半场、戏剧的某一幕、舞蹈表演的某一组曲

    (c) 单个演出节目:
    - 是最小的表演单位
    - 通常只包含一个特定的表演内容
    - 例如:一首歌曲、一个舞蹈、一个魔术表演、一个小品等

    这三个类别是从大到小的层级关系：集合演出可能包含多个章节或半场演出，而每个章节或半场演出又可能包含多个单个演出节目。

    ## 目标与任务

    - 【注意！！！】首先需要排除单个演出节目的演职人员信息。可以根据相邻原则排除单个演出节目的演职人员的信息。
    - 只提取与集合演出有关的演职人员信息。
    - 按照示例的json格式组织数据，不要给出任何多余的解释与说明。
    - 【重要！！！】如果没有提取到对应的节点信息，则为 `null`。

    
    ## 输出要求与示例
    
    【重要】输出格式为 json, 具体样例如下：

    ### 有节目单列表信息，返回结果

    ```
    {
        "performanceCasts": [
            {
                "name": "Cast or Crew's Name",
                "role": "Cast or Crew's role",
                "description": "Descriptive information on the cast and crew"
            },
            {
                "name": "Cast or Crew's Name",
                "role": "Cast or Crew's role",
                "description": "Descriptive information on the cast and crew"
            }
            // More casts can be added here
        ]
    }
    ```

    ### 没有演职人员信息，返回空列表

    ```
        {
        "performanceCasts": []
        }
    ```

    ## 限制与约束
    【注意事项】
    - 【重要！！！】如果没有演出节目单列表信息，则返回空列表。
    - 【重要！！！】如果`role`、`description`的信息没有提取到，则为 `null`。
    - 只可以从文本中提取信息。要保持原始文本的完整性。
    - 直接输出最终结果即可，不要给出任何解释或说明。

    请根据上述要求，一步步思考，逐步完成任务。

    ---
    原始文本如下：
    """,

    "name_optimizer_prompt": """
    请将以下名字列表格式化，每个名字用分号分隔。请返回json格式，样例如下：
    ```
    {
        "result": "name1 ; name2 ; name3"
    }
    ```
    
    ---

    原始文本如下：
    """,

    "cast_description_optimizer_prompt": """
    ## 任务说明

    这是一段节目演出图片中ocr提取的节目演职人员信息。内容类型：
    （1）角色扮演说明：节目演出人员与扮演的节目角色
    （2）演出职责说明：演出人员与职责。包括但不限于乐器演奏、演唱、伴舞、表演等。

    请根据【内容类型】，按照如下规则提取json格式。
    【重要！！！】直接输出最终的json结果，不要给出任何解释或说明。

    （1）角色扮演说明。则提取规则：
        ```
        {
            "rolePlayDescriptions": [
                {
                "actorName": "Actor 1",
                "characterName": "Character 1"
                },
                {
                "actorName": "Actor 2",
                "characterName": "Character 2"
                }
            ]
        }
        ```

    （2）演出职责说明，提取规则：
    ```
    {
    "performanceResponsibilities": [
            {
                "performerName": "",
                "responsibility": ""
            },
            {
                "performerName": "",
                "responsibility": ""
            }
        ]
    }
    ```
    ---
    提取原内容如下：

    """

}