// 搜索模块
const SearchModule = {
    init() {
        this.searchInput = document.getElementById('search-input');
        this.searchIcon = document.getElementById('search-icon');
        this.bindEvents();
        this.searchDebounceTimer = null;
        console.log('Search module initialized');
    },

    bindEvents() {
        // 输入时延迟搜索，提高性能
        this.searchInput.addEventListener('input', () => {
            clearTimeout(this.searchDebounceTimer);
            this.searchDebounceTimer = setTimeout(() => this.handleSearch(), 300);
        });

        // 添加Enter键搜索
        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.handleSearch(true);
            }
        });

        // 点击搜索图标触发搜索
        this.searchIcon.addEventListener('click', () => {
            if (this.searchInput.value.trim()) {
                this.handleSearch(true);
            } else {
                this.searchInput.focus();
            }
        });

        // 添加ESC键清除搜索
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.clearSearch();
            }
        });
    },

    handleSearch(isDirectSearch = false) {
        const searchTerm = this.searchInput.value.toLowerCase().trim();
        this.clearHighlights();
        
        if (searchTerm === '') return;

        // 获取所有节点
        const nodes = d3.selectAll('.node');
        let hasMatches = false;

        nodes.each(function() {
            // 获取节点中的文本元素
            const textElement = d3.select(this).select('text');
            const text = textElement.text().toLowerCase();
            
            if (text.includes(searchTerm)) {
                hasMatches = true;
                // 添加高亮类
                d3.select(this)
                    .classed('search-highlight', true)
                    .classed('search-pulse', isDirectSearch);

                // 如果是直接搜索，添加脉冲效果
                if (isDirectSearch) {
                    setTimeout(() => {
                        d3.select(this).classed('search-pulse', false);
                    }, 1000);
                }

                // 调整节点的样式
                d3.select(this).select('circle')
                    .style('filter', CONFIG.bubble.glow.hover)
                    .style('fill-opacity', 0.5);
            }
        });

        // 如果没有找到匹配项，添加视觉反馈
        if (isDirectSearch && !hasMatches) {
            this.searchInput.classList.add('no-results');
            setTimeout(() => {
                this.searchInput.classList.remove('no-results');
            }, 500);
        }

        console.log(`Search completed: ${hasMatches ? 'found matches' : 'no matches'}`);
    },

    clearHighlights() {
        // 移除所有高亮效果
        const nodes = d3.selectAll('.node');
        nodes.each(function() {
            const node = d3.select(this);
            node.classed('search-highlight', false)
                .classed('search-pulse', false);
            
            // 恢复节点的原始样式
            node.select('circle')
                .style('filter', CONFIG.bubble.glow.normal)
                .style('fill-opacity', 0.3);
        });
    },

    clearSearch() {
        this.searchInput.value = '';
        this.clearHighlights();
    }
};

// 当DOM加载完成后初始化搜索模块
document.addEventListener('DOMContentLoaded', () => {
    SearchModule.init();
});
