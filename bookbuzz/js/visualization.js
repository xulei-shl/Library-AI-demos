// 初始化可视化
class BubbleVisualization {
    constructor(containerId) {
        this.container = d3.select(containerId);
        this.width = this.container.node().getBoundingClientRect().width;
        this.height = this.container.node().getBoundingClientRect().height;
        this.svg = this.container.append('svg')
            .attr('width', this.width)
            .attr('height', this.height);
        
        // 添加时间刻度组
        this.timeScaleGroup = this.svg.append('g')
            .attr('class', 'time-scale')
            .attr('transform', this.calculateScaleTransform(this.level3X, 40));  // 从三级节点位置开始

        // 定义不同层级的x坐标位置
        this.level1X = 50;    // 第一层（书名）
        this.level2X = 350;   // 第二层（索书号） - 增加与第一层的距离
        this.level3X = 650;   // 第三层（借阅记录）

        // 存储全局最新和最旧借阅时间
        this.latestDate = null;
        this.oldestDate = null;

        // 添加时间刻度状态标记
        this.timeScaleShown = false;

        // 莫兰迪色系
        this.colors = [
            // 主节点使用的暖色调 (前三个使用新的色系)
            '#94B49F', '#CEA0AA', '#B0A8B9', '#A69B8D', '#8B8178',
            // 二级节点使用的清新色调
            '#A8D8B9', '#81C7D4', '#7DB9DE', '#8B81C3', '#B481BB'
        ];

        // 添加节点状态跟踪
        this.nodeStates = {
            selectedBook: null,
            openCallNumbers: new Set(),
            openBorrowRecords: new Set()
        };

        // 添加tooltip
        this.tooltip = d3.select('body')
            .append('div')
            .attr('class', 'tooltip')
            .style('position', 'absolute')
            .style('opacity', 0)
            .style('display', 'flex')
            .style('align-items', 'center')
            .style('z-index', '9999'); // Ensure high z-index

        // Fetch book image mapping from JSON file
        this.bookImageMap = {};
        fetch('../data/book_image_map.json')
            .then(response => response.json())
            .then(data => {
                this.bookImageMap = data;
            })
            .catch(error => {
                console.error('Error loading book image map:', error);
                // Fallback to a default mapping if loading fails
                this.bookImageMap = {
                    '红楼梦': 'honglou-1.jpeg',
                    '西游记': 'xiyou.jpeg',
                    '史记': 'shiji.jpeg',
                    '古文观止': 'guwen.jpeg',
                    '射雕英雄传': 'shediao.jpeg',
                    '庄子': 'zhuangzi.jpeg',
                    '平凡的世界': 'pingfan-1.jpeg',
                    '卡拉马佐夫兄弟': 'kala-1.jpeg',
                    '悉达多': 'xidaduo-1.jpeg',
                    '毛泽东选集': 'maoxuan.jpeg'
                };
            });

        this.simulation = d3.forceSimulation()
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('charge', d3.forceManyBody().strength(100))
            .force('collide', d3.forceCollide().radius(d => d.radius + 2));
    }

    async loadData() {
        try {
            const data = await d3.json('data/filtered_data.json');
            this.processData(data);
        } catch (error) {
            console.error('Error loading data:', error);
        }
    }

    processData(rawData) {
        this.data = Object.entries(rawData)
            .map(([title, info]) => ({
                id: title,
                title,
                totalBorrows: info.总次数,
                monthlyBorrowings: info['月份借阅量'] || {},
                callNumbers: Object.entries(info.索书号)
                    .map(([callNumber, records]) => ({
                        callNumber,
                        records: records.map(record => ({
                            readerId: record.读者卡号,
                            borrowDate: record.出库时间
                        }))
                    }))
            }))
            .sort((a, b) => b.totalBorrows - a.totalBorrows)
            .slice(0, 10);

        // 计算全局最新和最旧借阅时间
        let allDates = [];
        this.data.forEach(book => {
            book.callNumbers.forEach(cn => {
                allDates = allDates.concat(cn.records.map(r => new Date(r.borrowDate)));
            });
        });
        this.latestDate = new Date(Math.max.apply(null, allDates));
        this.oldestDate = new Date(Math.min.apply(null, allDates));
        this.timeRange = this.latestDate - this.oldestDate;

        this.initializeVisualization();
    }

    initializeVisualization() {
        const baseRadius = Math.min(this.width, this.height) / 25;
        
        // 为每个数据创建一个组，初始位置在左侧且不可见
        const bubbleGroups = this.svg.selectAll('.bubble-group')
            .data(this.data)
            .enter()
            .append('g')
            .attr('class', 'bubble-group')
            .style('opacity', 0)
            .attr('transform', (d, i) => `translate(${this.level1X}, ${this.height * (i + 1) / 11})`);

        // 在组内添加圆圈
        bubbleGroups.append('circle')
            .attr('class', 'bubble level1-bubble')  // 添加level1-bubble类
            .attr('r', baseRadius)
            .attr('fill', (d, i) => this.colors[i]);

        // 在组内添加文本
        bubbleGroups.append('text')
            .attr('class', 'bubble-text')
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .style('fill', '#fff')
            .style('font-weight', 'bold')
            .text((d, i) => i + 1);

        // 设置交互
        this.setupInteractions(bubbleGroups);

        // 依次显示节点的动画
        bubbleGroups.each((d, i, nodes) => {
            d3.select(nodes[i])
                .transition()
                .delay(i * 300)  // 每个节点延迟300ms出现
                .duration(500)
                .style('opacity', 1)
                .on('end', () => {
                    // 当最后一个节点动画完成时，随机展开一个节点
                    if (i === this.data.length - 1) {
                        setTimeout(() => this.autoExpandRandomNode(), 500);
                    }
                });
        });
    }

    async autoExpandRandomNode() {
        // 随机选择一个节点
        const randomIndex = Math.floor(Math.random() * this.data.length);
        const randomNode = this.data[randomIndex];
        
        // 模拟点击事件来展开节点
        const group = this.svg.selectAll('.bubble-group').filter((d, i) => i === randomIndex);
        const event = { currentTarget: group.node() };
        this.handleBubbleClick(event, randomNode);

        // 增加等待时间，确保二级节点完全展开
        setTimeout(() => {
            // 获取所有索书号节点
            const callNumberGroups = this.svg.selectAll('.call-number-group');
            
            // 为每个索书号节点依次触发展开借阅记录，添加间隔时间
            callNumberGroups.each((d, i, nodes) => {
                setTimeout(() => {
                    const callNumberEvent = { currentTarget: nodes[i] };
                    this.showBorrowRecords(callNumberEvent, d);
                }, i * 300); // 每个节点间隔300ms展开
            });
        }, 2500); // 等待2.5秒确保二级节点已完全展开
    }

    setupInteractions(bubbleGroups) {
        bubbleGroups
            .on('mouseover', (event, d) => {
                const group = d3.select(event.currentTarget);
                const bubble = group.select('.bubble');
                
                // 只有非一级节点才改变大小
                if (!bubble.classed('level1-bubble')) {
                    bubble.transition()
                        .duration(300)
                        .attr('r', bubble.attr('r') * 1.2);
                }

                this.showTooltip(d, event);
            })
            .on('mouseout', (event, d) => {
                const group = d3.select(event.currentTarget);
                const bubble = group.select('.bubble');
                
                // 只有非一级节点才改变大小
                if (!bubble.classed('level1-bubble')) {
                    bubble.transition()
                        .duration(300)
                        .attr('r', bubble.attr('r') / 1.2);
                }

                this.tooltip.transition()
                    .duration(500)
                    .style('opacity', 0);
            })
            .on('click', (event, d) => this.handleBubbleClick(event, d));
    }

    async showTooltip(d, event) {
        // Create a filename-friendly version of the book title
        let imageFilename;
        if (this.bookImageMap[d.title]) {
            imageFilename = this.bookImageMap[d.title];
        } else {
            // If book image map is not loaded yet, wait for it to load
            await new Promise(resolve => {
                const intervalId = setInterval(() => {
                    if (this.bookImageMap[d.title]) {
                        clearInterval(intervalId);
                        resolve();
                    }
                }, 100);
            });
            imageFilename = this.bookImageMap[d.title] || 'logo_shl.jpg';
        }
        
        this.tooltip.transition()
            .duration(200)
            .style('opacity', .9);
        
        this.tooltip.html(`
            <div class="tooltip-image-container">
                <img src="css/img/${imageFilename}" alt="${d.title}" class="tooltip-book-image" 
                     onerror="this.style.display='none';">
            </div>
            <div class="tooltip-text-container">
                <strong class="tooltip-book-title">书名：</strong> <span class="tooltip-book-title-value">${d.title}</span><br>
                <br>
                <strong class="tooltip-book-title">借阅总次数：</strong> <span class="tooltip-book-title-value">${d.totalBorrows}</span><br>
                <br>
                <strong class="tooltip-book-title">索书号数量：</strong> <span class="tooltip-book-title-value">${d.callNumbers.length}</span>
            </div>
        `)
        .style('left', (event.pageX + 50) + 'px')
        .style('top', (event.pageY - 28) + 'px');
    }

    handleBubbleClick(event, d) {
        const group = d3.select(event.currentTarget);
        const bubble = group.select('.bubble');
        const isSelected = bubble.classed('selected');

        // 如果当前书已被选中，收起所有节点
        if (isSelected) {
            this.resetView();
            this.nodeStates.selectedBook = null;
            this.nodeStates.openCallNumbers.clear();
            this.nodeStates.openBorrowRecords.clear();
            return;
        }

        // 重置所有气泡
        this.svg.selectAll('.bubble').classed('selected', false);
        bubble.classed('selected', true);
        this.nodeStates.selectedBook = d.id;
        
        // 展开详细视图并自动展开所有层级
        this.showDetailView(d);
    }

    showDetailView(selectedBook) {
        // 移除任何现有的月份借阅显示
        this.svg.selectAll('.monthly-borrowing-display').remove();

        // 检查选定的书籍是否有月份借阅数据
        if (selectedBook.monthlyBorrowings) {
            // 创建月份借阅显示组，使用时间刻度的位置和宽度
            const monthlyBorrowingGroup = this.svg.append('g')
                .attr('class', 'monthly-borrowing-display')
                .attr('transform', this.calculateScaleTransform(this.level2X));

            // 使用三级节点的x坐标计算范围
            const baseX = this.level2X;
            const minOffset = 100;
            const maxOffset = 900;
            
            // 计算每个月份段的起始和结束位置
            const getMonthSegment = (month) => {
                const segmentWidth = (maxOffset - minOffset) / 12;  // 将总长度等分为12段
                const adjustedMonth = month - 6;
                const start = baseX + minOffset + (adjustedMonth - 1) * segmentWidth;
                const end = start + segmentWidth;
                return { start, end };
            };

            // 垂直位置调整到页面上部
            const verticalPosition = 13;  // 距离顶部16像素

            // 定义月份顺序
            const monthOrder = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

            // 定义稍微亮一些的莫兰迪色系
            const morlandiColors = [
                '#B0C4B1', '#E7C8B4', '#A4C2A5', '#D1B3C4', 
                '#B5C6D1', '#C4B3A4', '#A5B4C2', '#C4A5B3', 
                '#B3C4A5', '#D1C4B3', '#A5C4B3', '#C4B5A5'
            ];

            // 添加月份借阅量数据
            monthOrder.forEach((month, index) => {
                const borrowCount = selectedBook.monthlyBorrowings[month] || 0;
                
                // 计算每个月份的段落
                const segment = getMonthSegment(index + 1);

                // 创建月份借阅量组
                const monthBorrowGroup = monthlyBorrowingGroup.append('g')
                    .attr('class', 'month-borrow-group')
                    .style('opacity', 0);

                // 创建背景矩形
                const backgroundRect = monthBorrowGroup.append('rect')
                    .attr('x', segment.start)
                    .attr('y', verticalPosition - 5)
                    .attr('width', 0)  // 初始宽度为0，用于动画
                    .attr('height', 15)
                    .attr('fill', morlandiColors[index])
                    .attr('opacity', 0.2);

                // 创建文本
                const borrowText = monthBorrowGroup.append('text')
                    .attr('x', (segment.start + segment.end) / 2)
                    .attr('y', verticalPosition + 10)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', '12px')
                    .attr('fill', morlandiColors[index])
                    .attr('opacity', 0)
                    .text(borrowCount);

                // 添加动画效果
                backgroundRect
                    .transition()
                    .delay(index * 200)
                    .duration(1000)
                    .attr('width', segment.end - segment.start);

                monthBorrowGroup
                    .transition()
                    .delay(index * 200)
                    .duration(1000)
                    .style('opacity', 4);

                borrowText
                    .transition()
                    .delay(index * 200)
                    .duration(1000)
                    .attr('opacity', 4);
            });
        }

        // 移动所有气泡组到左侧，使用统一的过渡效果
        const bookIndex = this.data.findIndex(d => d.id === selectedBook.id);
        const finalBookY = this.height * (bookIndex + 1) / 11;

        // 移动所有气泡组
        this.svg.selectAll('.bubble-group')
            .transition()
            .duration(750)
            .ease(d3.easeCubicInOut)
            .attr('transform', (d, i) => `translate(${this.level1X}, ${this.height * (i + 1) / 11})`);

        // 创建索书号气泡组，但先不添加到DOM
        const callNumberData = selectedBook.callNumbers.map((d, i) => ({
            data: d,
            y: this.height * (i + 1) / (selectedBook.callNumbers.length + 1)
        }));

        // 随机打乱顺序
        const shuffledData = [...callNumberData].sort(() => Math.random() - 0.5);
        
        // 分批显示索书号节点和连接线
        const nodeDelay = 300; // 每个节点的延迟时间
        
        // 逐个创建和动画显示节点及其连接线
        shuffledData.forEach((item, sequenceIndex) => {
            const currentDelay = sequenceIndex * nodeDelay;
            
            // 创建节点组，初始位置在第一层节点位置
            const group = this.svg.append('g')
                .attr('class', 'call-number-group')
                .attr('transform', `translate(${this.level1X}, ${finalBookY})`)
                .style('opacity', 0);

            // 添加圆圈，初始时完全透明
            const circle = group.append('circle')
                .attr('class', 'bubble call-number-bubble')
                .attr('r', Math.max(12, Math.sqrt(item.data.records.length) * 3))
                .attr('fill', this.colors[5 + (sequenceIndex % 5)])
                .style('opacity', 0)
                .on('mouseover', (event) => {
                    circle.transition()
                        .duration(300)
                        .attr('r', circle.attr('r') * 1.2);

                    this.tooltip.transition()
                        .duration(200)
                        .style('opacity', .9);
                    this.tooltip
                        .attr('class', 'tooltip tooltip-secondary')
                        .html(`
                        <div class="tooltip-text-container">
                            <strong class="tooltip-book-title">索书号：</strong> <span class="tooltip-book-title-value">${item.data.callNumber}</span><br>
                            <br>
                            <strong class="tooltip-book-title">借阅次数：</strong> <span class="tooltip-book-title-value">${item.data.records.length}</span><br>
                        </div>`)
                        .style('left', (event.pageX + 50) + 'px')
                        .style('top', (event.pageY - 28) + 'px');
                })
                .on('mouseout', (event) => {
                    circle.transition()
                        .duration(300)
                        .attr('r', circle.attr('r') / 1.2);

                    this.tooltip.transition()
                        .duration(500)
                        .style('opacity', 0);
                });

            // 计算连接线的路径
            const sourceX = this.level1X;
            const sourceY = finalBookY;
            const targetX = this.level2X;
            const targetY = item.y;
            
            // 使用书籍的总借阅次数计算源节点的半径
            const sourceRadius = Math.max(8, Math.sqrt(selectedBook.totalBorrows) * 3);
            const targetRadius = 8;
            
            const dx = targetX - sourceX;
            const dy = targetY - sourceY;
            const angle = Math.atan2(dy, dx);
            
            const sourceStartX = sourceX + sourceRadius * Math.cos(angle);
            const sourceStartY = sourceY + sourceRadius * Math.sin(angle);
            const targetEndX = targetX - targetRadius * Math.cos(angle);
            const targetEndY = targetY - targetRadius * Math.sin(angle);
            
            const controlPoint1X = sourceStartX + (targetEndX - sourceStartX) * 0.5;
            const controlPoint1Y = sourceStartY;
            const controlPoint2X = sourceStartX + (targetEndX - sourceStartX) * 0.5;
            const controlPoint2Y = targetEndY;

            // 创建连接线，初始时完全透明
            const path = this.svg.append('path')
                .attr('class', 'connection-line')
                .attr('d', `M ${sourceStartX},${sourceStartY} ` +
                          `C ${controlPoint1X},${controlPoint1Y} ` +
                          `${controlPoint2X},${controlPoint2Y} ` +
                          `${targetEndX},${targetEndY}`)
                .style('fill', 'none')
                .style('stroke', '#ccc')
                .style('stroke-width', 1.5)
                .style('opacity', 0);

            // 使用Promise来确保动画顺序
            setTimeout(() => {
                // 先显示连接线
                path.transition()
                    .duration(500)
                    .style('opacity', 0.6)
                    .end()
                    .then(() => {
                        // 连接线显示完成后，再显示节点
                        group.style('opacity', 1);
                        circle.transition()
                            .duration(500)
                            .style('opacity', 1);

                        // 最后移动节点到目标位置
                        return group.transition()
                            .duration(500)
                            .attr('transform', `translate(${this.level2X}, ${targetY})`)
                            .end();
                    })
                    .then(() => {
                        // 动画完成后展开借阅记录
                        const event = { currentTarget: group.node() };
                        this.showBorrowRecords(event, item.data);
                    });
            }, currentDelay);
        });
        
        // 绘制时间刻度
        this.drawTimeScale(true);
    }

    showBorrowRecords(event, callNumberData) {
        const group = d3.select(event.currentTarget);
        const bubble = group.select('.call-number-bubble');
        
        // 更新节点状态并创建有效的CSS类名
        const safeBookId = this.nodeStates.selectedBook.replace(/[^a-zA-Z0-9]/g, '_');
        const safeCallNumber = callNumberData.callNumber.replace(/[^a-zA-Z0-9]/g, '_');
        const callNumberKey = `${safeBookId}-${safeCallNumber}`;
        this.nodeStates.openCallNumbers.add(callNumberKey);

        // 获取当前索书号节点的位置
        const transform = group.attr('transform');
        const match = transform.match(/translate\(([\d.]+),\s*([\d.]+)\)/);
        const sourceY = parseFloat(match[2]);

        // 按时间排序借阅记录
        const sortedRecords = [...callNumberData.records].sort((a, b) => 
            new Date(a.borrowDate) - new Date(b.borrowDate));

        // 创建借阅记录气泡，使用安全的类名
        const recordBubbles = this.svg.selectAll(`.record-bubble-${callNumberKey}`)
            .data(sortedRecords)
            .enter()
            .append('g')
            .attr('class', `record-bubble-group record-bubble-${callNumberKey}`)
            .attr('transform', `translate(${this.level2X}, ${sourceY})`)
            .style('opacity', 0);

        // 添加固定大小的圆圈
        recordBubbles.append('circle')
            .attr('class', 'record-circle')
            .attr('r', 10)  // 增加三级节点的基础大小
            .attr('fill', (d, i) => this.colors[i % this.colors.length]);

        recordBubbles
            .on('mouseover', (event, d) => {
                const bubble = d3.select(event.currentTarget).select('circle');
                bubble.transition()
                    .duration(300)
                    .attr('r', 12);

                this.tooltip.transition()
                    .duration(200)
                    .style('opacity', .9);
                this.tooltip
                    .attr('class', 'tooltip tooltip-tertiary')
                    .html(`<strong>借阅时间：</strong>${d.borrowDate}`)
                    .style('left', (event.pageX + 50) + 'px')
                    .style('top', (event.pageY - 28) + 'px');
            })
            .on('mouseout', (event, d) => {
                const bubble = d3.select(event.currentTarget).select('circle');
                bubble.transition()
                    .duration(300)
                    .attr('r', 10);

                this.tooltip.transition()
                    .duration(500)
                    .style('opacity', 0);
            });

        // 绘制时间刻度并开始动画
        this.drawTimeScale(true);

        // 处理每条借阅记录
        sortedRecords.forEach((d, i) => {
            const node = d3.select(recordBubbles.nodes()[i]);
            const borrowDate = new Date(d.borrowDate);
            const timeDiff = this.latestDate - borrowDate;
            const timeRatio = this.timeRange === 0 ? 1 : 1 - (timeDiff / this.timeRange);
            
            // 调整三级节点的布局参数
            const verticalPaddingTop = 80;  // 增加顶部padding
            const verticalPaddingBottom = 80;  // 增加底部padding
            const availableHeight = this.height - verticalPaddingTop - verticalPaddingBottom;
            const baseSpacing = 60;  // 增加基础间距
            const dynamicSpacing = Math.max(baseSpacing, availableHeight / Math.min(sortedRecords.length, 15));
            
            // 计算可见节点数量
            const maxNodesInView = Math.floor(availableHeight / dynamicSpacing);
            const visibleNodes = Math.min(maxNodesInView, sortedRecords.length);
            
            // 计算起始位置，使节点在视图中均匀分布
            let targetY;
            if (sortedRecords.length <= maxNodesInView) {
                // 如果节点数量不多，在可用空间内均匀分布
                const totalSpacing = (sortedRecords.length - 1) * dynamicSpacing;
                const startY = verticalPaddingTop + (availableHeight - totalSpacing) / 2;
                targetY = startY + i * dynamicSpacing;
            } else {
                // 如果节点数量过多，使用时间位置进行分布
                const timePosition = i / (sortedRecords.length - 1);
                const effectiveHeight = availableHeight - dynamicSpacing;
                targetY = verticalPaddingTop + timePosition * effectiveHeight;
            }
            
            // 存储目标位置
            d.targetX = this.level2X + (100 + (900 - 100) * Math.pow(timeRatio, 0.6));
            d.targetY = targetY;

            // 创建连接线
            const dx = d.targetX - this.level2X;
            const dy = targetY - sourceY;
            const angle = Math.atan2(dy, dx);
            
            const sourceRadius = 8;
            const targetRadius = 8;
            
            const sourceStartX = this.level2X + sourceRadius * Math.cos(angle);
            const sourceStartY = sourceY + sourceRadius * Math.sin(angle);
            const targetEndX = d.targetX - targetRadius * Math.cos(angle);
            const targetEndY = targetY - targetRadius * Math.sin(angle);
            
            const controlPoint1X = sourceStartX + (targetEndX - sourceStartX) * 0.5;
            const controlPoint1Y = sourceStartY;
            const controlPoint2X = sourceStartX + (targetEndX - sourceStartX) * 0.5;
            const controlPoint2Y = targetEndY;

            const path = this.svg.append('path')
                .attr('class', `record-connection-line record-line-${callNumberKey}`)
                .attr('d', `M ${sourceStartX},${sourceStartY} ` +
                          `C ${controlPoint1X},${controlPoint1Y} ` +
                          `${controlPoint2X},${controlPoint2Y} ` +
                          `${targetEndX},${targetEndY}`)
                .style('fill', 'none')
                .style('stroke', '#ccc')
                .style('stroke-width', 1)
                .style('opacity', 0);

            // 添加时间序列动画
            node.transition()
                .delay(i * 100)
                .duration(500)
                .style('opacity', 1)
                .attr('transform', `translate(${d.targetX}, ${targetY})`);

            path.transition()
                .delay(i * 100)
                .duration(500)
                .style('opacity', 0.4);
        });
    }

    // 计算每个月的借阅数量
    calculateMonthlyBorrowings(nodes) {
        const monthlyCounts = new Array(12).fill(0);
        nodes.forEach(node => {
            if (node.borrowDate) {
                const month = new Date(node.borrowDate).getMonth();
                monthlyCounts[month]++;
            }
        });
        return monthlyCounts;
    }

    // 添加绘制时间刻度的方法
    drawTimeScale(animate = false) {
        // 如果时间刻度已经显示，则不重复动画
        if (this.timeScaleShown) {
            return;
        }
        this.timeScaleShown = true;

        // 清除已有的时间刻度
        this.timeScaleGroup.selectAll('*').remove();

        // 使用三级节点的x坐标计算范围
        const baseX = this.level2X;
        const minOffset = 100;
        const maxOffset = 900;
        
        // 计算每个月份段的起始和结束位置
        const getMonthSegment = (month) => {
            const segmentWidth = (maxOffset - minOffset) / 12;  // 将总长度等分为12段
            const start = baseX + minOffset + (month - 1) * segmentWidth;
            const end = start + segmentWidth;
            return { start, end };
        };

        // 垂直位置调整到页面上部
        const verticalPosition = 37;  // 距离顶部40像素

        if (animate) {
            // 创建主刻度线容器
            const mainLineContainer = this.timeScaleGroup.append('g')
                .attr('class', 'main-line-container');

            // 创建剪切路径
            const clipId = 'clip-' + Math.random().toString(36).substr(2, 9);
            this.svg.append('defs')
                .append('clipPath')
                .attr('id', clipId)
                .append('rect')
                .attr('x', baseX + minOffset)
                .attr('y', verticalPosition - 10)
                .attr('width', 0)
                .attr('height', 20);

            // 绘制主刻度线
            mainLineContainer.append('line')
                .attr('x1', baseX + minOffset)
                .attr('x2', baseX + maxOffset)
                .attr('y1', verticalPosition)
                .attr('y2', verticalPosition)
                .style('stroke', '#ccc')
                .style('stroke-width', 2)
                .attr('clip-path', `url(#${clipId})`);

            // 延长动画时间，使用缓动效果使动画更平滑
            this.svg.select(`#${clipId} rect`)
                .transition()
                .duration(3600)
                .ease(d3.easeCubicInOut)
                .attr('width', maxOffset - minOffset);

            // 添加月份段和标签
            Array.from({length: 12}, (_, i) => i + 1).forEach((month, index) => {
                const segment = getMonthSegment(month);
                const tickGroup = this.timeScaleGroup.append('g')
                    .attr('class', 'tick-group')
                    .style('opacity', 0);
                
                // 添加段落分隔线
                tickGroup.append('line')
                    .attr('x1', segment.start)
                    .attr('x2', segment.start)
                    .attr('y1', verticalPosition - 5)
                    .attr('y2', verticalPosition + 5)
                    .style('stroke', '#666')
                    .style('stroke-width', 1);

                // 如果不是最后一个月，添加结束分隔线
                if (month < 12) {
                    tickGroup.append('line')
                        .attr('x1', segment.end)
                        .attr('x2', segment.end)
                        .attr('y1', verticalPosition - 5)
                        .attr('y2', verticalPosition + 5)
                        .style('stroke', '#666')
                        .style('stroke-width', 1);
                }

                // 添加月份标签（在段落中间）
                tickGroup.append('text')
                    .attr('x', (segment.start + segment.end) / 2)
                    .attr('y', verticalPosition + 20)
                    .attr('text-anchor', 'middle')
                    .text(month + '月')
                    .style('font-size', '12px')
                    .style('fill', '#666');

                // 添加渐入动画
                tickGroup.transition()
                    .delay(index * 100)
                    .duration(500)
                    .style('opacity', 1);
            });
        } else {
            // 非动画模式
            // 绘制主刻度线
            this.timeScaleGroup.append('line')
                .attr('x1', baseX + minOffset)
                .attr('x2', baseX + maxOffset)
                .attr('y1', verticalPosition)
                .attr('y2', verticalPosition)
                .style('stroke', '#ccc')
                .style('stroke-width', 2);

            // 添加月份段和标签
            Array.from({length: 12}, (_, i) => i + 1).forEach(month => {
                const segment = getMonthSegment(month);
                const tickGroup = this.timeScaleGroup.append('g')
                    .attr('class', 'tick-group');
                
                // 添加段落分隔线
                tickGroup.append('line')
                    .attr('x1', segment.start)
                    .attr('x2', segment.start)
                    .attr('y1', verticalPosition - 5)
                    .attr('y2', verticalPosition + 5)
                    .style('stroke', '#666')
                    .style('stroke-width', 1);

                // 如果不是最后一个月，添加结束分隔线
                if (month < 12) {
                    tickGroup.append('line')
                        .attr('x1', segment.end)
                        .attr('x2', segment.end)
                        .attr('y1', verticalPosition - 5)
                        .attr('y2', verticalPosition + 5)
                        .style('stroke', '#666')
                        .style('stroke-width', 1);
                }

                // 添加月份标签（在段落中间）
                tickGroup.append('text')
                    .attr('x', (segment.start + segment.end) / 2)
                    .attr('y', verticalPosition + 20)
                    .attr('text-anchor', 'middle')
                    .text(month + '月')
                    .style('font-size', '12px')
                    .style('fill', '#666');
            });
        }
    }

    // 计算刻度线和月份借阅量的水平偏移
    calculateScaleTransform(baseLevel, verticalOffset = 10, horizontalOffset = 50) {
        return `translate(${baseLevel + horizontalOffset}, ${verticalOffset})`;
    }

    resetView() {
        // 移除所有索书号气泡组和连接线
        this.svg.selectAll('.call-number-group').remove();
        this.svg.selectAll('.connection-line').remove();
        this.svg.selectAll('.record-bubble-group').remove();
        this.svg.selectAll('.record-connection-line').remove();
        
        // 移除月份借阅数据显示
        this.svg.selectAll('.monthly-borrowing-display').remove();
        
        // 重置时间刻度状态
        this.timeScaleShown = false;
        this.timeScaleGroup.selectAll('*').remove();
        
        // 重置所有气泡组到侧边垂直位置
        this.svg.selectAll('.bubble-group')
            .transition()
            .duration(750)
            .ease(d3.easeCubicInOut)
            .attr('transform', (d, i) => `translate(${this.level1X}, ${this.height * (i + 1) / 11})`);

        // 清除选中状态
        this.svg.selectAll('.bubble').classed('selected', false);
    }
}

// 初始化可视化
document.addEventListener('DOMContentLoaded', () => {
    const viz = new BubbleVisualization('#visualization');
    viz.loadData();
});
