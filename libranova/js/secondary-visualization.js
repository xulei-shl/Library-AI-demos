class SecondaryVisualization {
    constructor() {
        this.container = d3.select('#secondary-visualization');
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.setupVisualization();
        this.loadData();
        
        // 添加tooltip
        this.tooltip = this.container
            .append('div')
            .attr('class', 'tooltip')
            .style('position', 'absolute')
            .style('visibility', 'hidden')
            .style('opacity', '0')
            .style('background-color', 'rgba(13, 17, 23, 0.3)')
            .style('color', '#fff')
            .style('border', '1px solid rgba(100, 200, 255, 0.15)')
            .style('border-radius', '8px')
            .style('padding', '12px')
            .style('font-family', 'Arial, sans-serif')
            .style('font-size', '14px')
            .style('pointer-events', 'none')
            .style('box-shadow', '0 0 15px rgba(100, 200, 255, 0.1)')
            .style('backdrop-filter', 'blur(8px)')
            .style('transition', 'opacity 0.2s ease-in-out')
            .style('z-index', '1000');
    }

    setupVisualization() {
        this.svg = this.container
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height);
            
        this.g = this.svg.append('g')
            .attr('transform', `translate(${this.width/2},${this.height/2})`);

        // 添加缩放功能
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
            });
        
        this.svg.call(this.zoom);
        
        // 设置初始缩放
        const initialScale = 0.5;
        const initialTransform = d3.zoomIdentity
            .translate(this.width/2, this.height/2)
            .scale(initialScale);
        this.svg.call(this.zoom.transform, initialTransform);
    }

    async loadData() {
        console.log('Loading secondary visualization data...');
        const urlParams = new URLSearchParams(window.location.search);
        const topicName = urlParams.get('topic');
        console.log('Topic name from URL:', topicName);
        
        if (!topicName) {
            console.error('No topic name provided');
            this.showError('No topic name provided in URL');
            return;
        }

        // Update breadcrumb with current topic name
        const currentTopicSpan = document.getElementById('current-topic');
        if (currentTopicSpan) {
            currentTopicSpan.textContent = decodeURIComponent(topicName);
        }

        try {
            // Check if data exists in localStorage, if not, load it
            const completeDataStr = localStorage.getItem('completeLibraryData');
            if (!completeDataStr) {
                console.log('Library data not found in localStorage, loading it now...');
                await DataLoader.loadLibraryData();
            }

            // Now try to get the topic data
            const topicData = DataLoader.getSecondaryTopicData(topicName);
            
            if (!topicData) {
                console.error('No data found for topic:', topicName);
                this.showError(`No data found for topic: ${topicName}`);
                return;
            }

            // Process and visualize the data
            this.processData(topicData);
        } catch (error) {
            console.error('Error loading visualization data:', error);
            this.showError(`Error loading data: ${error.message}`);
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: rgba(255, 0, 0, 0.1);
            color: #ff4444;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #ff4444;
            text-align: center;
            font-family: Arial, sans-serif;
        `;
        errorDiv.textContent = message;
        this.container.node().appendChild(errorDiv);
    }

    _createTooltipContent(d, totalValue) {
        const percentage = ((d.value / totalValue) * 100).toFixed(2);
        
        const tooltipContent = `
            <div style="
                background: rgba(13, 17, 23, 0.3);
                backdrop-filter: blur(8px);
                border: 1px solid rgba(100, 200, 255, 0.15);
                border-radius: 8px;
                padding: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2), 0 0 20px rgba(100, 200, 255, 0.1);
            ">
                <div style="margin-bottom: 8px; font-size: 16px; color: rgba(100, 200, 255, 0.9); font-weight: bold; font-family: '润植家如印奏章楷';">
                    ${d.name}
                </div>
                <div style="display: flex; flex-direction: column; gap: 4px; font-family: '润植家如印奏章楷';">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: rgba(255, 255, 255, 0.7);">借阅量：</span>
                        <span style="color: rgba(100, 200, 255, 0.9); font-weight: bold;">${d.value.toLocaleString()}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: rgba(255, 255, 255, 0.7);">占比：</span>
                        <span style="color: rgba(100, 200, 255, 0.9); font-weight: bold;">${percentage}%</span>
                    </div>
                </div>
            </div>
        `;
        
        return tooltipContent;
    }

    processData(topicData) {
        console.log('Processing data:', topicData);
        if (!topicData.children) {
            console.error('No children data found:', topicData);
            return;
        }

        const nodes = topicData.children.map(d => ({
            ...d,
            x: (Math.random() - 0.5) * this.width * 0.8,
            y: (Math.random() - 0.5) * this.height * 0.8
        }));

        // 计算总值和最大值
        const totalValue = d3.sum(nodes, d => d.value || 0);
        const maxValue = d3.max(nodes, d => d.value || 0) || 1;
        
        // 设置气泡大小比例尺
        const radiusScale = d3.scaleSqrt()
            .domain([0, maxValue])
            .range([50, 100]); // 增加气泡的最小和最大半径

        // 创建力导向图
        this.simulation = d3.forceSimulation(nodes)
            .force('center', d3.forceCenter(0, 0).strength(0.05))  // 减小中心力的强度
            .force('charge', d3.forceManyBody().strength(-1500))  // 增加排斥力的强度
            .force('collide', d3.forceCollide().radius(d => radiusScale(d.value) + 2))  // 减小碰撞半径
            .force('x', d3.forceX(0).strength(0.2))  // 增加 x 方向的力的强度
            .force('y', d3.forceY(0).strength(0.2))  // 增加 y 方向的力的强度
            .on('tick', () => this.ticked());

        // 清除现有节点
        this.g.selectAll('.node').remove();

        // 创建节点
        const nodeElements = this.g.selectAll('.node')
            .data(nodes)
            .join('g')
            .attr('class', 'node')
            .style('cursor', 'pointer');

        // 添加圆形
        nodeElements.append('circle')
            .attr('r', d => radiusScale(d.value))
            .style('fill', (d, i) => {
                const colorScheme = {
                    base: d3.schemeCategory10[i % 10],
                    glow: d3.color(d3.schemeCategory10[i % 10]).brighter(0.5)
                };
                return colorScheme.base;
            })
            .style('fill-opacity', 0.3)
            .style('stroke', (d, i) => {
                const colorScheme = {
                    base: d3.schemeCategory10[i % 10],
                    glow: d3.color(d3.schemeCategory10[i % 10]).brighter(0.5)
                };
                return colorScheme.glow;
            })
            .style('stroke-width', 2)
            .style('filter', 'url(#glow)');

        // 添加文本
        nodeElements.append('text')
            .text(d => d.name)
            .attr('dy', '.3em')
            .style('text-anchor', 'middle')
            .style('fill', '#ffffff')
            .style('font-size', d => {
                const radius = radiusScale(d.value);
                const length = d.name.length;
                return Math.min(radius * 1.5 / length, 16) + 'px';
            });

        // 添加悬浮效果
        nodeElements
            .on('mouseover', (event, d) => {
                this.tooltip
                    .style('visibility', 'visible')
                    .style('opacity', '1')
                    .html(this._createTooltipContent(d, totalValue))
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 10) + 'px');

                // 高亮当前气泡
                d3.select(event.currentTarget)
                    .select('circle')
                    .style('filter', 'url(#glow-highlight)');
            })
            .on('mousemove', (event) => {
                this.tooltip
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 10) + 'px');
            })
            .on('mouseout', (event) => {
                this.tooltip
                    .style('visibility', 'hidden')
                    .style('opacity', '0');

                // 恢复正常状态
                d3.select(event.currentTarget)
                    .select('circle')
                    .style('filter', 'url(#glow)');
            });

        // 添加SVG滤镜
        const defs = this.svg.append('defs');
        
        // 普通发光效果
        const glowFilter = defs.append('filter')
            .attr('id', 'glow')
            .attr('x', '-50%')
            .attr('y', '-50%')
            .attr('width', '200%')
            .attr('height', '200%');

        glowFilter.append('feGaussianBlur')
            .attr('stdDeviation', '3')
            .attr('result', 'coloredBlur');

        const glowMerge = glowFilter.append('feMerge');
        glowMerge.append('feMergeNode').attr('in', 'coloredBlur');
        glowMerge.append('feMergeNode').attr('in', 'SourceGraphic');

        // 高亮发光效果
        const glowHighlightFilter = defs.append('filter')
            .attr('id', 'glow-highlight')
            .attr('x', '-50%')
            .attr('y', '-50%')
            .attr('width', '200%')
            .attr('height', '200%');

        glowHighlightFilter.append('feGaussianBlur')
            .attr('stdDeviation', '5')
            .attr('result', 'coloredBlur');

        const glowHighlightMerge = glowHighlightFilter.append('feMerge');
        glowHighlightMerge.append('feMergeNode').attr('in', 'coloredBlur');
        glowHighlightMerge.append('feMergeNode').attr('in', 'SourceGraphic');
    }

    ticked() {
        this.g.selectAll('.node')
            .attr('transform', d => `translate(${d.x},${d.y})`);
    }
}

// 页面加载完成后初始化可视化
document.addEventListener('DOMContentLoaded', () => {
    new SecondaryVisualization();
});
