// 为LibraryVisualization类添加主题导航功能
class TopicNavigation {
    constructor(visualization) {
        this.visualization = visualization;
        this.setupNavigationEvents();
    }

    setupNavigationEvents() {
        // 获取返回按钮元素
        const backButton = d3.select('#back-button');
        if (!backButton.empty()) {
            backButton.on('click', () => this.handleBackNavigation());
        }

        // 监听自定义主题点击事件
        this.visualization.container.node().addEventListener('topicClick', (event) => {
            event.stopPropagation();
            const topicNode = event.detail;
            console.log('Topic clicked:', topicNode);
            this.handleTopicClick(topicNode);
        });
    }

    handleTopicClick(topicNode) {
        console.log('Handling topic click:', topicNode);
        // 检查节点是否有子主题
        if (topicNode.children && topicNode.children.length > 0) {
            console.log('Navigating to secondary level for topic:', topicNode.name);
            
            // 将选中的主题数据存储到localStorage
            localStorage.setItem('selectedTopic', JSON.stringify(topicNode));
            
            // 跳转到二级主题页面
            window.location.href = `second.html?topic=${encodeURIComponent(topicNode.name)}`;
        } else {
            console.log('Node has no children');
        }
    }

    handleBackNavigation() {
        // 只有在二级主题页面时才能返回
        if (this.visualization.currentLevel === 1) {
            // 清空路径
            this.visualization.currentPath = [];
            this.visualization.currentLevel = 0;
            
            // 更新面包屑
            this.visualization.updateBreadcrumb();
            
            // 返回一级主题页面
            this.visualization.visualizeLevel(0);
        }
    }
}

// 在LibraryVisualization类初始化完成后初始化导航功能
document.addEventListener('DOMContentLoaded', () => {
    // 等待visualization实例创建完成后初始化导航
    const initNavigation = () => {
        if (window.visualization) {
            window.topicNavigation = new TopicNavigation(window.visualization);
        } else {
            setTimeout(initNavigation, 100);
        }
    };
    
    initNavigation();
});
