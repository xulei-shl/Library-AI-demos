document.addEventListener('DOMContentLoaded', async () => {
    try {
        // 初始化星空背景
        const starfield = new Starfield('starfield');
        
        // 初始化可视化
        const visualization = new LibraryVisualization('visualization');
        
        // 加载数据并开始可视化
        await visualization.loadData();
        
        console.log('Initialization complete');
    } catch (error) {
        console.error('Initialization error:', error);
    }
});
