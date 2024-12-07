document.addEventListener('DOMContentLoaded', async () => {
    try {
        // 初始化星空背景
        const starfield = new Starfield('starfield');
        
        // 初始化可视化
        new SecondaryVisualization();
        
        console.log('Secondary page initialization complete');
    } catch (error) {
        console.error('Secondary page initialization error:', error);
    }
});
