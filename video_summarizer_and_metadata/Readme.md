# 图书馆讲座视频增强描述与小红书文案生成

## 场景与功能：

读取本地文件夹（当天日期文件夹）下的所有子文件夹，将讲座视频转录为音频后，再利用 GLM 进行转录文本优化，总结和小红书文案生成，结果保存到本地 markdown 文件中。
   
## 工具
1. [Zulko/moviepy](https://github.com/Zulko/moviepy)

   - 视频转音频

2. ModelScople的[Paraformer语音识别-中文-通用-16k-离线-large-长音频版](https://modelscope.cn/models/iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch)
   - 使音频文本提取
3. 智谱 glm-4-air API 
   - 转录文本优化
   - 文本总结
   - 小红书文案生成
## 预警

1. 讲座视频都是长视频，token消耗较大
   
2. 利用 GLM 进行转录文本的优化，输出格式不稳定
   - 也许进行转录文本的 LLM 优化并没有必要。后续可以直接将原始转录文本按照句子进行整理就可以了

## 致谢

1. [jianchang512/zh_recogn](https://github.com/jianchang512/zh_recogn)

## TODO？

1. 根据转录文本撰写 SEO 友好的博客文章？[Agent101：将YouTube视频转化为SE0友好的文章](https://fw7qiozbnjr.feishu.cn/wiki/WiAnwBMXRip9orkYv54c7v5Zncr)
2. [【莱森】Dify AI 教程｜Dify 一键生成多尺寸运营封面与跨平台文案_哔哩哔哩_bilibili](https://www.bilibili.com/video/BV1Kx4ae8Eyz/?vd_source=1d3b1df26617554772f26729180cff38)