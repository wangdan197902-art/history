# S19 - Hugo 模板开发与 partial 缓存

> 阶段：Phase 3 - Hugo 集成与 10 万页构建
> 人天：2 | 依赖：S18 | 前置：垂直切片通过

---

## 一、步骤概述

开发 Hugo 完整模板体系：首页 / 地区列表页 / 单日详情页 / 404 页。使用 `partialCached` 缓存热点 partial（hreflang / schema-article / related-countries），确保缓存键含 `.Lang` 前缀避免跨语种串内容。

## 二、任务清单

### 2.1 模板文件清单

```
site/layouts/
├── _default/
│   ├── baseof.html       # 基础模板（S02 已建）
│   ├── day.html          # 单日详情页（S02 已建，需增强）
│   ├── list.html         # 列表页（地区/语种首页）
│   └── home.html         # 站点首页
├── partials/
│   ├── head.html         # <head> 内容
│   ├── header.html       # 站点头部导航
│   ├── footer.html       # 站点底部
│   ├── hreflang.html     # 多语种链接
│   ├── schema-article.html  # JSON-LD 结构化数据
│   ├── related-countries.html  # 相关地区推荐
│   ├── language-switcher.html  # 语种切换器
│   ├── country-list.html  # 地区列表
│   └── search-box.html   # Pagefind 搜索框
├── index.html            # 首页
├── 404.html              # 404 页
└── robots.txt            # robots.txt 模板
```

### 2.2 单日详情页模板（增强）

文件：`site/layouts/_default/day.html`

```html
{{ define "main" }}
<article class="day-page" data-country="{{ .Params.country_code }}" data-lang="{{ .Site.Language.Lang }}">
  <header class="day-header">
    <h1>{{ .Title }}</h1>
    <p class="day-meta">
      <time datetime="{{ .Date.Format "2006-01-02" }}">{{ .Date.Format "2006年01月02日" }}</time>
      · {{ .Params.country_name }}
    </p>
    {{ partial "language-switcher.html" . }}
  </header>

  <div class="day-content">
    {{ .Content }}
  </div>

  <footer class="day-footer">
    {{ partialCached "related-countries.html" . .Params.country_code .Date.Format "2006-01-02" .Site.Language.Lang }}
    {{ partialCached "schema-article.html" . .Params.country_code .Date.Format "2006-01-02" .Site.Language.Lang }}
  </footer>
</article>
{{ end }}
```

### 2.3 hreflang partial（带 .Lang 缓存键）

文件：`site/layouts/partials/hreflang.html`

```html
{{/* 缓存键: 页面 Permalink（含 lang 前缀） */}}
{{ partialCached "hreflang-inner.html" . .Permalink }}
```

文件：`site/layouts/partials/hreflang-inner.html`

```html
{{ range $.Site.Languages }}
  {{ $translated := index $.Translations .Lang }}
  {{ if $translated }}
    <link rel="alternate" hreflang="{{ .Lang }}" href="{{ $translated.Permalink }}">
  {{ end }}
{{ end }}
<link rel="alternate" hreflang="x-default" href="{{ $.Permalink }}">
```

### 2.4 JSON-LD 结构化数据

文件：`site/layouts/partials/schema-article.html`

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{{ .Title }}",
  "datePublished": "{{ .Date.Format "2006-01-02T15:04:05Z07:00" }}",
  "dateModified": "{{ .Lastmod.Format "2006-01-02T15:04:05Z07:00" }}",
  "inLanguage": "{{ .Site.Language.Lang }}",
  "about": {
    "@type": "Place",
    "name": "{{ .Params.country_name }}"
  },
  "author": {
    "@type": "Organization",
    "name": "{{ .Site.Title }}"
  }
}
</script>
```

### 2.5 语种切换器

文件：`site/layouts/partials/language-switcher.html`

```html
<nav class="language-switcher" aria-label="语言切换">
  {{ range $.Site.Languages }}
    {{ $translated := index $.Translations .Lang }}
    {{ if $translated }}
      <a href="{{ $translated.Permalink }}" lang="{{ .Lang }}">{{ .LanguageName }}</a>
    {{ else if eq .Lang $.Site.Language.Lang }}
      <span class="current" lang="{{ .Lang }}">{{ .LanguageName }}</span>
    {{ end }}
  {{ end }}
</nav>
```

### 2.6 相关地区推荐

文件：`site/layouts/partials/related-countries.html`

```html
{{ $current_country := .Params.country_code }}
{{ $date := .Date.Format "01-02" }}
<aside class="related-countries">
  <h3>同日其他地区</h3>
  <ul>
    {{ range first 10 (where $.Site.RegularPages "Date" .Date) }}
      {{ if ne .Params.country_code $current_country }}
        <li><a href="{{ .Permalink }}">{{ .Params.country_name }}</a></li>
      {{ end }}
    {{ end }}
  </ul>
</aside>
```

### 2.7 首页模板

文件：`site/layouts/index.html`

```html
{{ define "main" }}
<section class="home-hero">
  <h1>{{ .Site.Title }}</h1>
  <p>{{ .Site.Params.description }}</p>
</section>

<section class="home-countries">
  <h2>地区</h2>
  {{ partial "country-list.html" . }}
</section>

<section class="home-search">
  {{ partial "search-box.html" . }}
</section>
{{ end }}
```

### 2.8 性能优化验证

```bash
# 模板性能审计
cd site
hugo --templateMetrics --templateMetricsHints
# 期望: partialCached 命中率 > 80%
# 期望: 单页渲染 < 3ms
```

## 三、实施步骤

1. 编写 9 个 partial 模板
2. 增强 `day.html`（添加 partial 调用）
3. 编写 `index.html` 首页
4. 编写 `list.html` 列表页
5. 编写 `404.html` 错误页
6. 编写 `robots.txt` 模板
7. 运行 `--templateMetrics` 验证性能

## 四、验收命令

```bash
cd site

# 模板性能审计
hugo --templateMetrics --templateMetricsHints
# 期望:
# - partialCached 命中率 > 80%
# - 单页渲染 < 3ms
# - Top 10 慢 partial 已优化

# 构建 1 日数据
hugo --quiet
# 期望: 无错误

# 浏览器预览
hugo server
# 访问各页面验证渲染正确
```

## 五、依赖关系

- 前置：S18
- 后续：S20（图片处理）、S21（全量构建）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| partialCached 缓存键冲突 | 高 | 键必须含 .Lang + country + date |
| 跨语种串内容 | 高 | 强制 .Lang 前缀 |
| 模板循环调用 | 中 | 避免循环内 .GetPage |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 单页渲染 | < 5ms | `--templateMetrics` |
| partialCached 命中率 | > 80% | `--templateMetrics` |
| Top 10 慢 partial | 已优化 | 模板审计报告 |

## 八、测试要求

- 10 语种切换链接正确（hreflang）
- JSON-LD 结构化数据有效（Google Rich Results Test）
- partialCached 命中率 > 80%
- 单页渲染 < 5ms
