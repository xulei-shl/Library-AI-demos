# 项目简介

**书径指南（LitWay Compass）**

LitWay Compass 是一个面向图书馆用户的交互式 AI Demo，通过 AI 技术实现实时交互。

主要功能：根据读者的借阅历史，分析用户阅读倾向，给出阅读身份标签。并推荐相关图书

<img src="https://xulei-pic-1258542021.cos.ap-shanghai.myqcloud.com/mdpic/1733978970772.png" width="200" height="300">

<img src="https://xulei-pic-1258542021.cos.ap-shanghai.myqcloud.com/mdpic/1733979072278.png" width="200" height="300">


https://github.com/user-attachments/assets/9ec9ca1a-c6f1-4605-94d9-cc0007996a86

> 项目设计之处的使用场景是：图书馆大厅之类的地方，有一个交互屏幕，放上读者卡后，读取读者个人信息和书目信息，利用 AI 实现交互

> 推荐的功能，简单粗暴之间调用大模型的联网检索功能实现，并没有结合图书馆的数据进行推荐。懒得弄了

## 运行

1. API 配置
   - GLM API： `src/readerAnalysis.js`的`API_URL`和`API_KEY`
   - DeepSeek：`src/bookRecommendation.js`的`API_URL`和`API_KEY`
2. python -m http.server 8000



## 致谢

1. [Touchdesigner+comfyUI生成3D点云交互技术说明_哔哩哔哩_bilibili](https://www.bilibili.com/video/BV18t421J7rg/?spm_id_from=333.880.my_history.page.click&vd_source=1d3b1df26617554772f26729180cff38)
2. [JavaScript实现在HTML中的粒子文字特效_html写一个粒子扩散-CSDN博客](https://blog.csdn.net/m0_46700215/article/details/126963561)
