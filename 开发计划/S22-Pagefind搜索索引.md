# S22 - Pagefind 搜索索引

> 阶段：Phase 3 - Hugo 集成与 10 万页构建
> 人天：0.5 | 依赖：S21 | 前置：全量构建完成

---

## 一、步骤概述

使用 Pagefind 为 10 万页面生成静态搜索索引，目标索引体积 < 100MB，搜索响应 < 50ms。集成到 Hugo 模板，提供前端搜索 UI。

## 二、任务清单

### 2.1 Pagefind 安装与配置

```bash
# 通过 npx 使用（无需全局安装）
npx pagefind --version

# 或全局安装
npm install -g pagefind
```

### 2.2 索引生成脚本

文件：`scripts/build_search_index.sh`

```bash
#!/bin/bash
set -e

echo "=== Pagefind 搜索索引生成 ==="
START_TIME=$(date +%s)

cd site/public

# 生成索引
npx pagefind \
  --source . \
  --bundle-dir pagefind \
  --output-subdir _pagefind

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

INDEX_SIZE=$(du -sh pagefind | cut -f1)
INDEX_FILES=$(find pagefind -type f | wc -l)

echo "=== 索引生成完成 ==="
echo "总耗时: ${DURATION}s"
echo "索引体积: $INDEX_SIZE"
echo "索引文件数: $INDEX_FILES"

# 性能预算检查
if [ $DURATION -gt 180 ]; then
    echo "⚠️  超时: ${DURATION}s > 180s 预算"
    exit 1
fi
echo "✅ 性能预算达标"
```

### 2.3 搜索 UI partial

文件：`site/layouts/partials/search-box.html`

```html
<div class="search-container">
  <input type="search" id="search-input" placeholder="搜索历史事件..." aria-label="搜索">
  <div id="search-results" class="search-results"></div>
</div>

<link href="/pagefind/pagefind-ui.css" rel="stylesheet">
<script src="/pagefind/pagefind-ui.js" type="text/javascript"></script>
<script>
  window.addEventListener('DOMContentLoaded', () => {
    new PagefindUI({
      element: "#search-input",
      showSubResults: true,
      translations: {
        placeholder: "搜索历史事件...",
        zero_results: "未找到相关结果",
        many_results: "找到 {{count}} 个结果",
      }
    });
  });
</script>
```

### 2.4 搜索结果页

文件：`site/content/search.md`

```markdown
---
title: "搜索"
layout: search
url: /search/
---

# 搜索历史事件

使用 Pagefind 静态搜索，支持全文检索。
```

文件：`site/layouts/search.html`

```html
{{ define "main" }}
<section class="search-page">
  <h1>{{ .Title }}</h1>
  {{ partial "search-box.html" . }}
</section>
{{ end }}
```

### 2.5 CSS 样式

文件：`site/assets/css/main.css`（增强）

```css
.search-container {
  margin: 2rem 0;
}
.search-results {
  margin-top: 1rem;
}
.search-results .pagefind-ui__result {
  padding: 0.75rem;
  border-bottom: 1px solid var(--border);
}
.search-results .pagefind-ui__result-title {
  font-weight: 600;
  color: var(--primary);
}
```

## 三、实施步骤

1. 编写 `scripts/build_search_index.sh`
2. 运行索引生成
3. 编写 `search-box.html` partial
4. 编写 `search.html` 布局
5. 创建 `content/search.md`
6. 增强 `main.css` 搜索样式
7. 重新构建 Hugo 并生成索引

## 四、验收命令

```bash
. .venv/bin/activate

# 全量构建
bash scripts/hugo_build.sh

# 生成搜索索引
time bash scripts/build_search_index.sh
# 期望: < 3min，索引 < 100MB

# 启动预览
cd site && hugo server
# 访问 http://localhost:1313/search/
# 输入关键词，验证搜索响应 < 50ms
```

## 五、依赖关系

- 前置：S21
- 后续：S23（预览验证）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| 索引构建超时 | 中 | 增量索引（仅新增页面） |
| 索引体积过大 | 低 | Pagefind 自动压缩 |
| 搜索响应慢 | 低 | Pagefind 客户端索引 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 10 万页索引生成 | < 3min | `time` |
| 索引体积 | < 100MB | `du -sh` |
| 搜索响应 | < 50ms | 浏览器 DevTools |

## 八、测试要求

- 搜索索引生成
- 搜索框正常工作
- 搜索结果准确
- 响应时间 < 50ms
