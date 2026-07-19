# S02 - Hugo 项目骨架初始化

> 阶段：Phase 0 - 环境与契约基础
> 人天：1 | 依赖：S01 | 前置：Hugo Extended 已安装

---

## 一、步骤概述

创建 Hugo 站点骨架，配置多语种（10 语种）、基础目录结构（`content/{lang}/{country}/{MM-DD}.md`）、URL 规则（`/{lang}/on-this-day/{country}/{MM-DD}/`），并验证空站点可启动。

## 二、任务清单

### 2.1 Hugo 站点初始化

文件：`site/hugo.toml`

```toml
baseURL = "http://localhost:1313/"
languageCode = "zh"
title = "今天历史 · 地区化档案站"
theme = "minimal"
defaultContentLanguage = "zh"

# 多语种配置（10 语种）
[languages]
[languages.zh]
  languageName = "中文"
  weight = 1
  title = "今天历史"
[languages.en]
  languageName = "English"
  weight = 2
  title = "Today in History"
[languages.ja]
  languageName = "日本語"
  weight = 3
  title = "今日の歴史"
[languages.ko]
  languageName = "한국어"
  weight = 4
  title = "오늘의 역사"
[languages.es]
  languageName = "Español"
  weight = 5
  title = "Hoy en la Historia"
[languages.fr]
  languageName = "Français"
  weight = 6
  title = "Aujourd'hui dans l'Histoire"
[languages.de]
  languageName = "Deutsch"
  weight = 7
  title = "Heute in der Geschichte"
[languages.pt]
  languageName = "Português"
  weight = 8
  title = "Hoje na História"
[languages.ru]
  languageName = "Русский"
  weight = 9
  title = "Сегодня в Истории"
[languages.ar]
  languageName = "العربية"
  weight = 10
  title = "اليوم في التاريخ"
  languageDirection = "rtl"

# 构建配置
[build]
  useResourceCacheWhen = "always"
  writeStats = true

[markup]
[markup.goldmark]
[markup.goldmark.renderer]
  unsafe = true
[markup.highlight]
  style = "github-dark"

# 缓存目录
[caches]
[caches.images]
  dir = ":cacheDir/hugo_tih_images"
  maxAge = "720h"
[caches.assets]
  dir = ":cacheDir/hugo_tih_assets"
  maxAge = "720h"

# Permalink 规则
[permalinks]
  day = "/:lang/on-this-day/:sections/:slug/"

# 输出格式
[outputs]
  home = ["HTML", "RSS", "JSON"]
  section = ["HTML", "RSS"]
  page = ["HTML"]

# 站点参数
[params]
  description = "地区化今天历史档案站 — 30 地区 × 10 语种 × 366 天"
  author = "Today in History Archive"
  # 30 地区列表
  countries = "CN,US,JP,KR,UK,DE,FR,RU,BR,IN,AU,CA,IT,ES,MX,ID,TH,VN,SG,MY,PH,SA,AE,EG,ZA,NG,TR,PL,NL,SE"
```

### 2.2 目录结构创建

```bash
mkdir -p site/content/{zh,en,ja,ko,es,fr,de,pt,ru,ar}
mkdir -p site/layouts/{_default,partials,shortcodes}
mkdir -p site/static/{css,js,images}
mkdir -p site/data
mkdir -p site/assets/{css,js,images}
mkdir -p site/archetypes
```

### 2.3 基础模板

文件：`site/layouts/_default/baseof.html`

```html
<!DOCTYPE html>
<html lang="{{ .Site.Language.Lang }}" dir="{{ .Site.Language.LanguageDirection | default "ltr" }}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ block "title" . }}{{ .Title }} · {{ .Site.Title }}{{ end }}</title>
  {{ partial "head.html" . }}
</head>
<body>
  {{ partial "header.html" . }}
  <main>{{ block "main" . }}{{ end }}</main>
  {{ partial "footer.html" . }}
</body>
</html>
```

文件：`site/layouts/_default/day.html`

```html
{{ define "main" }}
<article class="day-page">
  <header class="day-header">
    <h1>{{ .Title }}</h1>
    <p class="day-meta">{{ .Date.Format "2006-01-02" }} · {{ .Params.country_name }}</p>
  </header>
  {{ .Content }}
</article>
{{ end }}
```

文件：`site/layouts/partials/head.html`

```html
{{ partialCached "hreflang.html" . .Permalink }}
{{ partialCached "schema-article.html" . .Params.country_code .Date }}
```

文件：`site/layouts/partials/hreflang.html`

```html
{{ range $.Site.Languages }}
  <link rel="alternate" hreflang="{{ .Lang }}" href="{{ (index $.Translations .Lang).Permalink | default $.Permalink }}">
{{ end }}
```

### 2.4 内容示例

文件：`site/content/zh/CN/07-04.md`

```markdown
---
title: "7月4日 · 中国今天历史"
date: 2026-07-04
country_code: "CN"
country_name: "中国"
language: "zh"
draft: false
---

# 7月4日 · 中国今天历史

这是 Mock 内容示例，实际内容由管道生成。
```

### 2.5 主样式

文件：`site/assets/css/main.css`

```css
:root {
  --primary: #2563eb;
  --text: #1f2937;
  --bg: #ffffff;
  --border: #e5e7eb;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--text);
  background: var(--bg);
  margin: 0;
  line-height: 1.6;
}
.day-page { max-width: 800px; margin: 0 auto; padding: 2rem 1rem; }
.day-header h1 { color: var(--primary); }
```

## 三、实施步骤

1. 在 `site/` 目录运行 `hugo new site . --force`（如目录已存在）
2. 编写 `hugo.toml`（含 10 语种 + 30 地区配置）
3. 创建目录结构（content/layouts/static/data/assets）
4. 编写 `baseof.html` 基础模板
5. 编写 `day.html` 单页模板
6. 编写 `head.html` / `header.html` / `footer.html` / `hreflang.html` partials
7. 编写示例内容 `content/zh/CN/07-04.md`
8. 编写 `main.css` 主样式
9. 启动 `hugo server` 验证空站点可访问

## 四、验收命令

```bash
cd site
hugo server -D --bind 0.0.0.0
# 浏览器访问 http://localhost:1313
# 应看到站点首页 + 中文 7月4日 示例页

# 空构建验证
time hugo --quiet
# 期望 < 1s
```

## 五、依赖关系

- **前置依赖**：S01（Hugo Extended 已安装）
- **后续依赖**：S03（数据模型）、S19（模板开发）、S21（全量构建）
- **阻塞关系**：无后续步骤可在 Hugo 骨架未建立时进行模板/内容相关开发

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| Hugo Extended 版本错误 | 中 | `hugo version` 必须显示 "extended" |
| 多语种配置错误 | 中 | 检查 `[languages]` 段，权重 weight 唯一 |
| 模板 partialCached 缓存键冲突 | 高 | 缓存键必须包含 `.Lang` |
| 阿拉伯语 RTL 显示异常 | 低 | `languageDirection = "rtl"` 已配置 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| Hugo server 启动 | < 3s | `time hugo server` |
| 空构建时间 | < 1s | `time hugo --quiet` |
| 首页响应 | < 50ms | `curl -w "%{time_total}"` |

## 八、测试要求

- `hugo server` 启动无错误
- `http://localhost:1313/` 可访问
- `http://localhost:1313/zh/on-this-day/CN/07-04/` 可访问示例页
- 10 语种切换链接正确（hreflang）
