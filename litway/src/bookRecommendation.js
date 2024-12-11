// GLM API configuration
const API_URL = 'http://XXX/v1/chat/completions';
const API_KEY = 'sk-XXX';

// 分析读者的借阅历史
async function recommendBooks(reader) {
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
            model: "deepseek",
            messages: [
                {
                    role: "system",
                    content: "根据用户的借阅图书历史，分析用户的阅读偏好，然后根据阅读偏好，联网检索豆瓣图书，推荐近半年评分较高的相关图书【今年是2024年】。如果没有主题相近的图书推荐，则推荐最近半年豆瓣图书评分较高的任一本书即可。直接返回“作者：书名”即可，不要有任何多余的信息或标记。\n" +
                    "注意：只推荐一本2024年出版的图书即可"
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
        window.particleText.options.fontSize = window.innerWidth * 0.03;
        window.particleText.options.color = '#65B4C9',
        window.particleText.setText(analysisResult);

    } catch (error) {
        console.error('分析读者历史时出错:', error);
        window.particleText.setText('让我们一起探索更多有趣的书籍吧！');
    }
}

// 导出函数供其他模块使用
export { recommendBooks };