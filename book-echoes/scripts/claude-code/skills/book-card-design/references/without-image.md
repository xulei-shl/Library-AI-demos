# 无图片场景特殊要求

当模板不需要封面图片时，遵循以下特殊规范。

---

## 一、布局调整

### 满版信息布局

由于没有封面图片，信息区占据全部宽度：

```html
<div class="library-card">
    <!-- 满版信息区 -->
    <div class="content-section">
        <h1 class="book-title">{{TITLE}}</h1>
        <p class="book-author">{{AUTHOR}}</p>
        <p class="book-publisher">{{PUBLISHER}} / {{PUB_YEAR}}</p>
        <p class="recommendation">{{RECOMMENDATION}}</p>
    </div>
</div>
```

### 布局示意

```
┌─────────────────────────────────────┐
│                                     │
│      标题（大幅）                    │
│      作者                           │
│      出版社 / 年份                   │
│                                     │
│      推荐语（多行）                  │
│                                     │
└─────────────────────────────────────┘
```

---

## 二、背景替代方案

### 1. 纯色背景

```css
.library-card {
    background-color: #fdfbf6;
}
```

### 2. 纹理背景（CSS 图案）

```css
.library-card::before {
    content: "";
    position: absolute;
    inset: 0;
    background-image:
        repeating-linear-gradient(to bottom,
            transparent,
            transparent 29px,
            #e0f2fe 30px),
        repeating-linear-gradient(to right,
            transparent,
            transparent 149px,
            #f3f4f6 150px);
    background-size: 100% 30px, 150px 100%;
    opacity: 0.85;
    pointer-events: none;
}
```

### 3. CSS 噪点纹理

```css
.texture-grain {
    position: absolute;
    inset: 0;
    background-image: url("data:image/svg+xml,...");
    opacity: 0.08;
    mix-blend-mode: multiply;
    pointer-events: none;
}
```

### 4. 渐变背景

```css
.library-card {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}
```

---

## 三、装饰元素

### 标题水印（参考默认模板）

```html
<div class="watermark-title">
    书海回响
</div>
```

```css
.watermark-title {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 120px;
    opacity: 0.05;
    writing-mode: vertical-rl;
    pointer-events: none;
}
```

### 装饰线

```css
.divider {
    height: 2px;
    background: linear-gradient(to right, transparent, #333, transparent);
    margin: 20px 0;
}
```

---

## 四、元素间距调整

### 无图片时增加垂直间距

```css
.content-section {
    padding: 40px;
}

.book-title {
    font-size: 2rem;
    margin-bottom: 16px;
}

.book-author {
    font-size: 1.2rem;
    margin-bottom: 24px;
}

.recommendation {
    font-size: 1rem;
    line-height: 1.8;
    margin-top: 24px;
}
```

---

## 五、参考样式

### 极简风格

```
背景：纯白或浅灰
字体：黑体 / 无衬线体
装饰：极少，仅分割线
```

### 古典风格

```
背景：米色 + 线格纹理
字体：衬线体（又又意宋）
装饰：引号、装饰线
```

### 工业风格

```
背景：深色 + 网格
字体：等宽字体
装饰：边框、图标
```

---

## 六、对比：有图片 vs 无图片

| 元素 | 有图片 | 无图片 |
|------|--------|--------|
| 布局 | 左右分栏 | 满版 |
| 信息区宽度 | 60-70% | 100% |
| 背景 | 简洁 | 需要装饰 |
| 视觉重心 | 封面 | 标题/推荐语 |
| 二维码 | 必选 | 可选 |

---

## 七、模板示例结构

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Book Card - No Image</title>
    <style>
        .library-card {
            width: 600px;
            background-color: #fdfbf6;
            position: relative;
        }

        .texture-grain {
            position: absolute;
            inset: 0;
            /* 噪点纹理 */
            pointer-events: none;
        }

        .content {
            position: relative;
            z-index: 10;
            padding: 40px;
        }

        .book-title {
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 12px;
            /* 单行截断 */
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .book-author {
            font-size: 1.1rem;
            color: #666;
            margin-bottom: 20px;
        }

        .recommendation {
            font-size: 0.95rem;
            line-height: 1.8;
            /* 多行截断 */
            display: -webkit-box;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 4;
            overflow: hidden;
        }
    </style>
</head>
<body>
    <div class="library-card">
        <div class="texture-grain"></div>
        <div class="content">
            <h1 class="book-title">{{TITLE}}</h1>
            <p class="book-author">{{AUTHOR}}</p>
            <p class="recommendation">{{RECOMMENDATION}}</p>
        </div>
    </div>
</body>
</html>
```
