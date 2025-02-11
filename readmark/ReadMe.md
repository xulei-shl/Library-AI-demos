## 项目简介

悦读印记（ReadMark）

![](https://xulei-pic-1258542021.cos.ap-shanghai.myqcloud.com/mdpic/20250205153759.png)

## 项目自动化流程设计
1. 根据读者信息获取到当年度的借阅数据详细

2. 然后根据这些信息分析读者的年度阅读成就与阅读偏好，生成一张精美的阅读成就分享卡片

2.1 卡片中的`年度阅读进度`、`阅读成就`使用基于明确规则的python代码生成，而非大模型
2.2 `近期阅读主题`，先用规则提取对应的借阅数据后，再作为输入调用大模型生成准确结果
2.3 `擅长阅读领域`则根据完整的年度借阅信息由大模型生成
2.4 考虑到上下文窗口限制，可能读者借阅数据可能需要进行去重、分段等预处理

3. 头像生成逻辑：根据信息，由大模型生成图像生成提示词，再调用图像大模型生成图像

4. 二维码图像，根据大模型生成卡片的配色要求再单独调用工具生成

5. 最终卡片生成，参考`AI 摘要`卡片的方法，HTML 代码中变化的部分作为示例提交给大模型生成，其他不变的部分作为固定代码，最后与大模型返回的代码拼接在一起。一方面减少输入的 token，另一方面，确保生成结果的稳定。

## 仓库代码说明
1. 因为无法自动获取读者信息，因此本仓库中只提供实施思路，以及核心的两个 Chatbot 提示词，**卡片生成**与**头像提示词生成**。
2. 这两个提示词用于自动化流程中时，需要根据流程设计进行调整或者拆解

## 补充说明

1. 落地实践环节，因为涉及到读者个人信息的使用，可以在活动中说明，然后读者知情同意后主动发起请求，再进行卡片生成。
1.1 提交申请时，可以附加个表单，请读者提供更多维度的信息，用于后续的分析
2. 分阶段运行：可以在卡片与头像生成环节前置一个 Agent，先用基础信息进行用户阅读成就画像，后续卡片与图像生成环节用这个生成结果。确保每个环节都是专注于单一任务？？
3. 为确保生成效果的准确性，可以考虑增加一个审核 Agent，对生成的卡片进行审核。
4. 如果可以拿到更多的信息，可以更进一步分析读者的阅读偏好和阅读特征，并提供可视化。
