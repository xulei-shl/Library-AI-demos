## 项目功能

1. 爬取 Code4Lib 和 SWIB 会议的日程信息：报告名、报告摘要、链接，附件链接
   
2. 调用 Deepl 或百度翻译接口，将报告名、报告摘要翻译成中文
3. 调用 GLM-4-air，根据报告名和摘要，生成关键词
   - 特别关注某类主题的，可在 `prompts.py`的提示词中强调 