import { analyzeReaderHistory } from './readerAnalysis.js';
import { recommendBooks } from './bookRecommendation.js';


// 读取 readers.json 数据
async function fetchReaderData() {
    try {
        const response = await fetch('../data/readers.json');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return await response.json();
    } catch (error) {
        console.error('Error loading reader data:', error);
        return null;
    }
}

// 处理读者卡号输入
async function handleReaderInput() {
    const inputElement = document.querySelector('.prompt-input');
    if (!inputElement) {
        console.error('Input element not found');
        return;
    }
    
    const readerData = await fetchReaderData();
    
    if (!readerData) {
        console.error('Failed to load reader data.');
        return;
    }
    
    inputElement.addEventListener('change', async function() {
        const readerId = this.value.trim();
        const reader = readerData[readerId];
        
        if (reader && reader.name) {
            window.particleText.setText(`你好，${reader.name}！`);
            // 3秒后更新文本，使用较小字号
            setTimeout(() => {
                window.particleText.options.fontSize = window.innerWidth * 0.04;
                window.particleText.options.color = '#B5B5B5'; // 设置文本颜色为蓝色
                window.particleText.setText('让我看看你的阅读品味咋样', { initialEffect: 'smooth' });
                setTimeout(() => {
                    analyzeReaderHistory(reader);
                    setTimeout(() => {
                        window.particleText.options.fontSize = window.innerWidth * 0.03;
                        window.particleText.options.color = '#B5B5B5';
                        window.particleText.setText('我为你推荐了一本书，希望你会喜欢', { initialEffect: 'smooth' });
                        setTimeout(() => {
                            recommendBooks(reader);
                        }, 3000);
                    }, 5000);
                }, 3000);
            }, 3000);
        } else {
            window.particleText.options.color = '#EB8585';
            window.particleText.setText('未找到读者信息', { initialEffect: 'smooth' });
            setTimeout(() => {
                window.particleText.options.color = '#65B4C9';
                window.particleText.setText('你好，世界！', { initialEffect: 'smooth' });
            }, 3000);
        }
    });
}

// 等待 particleText 初始化完成后再初始化读者输入处理
function initializeWhenReady() {
    if (window.particleText) {
        handleReaderInput();
    } else {
        setTimeout(initializeWhenReady, 100);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initializeWhenReady);
