class LibraryVisualization {
    constructor() {
        this.data = null;
        this.borrowMap = new Map();
        this.maxBorrows = 0;
        this.minBorrows = Infinity;
    }

    async initialize() {
        try {
            const response = await fetch('data/borrow_data.json');
            this.data = await response.json();
            this.processData();
            this.renderVisualization();
            this.updateStatistics();
        } catch (error) {
            console.error('Error loading data:', error);
        }
    }


    processData() {
        this.data.borrow_data.forEach(day => {
          let holidayName = day.holiday_name;
          if (holidayName) {
            holidayName = holidayName.split('（')[0];
          }
          this.borrowMap.set(day.date, {
            count: day.borrow_count,
            isHoliday: day.is_holiday,
            holidayName: holidayName,
            weekday: day.weekday
          });
          this.maxBorrows = Math.max(this.maxBorrows, day.borrow_count);
          this.minBorrows = Math.min(this.minBorrows, day.borrow_count);
        });
      }
      
    updateMonthTitle(monthContainer, currentMonth) {
    const monthTitle = monthContainer.querySelector('.month-title');
    if (!monthTitle) {
        console.error('月份标题不存在');
        return;
    }
    const currentMonthData = this.data.summary.monthly_summary.find(summary => summary.month === currentMonth);
    const currentMonthBorrowCount = currentMonthData ? currentMonthData.borrow_count : 0;

    const monthName = monthTitle.textContent.split('（')[0];
    monthTitle.innerHTML = `<span>${monthName}</span><span class="brackets">(</span><strong class="borrow-count">${currentMonthBorrowCount.toLocaleString()}</strong><span class="brackets">)</span>`;
    }
      
    getCurrentMonth() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        return `${year}-${month}`;
    }

    getColorLevel(borrowCount) {
        if (!borrowCount) return 1;
        const range = this.maxBorrows - this.minBorrows;
        const normalized = (borrowCount - this.minBorrows) / range;
        return Math.ceil(normalized * 8);
    }

    renderVisualization() {
        const calendarGrid = document.querySelector('.yearly-calendar');
        const months = ['一月', '二月', '三月', '四月', '五月', '六月',
                        '七月', '八月', '九月', '十月', '十一月', '十二月'];

        months.forEach((month, index) => {
            const monthContainer = document.createElement('div');
            monthContainer.className = 'month-container';

            const monthTitle = document.createElement('div');
            monthTitle.className = 'month-title';
            monthTitle.textContent = month;

            const monthGrid = document.createElement('div');
            monthGrid.className = 'month-grid';
    
            // 获取该月的天数
            const daysInMonth = this.getDaysInMonth(2024, index + 1);
    
            // 获取该月第一天的周几（0: 周日, 1: 周一, ..., 6: 周六）
            const firstDayOfWeek = new Date(2024, index, 1).getDay();
    
            // 根据需要添加空白占位符，使第一天对齐到正确的周几（周一为起始日）
            const emptyCells = (firstDayOfWeek + 6) % 7; // 将周日 (0) 转为最后一天
            for (let i = 0; i < emptyCells; i++) {
                const emptyCell = document.createElement('div');
                emptyCell.className = 'day-cell empty-cell'; // 用于样式区分
                monthGrid.appendChild(emptyCell);
            }
    
            // 创建该月的日期网格
            for (let day = 1; day <= daysInMonth; day++) {
                const dateStr = this.formatDate(2024, index + 1, day); // 确保日期格式正确
                const dayData = this.borrowMap.get(dateStr);
    
                const dayCell = document.createElement('div');
                dayCell.className = 'day-cell';
                if (dayData) {
                    const level = this.getColorLevel(dayData.count);
                    dayCell.classList.add(`level-${level}`);
                    dayCell.title = '';
                
                    const tooltip = document.createElement('div');
                    tooltip.classList.add('tooltip');
                    tooltip.innerHTML = `${dateStr}`;
                    if (dayData.isHoliday) {
                        tooltip.innerHTML += `<br>${dayData.weekday} ${dayData.holidayName}`;
                    } else {
                        tooltip.innerHTML += `<br>${dayData.weekday}`;
                    }
                    tooltip.innerHTML += `<br>借阅量: ${dayData.count}`;
                
                    dayCell.appendChild(tooltip);
                }
                monthGrid.appendChild(dayCell);
            }
            
            monthContainer.appendChild(monthTitle);
            monthContainer.appendChild(monthGrid);
            
             const currentMonth = this.getCurrentMonth();
             const monthIndexStr = String(index+1).padStart(2,'0');
             const currentMonthString = `2024-${monthIndexStr}`;

             this.updateMonthTitle(monthContainer,currentMonthString);
            calendarGrid.appendChild(monthContainer);
        });
    }

    updateStatistics() {
        // 确保 this.data 已经正确加载
        if (!this.data || !this.data.summary) {
            console.error('Data not loaded correctly');
            return;
        }        
        // 更新总借阅量
        document.getElementById('totalBorrows').textContent =
            this.data.summary.total_borrows.toLocaleString();

        // 更新最高日借阅
        document.getElementById('maxBorrows').textContent =
            this.data.summary.top_day.borrow_count.toLocaleString();
        document.getElementById('maxDayName').textContent =
            this.formatDateFromString(this.data.summary.top_day.date);

        // 更新最低日借阅
        document.getElementById('minBorrows').textContent =
            this.data.summary.lowest_day.borrow_count.toLocaleString();
        document.getElementById('minDayName').textContent =
            this.formatDateFromString(this.data.summary.lowest_day.date);

        // 更新最高月借阅
        document.getElementById('maxMonthBorrows').textContent =
            this.data.summary.top_month.borrow_count.toLocaleString();
        document.getElementById('maxMonthName').textContent =
            this.formatMonth(this.data.summary.top_month.month);

        // 更新最低月借阅
        document.getElementById('minMonthBorrows').textContent =
            this.data.summary.lowest_month.borrow_count.toLocaleString();
        document.getElementById('minMonthName').textContent =
            this.formatMonth(this.data.summary.lowest_month.month);

    }

    formatMonth(monthStr) {
        const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'];
        const monthIndex = parseInt(monthStr.split('-')[1]) - 1;
        return monthNames[monthIndex];
    }

    formatDate(year, month, day) {
        return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    }

    formatDateFromString(dateStr) {
        const [year, month, day] = dateStr.split('-').map(Number);
        return this.formatDate(year, month, day);
    }
    getDaysInMonth(year, month) {
        return new Date(year, month, 0).getDate();
    }
}

// 初始化可视化
document.addEventListener('DOMContentLoaded', () => {
    const visualization = new LibraryVisualization();
    visualization.initialize();
});