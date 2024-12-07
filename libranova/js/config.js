const CONFIG = {
    // 动画配置
    animation: {
        duration: 750,
        ease: d3.easeCubicInOut
    },
    
    // 气泡配置
    bubble: {
        minRadius: 20,
        maxRadius: 80,
        padding: 10,
        opacity: 0.4,
        strokeWidth: 2,
        glow: {
            normal: 'drop-shadow(0 0 3px rgba(255, 255, 255, 0.3))',
            hover: 'drop-shadow(0 0 8px rgba(255, 255, 255, 0.6))'
        }
    },
    
    // 颜色配置
    colors: {
        background: '#090A0F',
        // 基于首字母的星空主题颜色配置（22个独特的颜色）
        initialColors: {
            'A': { base: '#FF6B6B', glow: '#FF9999' },     // 明亮红色
            'B': { base: '#4ECDC4', glow: '#7EDCD4' },     // 青绿色
            'C': { base: '#45B7D1', glow: '#72C7DB' },     // 天蓝色
            'D': { base: '#96CEB4', glow: '#B4DBC9' },     // 薄荷绿
            'F': { base: '#9B59B6', glow: '#B87AD4' },     // 紫色
            'G': { base: '#3498DB', glow: '#5FAEE3' },     // 蓝色
            'H': { base: '#FF69B4', glow: '#FF85C3' },     // 亮粉色
            'J': { base: '#1ABC9C', glow: '#45C9B0' },     // 绿松石色
            'K': { base: '#F1C40F', glow: '#F4D03F' },     // 金色
            'L': { base: '#E74C3C', glow: '#ED6A5E' },     // 深红色
            'M': { base: '#2ECC71', glow: '#57D68D' },     // 翠绿色
            'N': { base: '#F39C12', glow: '#F5B041' },     // 琥珀色
            'P': { base: '#16A085', glow: '#36BFA3' },     // 深青色
            'Q': { base: '#8E44AD', glow: '#A569BD' },     // 深紫色
            'R': { base: '#8A2BE2', glow: '#9C51E0' },     // 蓝紫色
            'S': { base: '#C0392B', glow: '#CD6155' },     // 暗红色
            'T': { base: '#27AE60', glow: '#4FBF7F' },     // 深绿色
            'W': { base: '#2980B9', glow: '#5499C7' },     // 深蓝色
            'X': { base: '#FF1493', glow: '#FF69B4' },     // 亮粉色
            'Y': { base: '#20B2AA', glow: '#48D1CC' },     // 浅海色
            'Z': { base: '#BA55D3', glow: '#DA70D6' },     // 兰花紫
            'default': { base: '#95A5A6', glow: '#B3B3B3' }  // 默认灰色
        },
        level: {
            1: { opacity: 0.9 },
            2: { opacity: 0.8 },
            3: { opacity: 0.7 }
        }
    },
    
    // 层级配置
    levels: {
        names: ['一级主题', '二级主题', '三级主题'],
        maxDepth: 3
    },
    
    // 力导向图配置
    force: {
        strength: -50,
        distance: 30
    }
};
