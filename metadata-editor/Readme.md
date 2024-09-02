![](https://xulei-pic-1258542021.cos.ap-shanghai.myqcloud.com/mdpic/%E8%8A%82%E7%9B%AE%E5%8D%95%E5%AE%9E%E4%BD%93%E6%8F%90%E5%8F%96%E4%B8%8E%E7%BC%96%E8%BE%91.png)


## API配置

大模型 API、知识库 API 和提示词都是用的本地 `.json` 存储。需要在 `jsondata`文件夹新建 `llm_settings.json` 、`knowledge_settings.json` 和 `prompts.json` 文件。样例如下：

1. llm_settings.json
   
   ```
   [
    {
        "name": "智谱/GLM-4-Flash",
        "api_key": "",
        "api_url": "https://open.bigmodel.cn/api/paas/v4/",
        "model": "glm-4-flash"
    },
    {
        "name": "siliconflow/Qwen2-7B-Instruct",
        "api_key": "",
        "api_url": "https://api.siliconflow.cn/v1/",
        "model": "Qwen/Qwen2-7B-Instruct"
    }
    ]
   ```

2. knowledge_settings.json
   ```
    [
        {
            "name": "Dify/节目单",
            "api_key": "",
            "api_url": "https://api.dify.ai/v1/chat-messages"
        }
    ]
    ```

3. prompts.json
   ```
   [
    {
        "label": "询问",
        "description": ""
    },
    {
        "label": "解释",
        "description": "请用通俗的语言解释下这个内容"
    },
    {
        "label": "翻译",
        "description": "请将内容翻译成英文"
    },
    {
        "label": "OCR纠错",
        "description": "请根据中文语义、语法角度，判断文本中是否有OCR识别错误的内容"
    }
    ]
   ```
