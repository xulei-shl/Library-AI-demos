# 模板核心规范

所有图书卡片模板必须遵循以下规范，确保截图功能正常工作。

---

## 一、主容器规范

### 必需：使用 library-card 类名

```html
<!-- ✅ 正确 -->
<div class="library-card">内容</div>

<!-- ❌ 错误 -->
<div class="book-card">内容</div>
<div class="card">内容</div>
```

### 容器必须是 body 下的第一个 div

```html
<body>
    <!-- ✅ 主容器是第一个 div -->
    <div class="library-card">
        ...
    </div>
</body>
```

---

## 二、容器尺寸规范

### 宽度建议

```css
.library-card {
    width: 600px;  /* 推荐 400-800px */
}
```

### 高度自动计算

```css
.library-card {
    /* 不设置固定高度 */
}
```

---

## 三、底部空白处理（关键）

### ❌ 禁止这样写

```css
.library-card {
    padding-bottom: 20px;  /* 会导致底部多余空白 */
    margin-bottom: 20px;   /* 会导致底部多余空白 */
}

.bottom-section {
    margin-bottom: 20px;   /* 禁止 */
}
```

### ✅ 正确做法

```css
.library-card {
    width: 600px;
    background-color: #fff;
    /* 不设置 padding-bottom 和 margin-bottom */
}

.bottom-section {
    height: 240px;
    background-color: #333;
    /* 不设置 margin-bottom */
}
```

---

## 四、文本截断处理

### 1. 单行文本截断（书名、作者、出版社）

```css
.book-title {
    white-space: nowrap;        /* 强制不换行 */
    overflow: hidden;           /* 隐藏溢出内容 */
    text-overflow: ellipsis;    /* 显示省略号 */
    max-width: 100%;
}
```

### 2. 多行文本截断（推荐语）

```css
.recommendation {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 4;      /* 限制4行 */
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.6;
}
```

### 3. Flex 布局中的文本截断

```css
.meta-row {
    display: flex;
    align-items: baseline;
}

.meta-key {
    flex-shrink: 0;             /* 标签不压缩 */
    min-width: 85px;
}

.meta-val {
    flex: 1;
    min-width: 0;               /* 关键：允许收缩 */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
```

---

## 五、图片路径规范

### ✅ 使用相对路径

```html
<img src="pic/cover.jpg" alt="Book Cover">
<img src="pic/qrcode.png" alt="QR Code">
<img src="pic/logo_shl.png" alt="Logo">
```

### ❌ 禁止使用

```html
<!-- 绝对路径 -->
<img src="C:/Users/.../pic/cover.jpg">

<!-- 网络路径 -->
<img src="https://example.com/cover.jpg">
```

### 添加错误处理

```html
<img src="pic/cover.jpg"
     alt="Book Cover"
     onerror="this.src='https://via.placeholder.com/300x400?text=COVER';">
```

---

## 六、占位符列表

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{{TITLE}}` | 书名 | 日本 : 文化核心日本 |
| `{{AUTHOR}}` | 作者 | [日] 松冈正刚 |
| `{{PUBLISHER}}` | 出版社 | 岳麓书社 |
| `{{PUB_YEAR}}` | 出版年份 | 2023 |
| `{{RECOMMENDATION}}` | 推荐语 | 一位编辑泰斗对日本文化... |
| `{{CALL_NUMBER}}` | 索书号 | G131.3/4971 |
| `{{DOUBAN_RATING}}` | 豆瓣评分 | 7.6 |

---

## 七、CSS 样式规范

### 字体定义示例

```css
:root {
    --title-font: "汇文明朝体", "HuiWen MingChao", serif;
    --body-font: "又又意宋", "YouYi Song", serif;
    --mono-font: "Cutive Mono", monospace;
}
```

### 颜色定义示例

```css
:root {
    --bg-color: #fdfbf6;
    --text-color: #423832;
    --accent-color: #d9480f;
}
```

---

## 八、禁止使用的特性

### ❌ 禁止使用

- 复杂的 CSS3 transform 动画
- JavaScript 异步加载图片
- `position: fixed`（可能影响边界计算）
- 复杂的 min-height / max-height 组合

### ✅ 推荐使用

- 简单的 transition 过渡效果
- 适度的 box-shadow
- border-radius 圆角
- opacity 透明度

---

## 九、DOM 结构示例

```html
<body>
    <div class="library-card">
        <!-- 顶部区域 -->
        <div class="top-section">
            <h1 class="book-title">{{TITLE}}</h1>
            <p class="book-author">{{AUTHOR}}</p>
        </div>

        <!-- 中间内容区域 -->
        <div class="content-section">
            <p class="recommendation">{{RECOMMENDATION}}</p>
        </div>

        <!-- 底部区域（如果有） -->
        <div class="bottom-section">
            <img src="pic/b.png" alt="Background">
        </div>
    </div>
</body>
```
