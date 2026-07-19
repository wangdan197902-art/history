# S04 - OpenAPI 契约编写

> 阶段：Phase 0 - 环境与契约基础
> 人天：1 | 依赖：S01 | 前置：数据模型已定义（S03 同步推进）

---

## 一、步骤概述

编写 6 份 OpenAPI 3.0 契约文件，定义 Wikipedia / Anthropic / OpenAI / Gemini / Buttondown / GSC 六个外部 API 的接口规范，作为 Mock Server 和真实实现共同遵守的契约，用于后续契约测试。

## 二、任务清单

### 2.1 6 份 OpenAPI 契约

文件清单：
- `tests/contracts/openapi_wikipedia.yaml`
- `tests/contracts/openapi_anthropic.yaml`
- `tests/contracts/openapi_openai.yaml`
- `tests/contracts/openapi_gemini.yaml`
- `tests/contracts/openapi_buttondown.yaml`
- `tests/contracts/openapi_gsc.yaml`

### 2.2 Wikipedia OnThisDay API 契约

文件：`tests/contracts/openapi_wikipedia.yaml`

```yaml
openapi: 3.0.3
info:
  title: Wikipedia OnThisDay API
  version: 1.0.0
  description: Wikipedia "On This Day" 事件 API 契约
servers:
  - url: https://api.wikimedia.org/feed/v1/wikipedia
    description: 生产环境
  - url: http://127.0.0.1:8765/wikipedia
    description: Mock 环境
paths:
  /onthisday/events/{month}/{day}:
    get:
      summary: 获取某月某日的历史事件
      parameters:
        - name: month
          in: path
          required: true
          schema:
            type: string
            pattern: '^(0[1-9]|1[0-2])$'
        - name: day
          in: path
          required: true
          schema:
            type: string
            pattern: '^(0[1-9]|[12][0-9]|3[01])$'
        - name: type
          in: query
          schema:
            type: string
            enum: [all, selected, births, deaths, holidays, events]
            default: all
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OnThisDayResponse'
        '404':
          description: 日期无效
        '429':
          description: 限流
        '500':
          description: 服务器错误
components:
  schemas:
    OnThisDayResponse:
      type: object
      properties:
        events:
          type: array
          items:
            $ref: '#/components/schemas/WikipediaEvent'
        births:
          type: array
          items:
            type: object
        deaths:
          type: array
          items:
            type: object
    WikipediaEvent:
      type: object
      required: [text, year, pages]
      properties:
        text:
          type: string
        year:
          type: integer
        pages:
          type: array
          items:
            type: object
            properties:
              title: { type: string }
              content_urls:
                type: object
                properties:
                  page: { type: string }
        categories:
          type: array
          items: { type: string }
```

### 2.3 Anthropic Claude API 契约（地区化重写）

文件：`tests/contracts/openapi_anthropic.yaml`

```yaml
openapi: 3.0.3
info:
  title: Anthropic Claude Messages API
  version: 1.0.0
servers:
  - url: https://api.anthropic.com/v1
  - url: http://127.0.0.1:8765/anthropic
paths:
  /messages:
    post:
      summary: Claude Messages API（用于地区化重写）
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [model, max_tokens, messages]
              properties:
                model:
                  type: string
                  enum: [claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022]
                max_tokens: { type: integer, minimum: 1 }
                system: { type: string }
                messages:
                  type: array
                  items:
                    type: object
                    properties:
                      role: { type: string, enum: [user, assistant] }
                      content: { type: string }
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  content:
                    type: array
                    items:
                      type: object
                      properties:
                        type: { type: string }
                        text: { type: string }
                  usage:
                    type: object
                    properties:
                      input_tokens: { type: integer }
                      output_tokens: { type: integer }
        '401': { description: 未授权 }
        '429': { description: 限流 }
        '500': { description: 服务器错误 }
```

### 2.4 OpenAI GPT-4o API 契约（翻译）

文件：`tests/contracts/openapi_openai.yaml`

```yaml
openapi: 3.0.3
info:
  title: OpenAI Chat Completions API
  version: 1.0.0
servers:
  - url: https://api.openai.com/v1
  - url: http://127.0.0.1:8765/openai
paths:
  /chat/completions:
    post:
      summary: GPT-4o 翻译 API
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [model, messages]
              properties:
                model:
                  type: string
                  enum: [gpt-4o, gpt-4o-mini]
                messages:
                  type: array
                  items:
                    type: object
                    properties:
                      role: { type: string, enum: [system, user, assistant] }
                      content: { type: string }
                temperature: { type: number, minimum: 0, maximum: 2 }
                response_format:
                  type: object
                  properties:
                    type: { type: string, enum: [json_object, text] }
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  choices:
                    type: array
                    items:
                      type: object
                      properties:
                        message:
                          type: object
                          properties:
                            role: { type: string }
                            content: { type: string }
                  usage:
                    type: object
```

### 2.5 Gemini API 契约（配图）

文件：`tests/contracts/openapi_gemini.yaml`

```yaml
openapi: 3.0.3
info:
  title: Google Gemini API
  version: 1.0.0
servers:
  - url: https://generativelanguage.googleapis.com/v1beta
  - url: http://127.0.0.1:8765/gemini
paths:
  /models/{model}:generateContent:
    post:
      summary: Gemini 配图生成
      parameters:
        - name: model
          in: path
          required: true
          schema:
            type: string
            enum: [gemini-1.5-flash, gemini-1.5-pro]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                contents:
                  type: array
                  items:
                    type: object
                    properties:
                      parts:
                        type: array
                        items:
                          type: object
                          properties:
                            text: { type: string }
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  candidates:
                    type: array
                    items:
                      type: object
                      properties:
                        content:
                          type: object
                          properties:
                            parts:
                              type: array
                              items:
                                type: object
```

### 2.6 Buttondown 邮件订阅 API 契约

文件：`tests/contracts/openapi_buttondown.yaml`

```yaml
openapi: 3.0.3
info:
  title: Buttondown Newsletter API
  version: 1.0.0
servers:
  - url: https://api.buttondown.com/api
  - url: http://127.0.0.1:8765/buttondown
paths:
  /emails:
    post:
      summary: 发送邮件
    get:
      summary: 获取邮件列表
  /subscribers:
    get:
      summary: 获取订阅者
    post:
      summary: 添加订阅者
```

### 2.7 Google Search Console API 契约

文件：`tests/contracts/openapi_gsc.yaml`

```yaml
openapi: 3.0.3
info:
  title: Google Search Console API
  version: 1.0.0
servers:
  - url: https://www.googleapis.com/webmasters/v3
  - url: http://127.0.0.1:8765/gsc
paths:
  /sites/{siteUrl}/sitemaps:
    get:
      summary: 获取 sitemap 列表
    submit:
      summary: 提交 sitemap
  /sites/{siteUrl}/searchAnalytics/query:
    post:
      summary: 查询搜索分析
```

## 三、实施步骤

1. 创建 `tests/contracts/` 目录
2. 编写 6 份 OpenAPI 3.0 YAML 文件
3. 每份契约包含：servers（生产 + Mock）、paths、components/schemas
4. 编写 `tests/contracts/README.md` 说明契约用途
5. 用 `schemathesis` 工具验证契约语法

## 四、验收命令

```bash
. .venv/bin/activate

# 契约语法验证
for f in tests/contracts/*.yaml; do
  python -c "import yaml; yaml.safe_load(open('$f'))" && echo "OK: $f"
done

# schemathesis 验证（语法层）
schemathesis run tests/contracts/openapi_wikipedia.yaml --checks all --base-url=http://127.0.0.1:8765
# 期望：所有契约语法正确
```

## 五、依赖关系

- **前置依赖**：S01（Python 环境）
- **并行依赖**：S03（数据模型）— 同步推进
- **后续依赖**：S05（Provider 抽象）、S06（Mock Server）、S17（契约测试）
- **阻塞关系**：契约定义完成才能编写 Provider 接口和 Mock Server

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| 契约与真实 API 不一致 | 高 | Phase 4 用 VCR.py 录制真实响应对比 |
| OpenAPI 3.0 语法错误 | 中 | 用 `schemathesis` 验证 |
| 字段缺失导致 Mock 失真 | 高 | 契约测试 + 真实样本对比 |
| 端点路径错误 | 中 | 参考 Wikipedia/OpenAI/Anthropic 官方文档 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 6 份契约编写 | < 1 天 | — |
| 契约语法验证 | < 5s | `schemathesis run` |
| 契约文件体积 | < 50KB/份 | `ls -la` |

## 八、测试要求

- 6 份 YAML 文件语法正确
- `schemathesis` 验证通过
- 每个 API 至少定义 1 个端点 + 完整请求/响应 schema
- 契约文档清晰（含 Mock 与生产 server URL）
