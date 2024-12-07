class LibraryVisualization {
    constructor(containerId) {
        this.container = d3.select(`#${containerId}`);
        // 确保容器是空的
        this.container.html('');
        
        this.width = this.container.node().offsetWidth;
        this.height = this.container.node().offsetHeight;
        this.currentLevel = 0;
        this.currentPath = [];
        this.data = null;
        this.simulation = null;
        
        this.svg = this.container
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height);
            
        this.g = this.svg.append('g')
            .attr('transform', `translate(${this.width/2},${this.height/2})`);

        // Add zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
            });
        
        this.svg.call(this.zoom);

        // Set initial zoom transform
        const initialScale = 0.8;  // 增加初始缩放比例
        const initialTransform = d3.zoomIdentity
            .translate(this.width/2, this.height/2)
            .scale(initialScale);
        this.svg.call(this.zoom.transform, initialTransform);
            
        // Add tooltip with space theme styles
        this.tooltip = this.container
            .append('div')
            .attr('class', 'tooltip')
            .style('position', 'absolute')
            .style('visibility', 'hidden')
            .style('opacity', '0')
            .style('background-color', 'rgba(13, 17, 23, 0.3)')  // 更透明的背景
            .style('color', '#fff')
            .style('border', '1px solid rgba(100, 200, 255, 0.15)')  // 更透明的边框
            .style('border-radius', '8px')
            .style('padding', '12px')
            .style('font-family', 'Arial, sans-serif')
            .style('font-size', '14px')
            .style('pointer-events', 'none')
            .style('box-shadow', '0 0 15px rgba(100, 200, 255, 0.1)')  // 更柔和的阴影
            .style('backdrop-filter', 'blur(8px)')  // 增加模糊效果
            .style('transition', 'opacity 0.2s ease-in-out')
            .style('z-index', '1000');
        
        window.addEventListener('resize', () => this.resize());
        
        console.log('Visualization initialized:', {
            width: this.width,
            height: this.height
        });
    }

    async loadData() {
        try {
            // 如果已经加载过数据，先清除现有的可视化
            if (this.data) {
                this.g.selectAll('.node').remove();
                if (this.simulation) {
                    this.simulation.stop();
                    this.simulation = null;
                }
            }
            
            const response = await fetch('data/library_data.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const rawData = await response.json();
            console.log('Raw data loaded:', rawData);
            
            // 更严格的数据验证
            if (!rawData.data || !Array.isArray(rawData.data.level1) || rawData.data.level1.length === 0) {
                throw new Error('Invalid or empty data structure');
            }
            
            // 验证每个节点的必要属性
            rawData.data.level1.forEach(node => {
                if (!node.name || typeof node.value !== 'number') {
                    console.warn('Invalid node data:', node);
                }
            });
            
            // Store complete data in localStorage before assigning to this.data
            console.log('Storing complete data in localStorage...');
            const dataToStore = JSON.stringify(rawData);
            localStorage.setItem('completeLibraryData', dataToStore);
            
            // Verify the data was stored correctly
            const storedData = localStorage.getItem('completeLibraryData');
            if (!storedData) {
                throw new Error('Failed to store data in localStorage');
            }
            console.log('Data stored successfully. Size:', dataToStore.length, 'bytes');
            
            this.data = rawData;
            console.log('Processed data:', this.data);

            // 立即开始可视化
            this.visualizeLevel(0);
        } catch (error) {
            console.error('Error loading data:', error);
            this.container.append('div')
                .attr('class', 'error-message')
                .text('Error loading data. Please check the console for details.');
        }
    }

    resize() {
        this.width = this.container.node().offsetWidth;
        this.height = this.container.node().offsetHeight;
        this.svg
            .attr('width', this.width)
            .attr('height', this.height);
        this.g.attr('transform', `translate(${this.width/2},${this.height/2})`);
        if (this.simulation) this.simulation.force('center', d3.forceCenter());
    }

    visualizeLevel(level, parentNode = null) {
        console.log('Visualizing level:', level, 'with parent:', parentNode);
        if (level >= CONFIG.levels.maxDepth) {
            console.warn('Max depth reached:', level);
            return;
        }
        
        this.currentLevel = level;
        if (parentNode) {
            console.log('Setting current path with parent:', parentNode);
            this.currentPath = this.currentPath.slice(0, level - 1);
            this.currentPath.push(parentNode);
        } else {
            console.log('Resetting current path');
            this.currentPath = [];
        }
        
        let nodes = this.getNodesForLevel(level, parentNode);
        if (nodes.length === 0) {
            console.warn('No nodes found for level:', level);
            return;
        }
        
        console.log('Updating visualization with nodes:', nodes.length);
        this.updateVisualization(nodes);
    }

    getNodesForLevel(level, parentNode) {
        console.log('Getting nodes for level:', level, 'parentNode:', parentNode);
        let nodes = [];
        
        try {
            if (level === 0) {
                // 对于第一层，直接使用level1数据
                nodes = this.data.data.level1;
                console.log('Level 1 nodes:', nodes);
            } else if (parentNode && Array.isArray(parentNode.children)) {
                // 对于其他层级，使用父节点的children
                nodes = parentNode.children;
                console.log(`Children nodes for ${parentNode.name}:`, nodes);
            }
            
            // 确保每个节点都有必要的属性
            nodes = nodes.map((node, index) => ({
                ...node,
                index,
                x: node.x || (Math.random() - 0.5) * this.width * 0.8,
                y: node.y || (Math.random() - 0.5) * this.height * 0.8,
                children: Array.isArray(node.children) ? node.children : []
            }));
            
        } catch (error) {
            console.error('Error getting nodes:', error);
            nodes = [];
        }
        
        console.log('Processed nodes:', nodes);
        return nodes;
    }

    updateVisualization(nodes) {
        console.log('Updating visualization with nodes:', nodes);
        
        // 停止之前的模拟
        if (this.simulation) {
            this.simulation.stop();
            this.simulation = null;
        }
        
        // 清除所有现有节点
        this.g.selectAll('.node').remove();
        
        if (!Array.isArray(nodes) || nodes.length === 0) {
            console.warn('No valid nodes to visualize');
            return;
        }
        
        // Calculate total value for percentage
        const totalValue = d3.sum(nodes, d => d.value || 0);
        
        // Safely calculate maxValue using d3.max
        const maxValue = d3.max(nodes, d => d.value || 0) || 1;
        
        const radiusScale = d3.scaleSqrt()
            .domain([0, maxValue])
            .range([CONFIG.bubble.minRadius, CONFIG.bubble.maxRadius]);

        // 创建力导向图模拟
        this.simulation = d3.forceSimulation(nodes)
            .force('charge', d3.forceManyBody()
                .strength(d => -Math.pow(radiusScale(d.value), 1.5) * 2)  // 更柔和的排斥力
                .distanceMin(10)  // 最小距离
                .distanceMax(300)  // 最大作用距离
            )
            .force('collide', d3.forceCollide()
                .radius(d => radiusScale(d.value) + 10)  // 保持适当间距
                .strength(0.9)
                .iterations(3)
            )
            .force('center', d3.forceCenter(0, 0).strength(0.08))  // 轻微的中心引力
            // 添加径向力，让大气泡趋向外圈，小气泡居中
            .force('radial', d3.forceRadial(
                d => Math.pow(radiusScale(d.value), 0.8) * 2,  // 基于大小的目标半径
                0, 0
            ).strength(0.3))
            .alphaDecay(0.01)  // 让布局变化更平滑
            .velocityDecay(0.3)  // 减小阻尼使运动更自然
            .on('tick', () => {
                nodeElements.attr('transform', d => `translate(${d.x},${d.y})`);
            });

        // 初始位置设置
        nodes.forEach(d => {
            if (!d.x || !d.y) {
                const angle = Math.random() * Math.PI * 2;
                const distance = Math.random() * Math.min(this.width, this.height) * 0.1;
                d.x = Math.cos(angle) * distance;
                d.y = Math.sin(angle) * distance;
            }
        });
            
        // 保存节点的最终位置（用于搜索时保持位置）
        setTimeout(() => {
            nodes.forEach(node => {
                node.savedX = node.x;
                node.savedY = node.y;
            });
        }, 2000);

        // 使用join模式来处理节点
        const nodeElements = this.g.selectAll('.node')
            .data(nodes, d => d.name)
            .join(
                enter => {
                    const enterSelection = enter.append('g')
                        .attr('class', 'node')
                        .style('cursor', 'pointer')
                        .style('opacity', 0);

                    enterSelection.append('circle')
                        .attr('r', d => radiusScale(d.value))
                        .style('fill', d => {
                            const colorScheme = CONFIG.colors.initialColors[d.initial] || CONFIG.colors.initialColors.default;
                            return colorScheme.base;
                        })
                        .style('fill-opacity', CONFIG.bubble.opacity)
                        .style('stroke', d => {
                            const colorScheme = CONFIG.colors.initialColors[d.initial] || CONFIG.colors.initialColors.default;
                            return colorScheme.glow;
                        })
                        .style('stroke-width', CONFIG.bubble.strokeWidth);

                    enterSelection.append('text')
                        .text(d => d.name)
                        .attr('dy', '.3em')
                        .style('text-anchor', 'middle')
                        .style('fill', '#ffffff')
                        .style('font-size', d => {
                            const radius = radiusScale(d.value);
                            return Math.min(radius * 0.4, 16) + 'px';
                        });

                    enterSelection.transition()
                        .duration(CONFIG.animation.duration)
                        .style('opacity', 1);

                    return enterSelection;
                },
                update => update,
                exit => exit.transition()
                    .duration(CONFIG.animation.duration)
                    .style('opacity', 0)
                    .remove()
            );

        // 添加交互事件
        nodeElements
            .on('mouseover', (event, d) => {
                const node = d3.select(event.currentTarget);
                const currentInitial = d.initial;
                
                // 高亮当前节点
                node.select('circle')
                    .style('filter', CONFIG.bubble.glow.hover)
                    .style('fill-opacity', 1);
                
                // 处理所有节点
                this.g.selectAll('.node').each(function(otherD) {
                    const otherNode = d3.select(this);
                    if (otherD.initial === currentInitial) {
                        // 高亮相同initial的节点
                        otherNode.select('circle')
                            .style('filter', CONFIG.bubble.glow.hover)
                            .style('fill-opacity', 1);
                    } else {
                        // 淡化其他节点
                        otherNode.select('circle')
                            .style('filter', 'none')
                            .style('fill-opacity', 0.2);
                    }
                });
                
                const tooltipContent = this._createTooltipContent(d, totalValue);
                this.tooltip
                    .html(tooltipContent)
                    .style('visibility', 'visible')
                    .style('opacity', '1')
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 10) + 'px');
            })
            .on('mousemove', (event) => {
                this.tooltip
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 10) + 'px');
            })
            .on('mouseout', (event, d) => {
                // 恢复所有节点的样式
                this.g.selectAll('.node').each(function() {
                    const node = d3.select(this);
                    node.select('circle')
                        .style('filter', CONFIG.bubble.glow.normal)
                        .style('fill-opacity', CONFIG.bubble.opacity);
                });
                
                this.tooltip
                    .style('visibility', 'hidden')
                    .style('opacity', '0');
            })
            .on('click', (event, d) => {
                console.log('Clicked topic:', d);
                
                // Get topic data directly from the clicked node
                const topicData = {
                    name: d.name,
                    value: d.value,
                    children: d.children || []
                };
                
                if (!topicData || !topicData.children || topicData.children.length === 0) {
                    console.error('No valid topic data found for:', d.name);
                    alert('No data found for this topic. Please try another topic.');
                    return;
                }
                
                console.log('Storing topic data:', topicData);
                localStorage.setItem('currentTopicData', JSON.stringify(topicData));
                
                // Redirect to second.html with topic name as query parameter
                window.location.href = `second.html?topic=${encodeURIComponent(d.name)}`;
            });
    }

    _createTooltipContent(node, totalValue) {
        const value = node.value;
        const percentage = totalValue > 0 ? ((value / totalValue) * 100).toFixed(1) : 0;
        
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
                    ${node.name}
                </div>
                <div style="display: flex; flex-direction: column; gap: 4px; font-family: '润植家如印奏章楷';">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: rgba(255, 255, 255, 0.7);">借阅量：</span>
                        <span style="color: rgba(100, 200, 255, 0.9); font-weight: bold;">${value.toLocaleString()}</span>
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
}

// 当DOM加载完成后初始化可视化
document.addEventListener('DOMContentLoaded', () => {
    // 创建可视化实例并暴露到全局作用域
    window.visualization = new LibraryVisualization('visualization');
    window.visualization.loadData();
});
