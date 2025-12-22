# 快速启动指南 - v0.4.0 墨迹动画版

## 🚀 启动应用

```bash
# 安装依赖（如果还没安装）
npm install

# 启动开发服务器
npm run dev
```

## 🎨 查看动画效果

### 主页面（推荐）
访问：**http://localhost:3000**

这是完整的应用体验，包含：
- ✅ 全屏墨迹地图
- ✅ 鲁迅作品数据自动加载
- ✅ 播放/暂停控制
- ✅ 中国传统色图例
- ✅ 墨迹生长动画
- ✅ 涟漪扩散效果
- ✅ 呼吸灯光晕

### 演示页面（调试用）
访问：**http://localhost:3000/demo/ink-animation**

包含额外的调试控制：
- 时间轴滑块
- 详细动画说明
- 手动时间控制

## 🎮 使用方法

### 1. 启动动画
点击右下角的 **"▶ 播放"** 按钮

### 2. 观察动画效果

**墨迹生长路径**（0-2秒）
- 路径从起点向终点延伸
- 朱砂色（#b03d46）
- 动态线宽（2-4px）
- 透明度渐变

**涟漪扩散**（2-3.5秒）
- 城市节点产生3层波纹
- 松石色（#457B9D）
- 向外扩散，透明度衰减

**常亮状态**（3.5秒后）
- 路径变为黛蓝色（#1D3557）
- 节点呈现呼吸灯效果
- 松石色光晕闪烁

### 3. 控制动画

**播放/暂停**
- 点击 "▶ 播放" 开始动画
- 点击 "⏸ 暂停" 暂停动画

**重置**
- 点击 "⏹ 重置" 回到初始状态

**地图交互**
- 播放时：地图交互被锁定（自动模式）
- 暂停时：可以缩放、平移地图

## 🎨 动画参数

当前配置（可在 `AnimationController.ts` 中调整）：

```typescript
{
  growthDuration: 2000,    // 墨迹生长时间（毫秒）
  rippleDuration: 1500,    // 涟漪扩散时间（毫秒）
  flowSpeed: 0.5           // 流动速度（未使用）
}
```

## 🐛 故障排查

### 问题：动画不播放
**解决方案**：
1. 确认点击了 "▶ 播放" 按钮
2. 打开浏览器控制台，查看是否有错误
3. 检查是否有 `[OpenLayersMap] 动画已启动` 日志

### 问题：地图是空白的
**解决方案**：
1. 检查网络连接（底图需要加载）
2. 等待数据加载完成（左上角会显示作者信息）
3. 刷新页面重试

### 问题：颜色不对
**解决方案**：
1. 确认使用的是 v0.4.0 版本
2. 检查 `src/core/theme/colors.ts` 是否包含 `traditional` 颜色组
3. 清除浏览器缓存

## 📊 性能监控

打开浏览器开发者工具：

**Performance 面板**
- 录制动画播放过程
- 检查帧率是否稳定在 60fps

**Console 面板**
- 查看动画状态日志
- 监控 Feature 注册信息

**Network 面板**
- 检查底图瓦片加载
- 确认数据文件加载成功

## 🎯 下一步

### 调整动画参数
编辑 `src/core/map/OpenLayersMap.tsx`：

```typescript
const animationController = new AnimationController({
  growthDuration: 3000,  // 改为3秒
  rippleDuration: 2000,  // 改为2秒
  flowSpeed: 1.0
});
```

### 修改颜色
编辑 `src/core/theme/colors.ts`：

```typescript
traditional: {
  cinnabar: '#ff0000',    // 改为纯红色
  indigo: '#0000ff',      // 改为纯蓝色
  turquoise: '#00ffff',   // 改为青色
}
```

### 添加更多作者
编辑 `src/app/page.tsx`：

```typescript
// 改为加载其他作者
loadAuthor('murakami_haruki');
```

## 📚 相关文档

- [完整设计方案](./墨迹与边界-0.4.md)
- [迁移计划](./design/openlayers_migration_plan.md)
- [实施总结](./changelog/v0.4.0_ink_animation_system.md)

---

**版本**: v0.4.0  
**更新日期**: 2025-12-22  
**状态**: ✅ 可用
