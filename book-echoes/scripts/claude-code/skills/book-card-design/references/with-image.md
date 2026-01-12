# 有图片场景特殊要求

当模板需要插入封面图片时，遵循以下特殊规范。

---

## 一、封面图片容器

### 基础结构

```html
<div class="cover-section">
    <img src="pic/cover.jpg" alt="Book Cover" class="cover-image">
</div>
```

### CSS 样式（参考：极简工业档案）

```css
.cover-section {
    position: relative;
    width: 260px;
    height: 100%;
    overflow: hidden;
}

.cover-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border: 2px solid rgba(255, 255, 255, 0.1);
}
```

### 3D 封面效果（可选）

```css
.cover-wrapper {
    perspective: 1200px;
}

.cover-3d {
    transform: rotateY(-12deg) rotateX(2deg) translateZ(20px);
    box-shadow: -15px 20px 30px rgba(0, 0, 0, 0.25);
}
```

---

## 二、二维码处理

### 基础结构

```html
<div class="qrcode-container">
    <img src="pic/qrcode.png" alt="QR Code">
</div>
```

### 固定位置示例

```css
.qrcode-container {
    position: absolute;
    bottom: 16px;
    right: 16px;
    padding: 6px;
    background: #fff;
    border-radius: 4px;
}

.qrcode-container img {
    width: 48px;
    height: 48px;
}
```

---

## 三、布局参考

### 左右分栏布局（极简工业档案风格）

```
┌─────────────────────┬─────────────────────┐
│      信息区          │     封面区          │
│   (62% 宽度)         │   (38% 宽度)        │
│                     │                     │
│  · 红色左边栏        │  · 3D封面效果       │
│  · 标题 + 作者       │  · Scan to Read     │
│  · 评分 + 出版社     │  · 二维码           │
│  · 推荐语            │                     │
└─────────────────────┴─────────────────────┘
```

### 代码结构

```html
<div class="library-card flex flex-row">
    <!-- 左侧信息区 -->
    <div class="w-[62%] p-8 border-r border-gray-300">
        ...
    </div>

    <!-- 右侧封面区 -->
    <div class="w-[38%] bg-ink-black">
        <div class="cover-wrapper">
            <img src="pic/cover.jpg" class="cover-3d">
        </div>
        <div class="qrcode-container">...</div>
    </div>
</div>
```

---

## 四、可用参考模板

| 模板 | 风格 |
|------|------|
| 极简工业档案 | 工业风、3D封面、左侧红边栏 |
| 绿色大字 | 前卫大胆、绿色背景、封面叠加效果 |
| 默认 | 古典风格、右侧封面、卡片打孔 |

---

## 五、图片资源清单

| 路径 | 用途 | 必填 |
|------|------|------|
| `pic/cover.jpg` | 封面图片 | 是 |
| `pic/qrcode.png` | 二维码 | 否 |
| `pic/logo_shl.png` | 机构Logo | 否 |
| `pic/b.png` | 装饰背景 | 否 |
| `pic/logozi_shl.jpg` | 水印Logo | 否 |

---

## 六、常见问题

### Q: 封面图片比例不一致怎么办？

A: 使用 `object-fit: cover` 配合固定容器尺寸：

```css
.cover-image {
    width: 260px;
    height: 390px;  /* 按 2:3 比例 */
    object-fit: cover;
}
```

### Q: 3D 效果在截图时变形怎么办？

A: 移除 transform 效果，或截图前临时禁用动画。
