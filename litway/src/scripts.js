// 这里可以添加后续的动态文字粒子图填充逻辑
document.addEventListener('DOMContentLoaded', function() {
    const modelContainer = document.getElementById('modelContainer');
    // 后续可以在这里添加动态文字粒子图的逻辑
});

// 自动滚动代码块效果
function setupCodeScroll() {
    const codeScroll = document.getElementById('codeScroll');
    if (codeScroll) {
        // 创建代码内容的克隆以实现无缝滚动
        const clone = codeScroll.cloneNode(true);
        codeScroll.parentNode.appendChild(clone);

        // 固定速度的函数
        function updateScrollSpeed(element) {
            const fixedSpeed = 70; // 固定速度
            element.style.transition = 'animation-duration 0.5s'; // 添加过渡效果
            element.style.animationDuration = `${fixedSpeed}s`;
        }

        // 初始化动画
        codeScroll.style.animation = 'naturalScroll 0.5s linear infinite';
        clone.style.animation = 'naturalScroll 0.5s linear infinite';
        clone.style.transform = 'translateY(100%)';

        // 定期更新速度
        setInterval(() => {
            updateScrollSpeed(codeScroll);
            updateScrollSpeed(clone);
        }, 3000); // 每3秒更新一次速度

        // 初始调用一次以设置初始速度
        updateScrollSpeed(codeScroll);
        updateScrollSpeed(clone);

        // 当动画完成一次循环时，重置位置
        codeScroll.addEventListener('animationiteration', () => {
            codeScroll.style.transform = 'translateY(0)';
            clone.style.transform = 'translateY(0)';
        });
    }
}

// 在页面加载完成后初始化滚动效果
document.addEventListener('DOMContentLoaded', setupCodeScroll);

document.addEventListener('DOMContentLoaded', function() {
    const codeScrollElement = document.getElementById('codeScroll');

    // 读取 src/demoshow.js 文件内容
    fetch('src/demoshow.js')
        .then(response => response.text())
        .then(data => {
            codeScrollElement.textContent = data;
        })
        .catch(error => {
            console.error('Error reading demoshow.js:', error);
            codeScrollElement.textContent = 'Error loading code.';
        });
});