// GLM API configuration
const API_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions';
const API_KEY = 'XXX';

// 分析读者的借阅历史
async function analyzeReaderHistory(reader) {
    try {
        // 从 readers.json 获取读者的借阅历史
        const response = await fetch('../data/readers.json');
        const readersData = await response.json();

        // 查找对应的读者记录
        const readerRecord = Object.values(readersData).find(r => r.name === reader.name);
        if (!readerRecord) {
            throw new Error('未找到读者记录');
        }

        // 获取借阅的书籍列表
        const loadBooks = readerRecord['load-books'] || [];
        const recentBooks = loadBooks.slice(0, 10).map(book => book.title).join('、');

        // 准备 GLM 请求数据
        const requestData = {
            model: "glm-4",
            messages: [
                {
                    role: "system",
                    content: "根据用户的借阅图书历史，分析用户的阅读偏好，然后根据阅读领域从下列候选列表中选择合适的阅读身份标签，如 `文学漫步者`、`科技探索者`等。不需要其他任何解释或说明或符号标记，直接给出最终阅读身份标签即可。\n" +
                    "候选标签：\n" +
                    "人文漫步者：对哲学、宗教、伦理学和美学有兴趣的读者。\n" +
                    "思维探索者：对逻辑学、思维科学和心理学有好奇心的读者。\n" +
                    "社会观察家：关注社会学、人口学和民族学，对社会现象有敏锐洞察力的读者。\n" +
                    "法律爱好者：对法律和国际法有热情，关注法律动态的读者。\n" +
                    "军事迷：对军事战略、战役和战术着迷，关注军事技术的读者。\n" +
                    "经济智囊：对经济学、经济管理和经济计划有独到见解的读者。\n" +
                    "会计达人：对会计和审计有深入研究，精通财务知识的读者。\n" +
                    "农业关注者：关注农业经济和世界农业经济，对农业发展有见解的读者。\n" +
                    "工业瞭望者：对工业经济和世界工业经济有研究，关注工业动态的读者。\n" +
                    "金融追随者：对金融、银行和保险有兴趣，关注金融市场的读者。\n" +
                    "文化鉴赏家：对文化、艺术和历史有深厚兴趣，热衷于文化探索的读者。\n" +
                    "教育关注者：关注教育领域，对教育发展和教育理论有见解的读者。\n" +
                    "语言学习者：对各种语言有学习热情，热衷于语言探索的读者。\n" +
                    "文学爱好者：对文学作品有热爱，喜欢阅读和文学研究的读者。\n" +
                    "艺术欣赏者：对绘画、雕塑、音乐和舞蹈等艺术形式有欣赏力的读者。\n" +
                    "历史探索者：对历史和文物考古有兴趣，喜欢探索历史奥秘的读者。\n" +
                    "地理爱好者：对地理学和地图有兴趣，喜欢探索世界各地的读者。\n" +
                    "科学求知者：对自然科学和数学有求知欲，喜欢科学探索的读者。\n" +
                    "医学关注者：对医学和健康有关注，对医学知识有学习热情的读者。\n" +
                    "农业实践者：对农业科学和植物保护有实践经验，关注农业技术的读者。\n" +
                    "交通关注者：对交通运输和航空航天有兴趣，关注交通发展的读者。\n" +
                    "安全卫士：对安全科学和环境科学有关注，关注安全和环境保护的读者。\n" +
                    "技术极客：对各种工业技术和科学有浓厚兴趣，喜欢技术探索的读者。\n" +
                    "综合知识追求者：对各个领域的知识都有追求，喜欢阅读综合性图书的读者。\n" +
                    "矿业研究者：对矿业工程和相关技术有研究，关注矿业发展的读者。\n" +
                    "能源关注者：对石油、天然气工业和能源动力工程有关注，关注能源利用的读者。\n" +
                    "建筑爱好者：对建筑科学和水利工程有兴趣，关注建筑和水利发展的读者。\n" +
                    "工业分析师：对冶金工业、机械工业和武器工业等有研究，关注工业动态的读者。\n" +
                    "信息科技达人：对无线电电子学、电信技术和自动化技术等有深入了解，关注信息技术发展的读者。\n" +
                    "化学工业关注者：对化学工业和轻工业等有关注，关注化学工业发展的读者。\n" +
                    "AI探索者：对人工智能领域有浓厚兴趣，关注AI技术发展的读者。\n" +
                    "计算先锋：对计算机科学和编程有深入研究，热衷于技术探索的读者。\n" +
                    "小说狂热者：对小说有极度热爱，喜欢沉浸在虚构世界中的读者。\n" +
                    "诗歌爱好者：对诗歌有独特欣赏力，喜欢诗歌的韵律和情感表达的读者。\n" +
                    "股票投资者：对股票市场有深入了解，关注股市动态和投资机会的读者。\n" +
                    "--- \n" +
                    "如果上述候选标签没有合适的，你也可以提出新的标签。" 
                },
                {
                    role: "user",
                    content: `这位读者最近借阅的书籍有：${recentBooks}`
                }
            ]
        };

        // 调用 GLM API
        const glmResponse = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        // 检查响应状态
        if (!glmResponse.ok) {
            throw new Error(`GLM API 请求失败，状态码: ${glmResponse.status}`);
        }

        // 获取分析结果
        const glmData = await glmResponse.json();
        const analysisResult = glmData.choices[0].message.content;

        // 更新粒子文本
        window.particleText.options.fontSize = window.innerWidth * 0.05;
        window.particleText.options.color = '#65B4C9',
        window.particleText.setText(analysisResult);

    } catch (error) {
        console.error('分析读者历史时出错:', error);
        window.particleText.setText('让我们一起探索更多有趣的书籍吧！');
    }
}

// 导出函数供其他模块使用
export { analyzeReaderHistory };