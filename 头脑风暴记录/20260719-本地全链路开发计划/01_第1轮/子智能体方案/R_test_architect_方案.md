# 测试架构师方案 — 第 1 轮

> 角色：测试架构师（R_test_architect）
> 视角：自动化框架选型 / 测试金字塔搭建 / Mock/Stub 策略 / 环境管理 / 持续测试流水线
> 输出范围：本地全链路开发计划的测试体系与 Mock 数据样本设计
> 编写日期：2026-07-19

---

## 角色定位

测试架构师，聚焦**测试体系设计与 Mock 策略**。在本项目中负责：

1. 设计完整的 Mock 体系（Wikipedia / AI API / Cloudflare / GitHub Actions）
2. 设计测试数据样本（事件池 JSON、Mock API 响应模板、多地区/多语种覆盖）
3. 搭建测试金字塔（单元 / 集成 / E2E）的工具选型与覆盖率目标
4. 设计本地 CI/CD 模拟方案（Makefile + act）
5. 设计数据完整性校验方案（JSON Schema / HTML 渲染 / 链接检查）
6. 为每个开发步骤提供"测试验收清单"

**核心立场**：Mock 数据必须"足够真实以暴露问题，足够简单以快速验证"。测试金字塔必须有清晰边界，避免 E2E 测试爆炸。

---

## Mock 体系总览（测试架构师特色）

### 1. 外部依赖清单与 Mock 策略

| 外部依赖 | Mock 策略 | 工具/库 | 响应数据来源 | 校验点 | 优先级 |
|---------|----------|---------|-------------|--------|--------|
| Wikipedia OnThisDay API | 本地 Flask 返回静态 JSON | Flask + fixtures | fixtures/wikipedia/{MM-DD}.json | 字段完整性 + 事件数 ≥ 5 | P0 |
| Wikimedia Commons API | 本地 Flask 返回图片 URL 列表 | Flask | fixtures/commons/{event_id}.json | URL 可访问（本地占位图） | P1 |
| Anthropic Claude API | 本地 Flask 返回预录制响应 | Flask | fixtures/anthropic/{country}-{date}.json | 字段完整性 + 中立性评分 | P0 |
| OpenAI GPT-4o API | 本地 Flask 返回预录制响应 | Flask | fixtures/openai/{lang}-{country}-{date}.json | 翻译完整性 + 10 语种齐全 | P0 |
| Google Gemini API | 本地 Flask 返回图片 URL | Flask | fixtures/gemini/{event_id}.json | URL 可访问 + WebP 格式 | P1 |
| Cloudflare Pages API | 本地 Flask 返回部署成功响应 | Flask | fixtures/cloudflare/deploy_success.json | deployment_id 字段 | P2 |
| Buttondown Email API | 本地 Flask 返回订阅成功响应 | Flask | fixtures/buttondown/subscribe.json | subscriber_id 字段 | P2 |
| Google Search Console | 跳过（本地无 SEO） | — | — | — | P3 |
| GitHub Actions | `act` 本地模拟 | act | .github/workflows/*.yml | workflow exit code = 0 | P1 |
| DBpedia SPARQL | 本地 Flask 返回 SPARQL JSON | Flask | fixtures/dbpedia/{entity}.json | 字段完整性 | P2 |

### 2. Mock Server 端口分配

| 服务 | 端口 | 路由前缀 |
|------|------|---------|
| Flask Mock Server（统一入口） | 8765 | /api/{service}/... |
| Hugo Dev Server | 1313 | / |
| 本地预览（生产模拟） | 8080 | / |
| act GitHub Actions | N/A | N/A |

### 3. 测试数据样本设计

#### 3.1 事件池样本结构（fixtures/wikipedia/）

```json
{
  "date": "07-04",
  "url": "https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/07/04",
  "events": [
    {
      "text": "American Revolution: The United States Declaration of Independence is adopted by the Second Continental Congress.",
      "year": 1776,
      "pages": [
        {
          "title": "United States Declaration of Independence",
          "description": "Statement adopted by the Second Continental Congress",
          "content_urls": {
            "desktop": { "page": "https://en.wikipedia.org/wiki/United_States_Declaration_of_Independence" }
          }
        }
      ]
    }
  ]
}
```

#### 3.2 多地区样本覆盖策略

| 日期样本 | 涉及地区数 | 涉及语种数 | 用途 |
|---------|----------|----------|------|
| 07-04（美国独立日） | 5（us/gb/fr/es/de） | 3（en/zh/es） | 验证跨地区事件 |
| 01-01（元旦） | 30（全部） | 10（全部） | 验证全规模覆盖 |
| 07-14（法国国庆） | 5（fr/gb/de/it/es） | 3（fr/en/zh） | 验证欧洲事件 |
| 10-01（中国国庆） | 5（cn/jp/kr/us/gb） | 3（zh/en/ja） | 验证亚洲事件 |
| 12-25（圣诞节） | 30（全部） | 10（全部） | 验证全球性事件 |

**样本数据生成器**：`src/scripts/gen_mock_data.py`
- 自动生成 5 个日期 × 30 地区 × 3 语种 = 450 个 Mock 响应样本
- 每个样本包含 5-15 个事件
- 人工编写 1 个高质量样本（07-04 美国独立日），其余基于模板生成

#### 3.3 Mock API 响应模板（fixtures/anthropic/）

```json
{
  "id": "msg_mock_001",
  "type": "message",
  "role": "assistant",
  "model": "claude-3-5-sonnet-20241022",
  "content": [
    {
      "type": "text",
      "text": "## 地区化重写结果\n\n**事件**：1776年7月4日，美国独立宣言被第二届大陆会议采纳。\n\n**地区视角（美国）**：..."
    }
  ],
  "usage": { "input_tokens": 1234, "output_tokens": 567 },
  "neutrality_score": 0.85,
  "regional_angle": "American perspective: The Declaration established the philosophical foundation..."
}
```

#### 3.4 测试覆盖矩阵

| 测试类型 | 工具 | 覆盖范围 | 目标覆盖率 | 执行频率 |
|---------|------|---------|----------|---------|
| 单元测试 | pytest + pytest-asyncio | Provider 接口、管道各阶段函数 | 80% | 每次提交 |
| 契约测试 | schemathesis | 6 份 OpenAPI 契约 | 100% 端点 | 每次提交 |
| 集成测试 | pytest + Flask test client | 管道端到端（单日） | 5 个日期样本 | 每日 CI |
| E2E 测试 | bash + curl + html5validator | 完整流程（Mock → Hugo → 预览） | 1 个垂直切片 | 每周 CI |
| 性能测试 | wrk + py-spy + Lighthouse CLI | Mock 吞吐量、Hugo 构建时间、页面性能 | 关键指标 100% | 每周 CI |
| 链接检查 | linkchecker | 全部内部链接 | 0 死链 | 每周 CI |
| HTML 校验 | html5validator + nu-validator | HTML5 规范 | 0 错误 | 每次提交 |
| Schema 校验 | jsonschema + Schema.org validator | JSON-LD Event schema | 100% 日期页 | 每次提交 |

---

## 方案清单

### 方案1：分层 Mock + 测试金字塔方案（推荐 — 测试严谨派）

**核心思路**（295 字）：

建立三层 Mock 体系：(1)**Fixture 层** — 预录制的 JSON 响应存储在 `tests/fixtures/{service}/`，覆盖 5 日期 × 30 地区 × 3 语种 = 450 个样本；(2)**Server 层** — Flask Mock Server 在端口 8765 统一响应所有外部 API，按 `{service}/{scenario}` 路由到对应 fixture；(3)**Client 层** — Provider 的 Mock 实现通过 httpx 调用 Flask Server，支持延迟注入模拟真实 API 时序。测试金字塔：单元测试 70%（pytest，目标覆盖率 80%）+ 集成测试 20%（pytest + Flask test client，覆盖单日管道）+ E2E 测试 10%（bash 脚本，覆盖完整流程）。本地 CI 用 Makefile 串联，关键 workflow 用 `act` 模拟 GitHub Actions。该方案核心优势是"分层隔离 + 真实时序模拟"，能在本地暴露 90% 的生产问题。

**实施步骤**：

1. **Phase A：Fixture 数据准备**
   - 编写 `src/scripts/gen_mock_data.py`
   - 生成 5 日期 × 30 地区 × 3 语种的 Wikipedia 事件样本
   - 人工编写 10 个高质量 AI 响应样本（3 地区 × 3 日期 + 1 边界）
   - 基于模板生成剩余 440 个 AI 响应样本
   - 编写 fixtures 的 README.md 说明数据来源与生成规则

2. **Phase B：Flask Mock Server 实现**
   - 实现 `src/mock_server/app.py` 的 `create_app()` 工厂函数
   - 实现 4 个路由 Blueprint：wikipedia / anthropic / openai / gemini
   - 实现 `data_loader.py` 的 `load_fixture(service, scenario)` 函数
   - 实现延迟注入：`await asyncio.sleep(delay)` 模拟真实 API 时序
   - 编写 Mock Server 自检脚本 `tests/integration/test_mock_server.py`

3. **Phase C：单元测试体系**
   - 编写 `tests/unit/test_providers.py`：测试 6 个 Provider 的 Mock 实现
   - 编写 `tests/unit/test_pipeline.py`：测试 7 个管道阶段函数
   - 编写 `tests/unit/test_models.py`：测试 pydantic 数据模型
   - 编写 `tests/unit/test_config.py`：测试配置双轨制切换
   - 配置 `pytest.ini`：覆盖率目标 80%，失败立即停止

4. **Phase D：契约测试**
   - 编写 6 份 OpenAPI 契约文件（`tests/contracts/*.openapi.yaml`）
   - 使用 `schemathesis` 自动生成契约测试用例
   - 验证 Mock Server 响应 100% 符合契约
   - 在 CI 中加入 `schemathesis run` 步骤

5. **Phase E：集成测试**
   - 编写 `tests/integration/test_pipeline_e2e.py`：单日管道端到端
   - 编写 `tests/integration/test_hugo_build.py`：Hugo 构建验证
   - 编写 `tests/integration/test_mock_server.py`：Mock Server 自检
   - 使用 pytest 的 `@pytest.fixture` 管理 Mock Server 启动/停止

6. **Phase F：E2E 测试**
   - 编写 `scripts/local_e2e.sh`：完整流程脚本
   - 启动 Mock Server → 跑管道 → 生成 Markdown → Hugo 构建 → 启动预览
   - 用 `curl` 验证关键页面可访问
   - 用 `html5validator` 校验 HTML
   - 用 `linkchecker` 校验内部链接

7. **Phase G：本地 CI/CD 模拟**
   - 编写 `Makefile`：`make test` / `make e2e` / `make lint` / `make ci`
   - 安装 `act`（GitHub Actions 本地模拟器）
   - 编写 `.github/workflows/test.yml`（轻量测试 workflow）
   - 用 `act -j test` 本地执行 GitHub Actions

8. **Phase H：数据完整性校验**
   - 编写 `tests/integration/test_schema_validation.py`
   - 用 `jsonschema` 校验所有 `data/events/*.json`
   - 用 Schema.org validator 校验 HTML 中的 JSON-LD
   - 编写 `scripts/check_links.sh` 校验内部链接

**Mock 体系设计**：

| 外部依赖 | Mock 策略 | 工具/库 | 响应数据来源 | 校验点 |
|---------|----------|---------|-------------|--------|
| Wikipedia API | Flask + fixtures JSON | Flask | fixtures/wikipedia/{MM-DD}.json | 字段完整性 + 事件数 ≥ 5 |
| Anthropic Claude | Flask + fixtures JSON | Flask | fixtures/anthropic/{country}-{date}.json | 中立性评分 ≥ 0.7 |
| OpenAI GPT-4o | Flask + fixtures JSON | Flask | fixtures/openai/{lang}-{country}-{date}.json | 10 语种齐全 |
| Google Gemini | Flask + 占位图 URL | Flask | fixtures/gemini/{event_id}.json | URL 可访问 + WebP |
| Cloudflare Pages | Flask + 成功响应 | Flask | fixtures/cloudflare/deploy_success.json | deployment_id |
| GitHub Actions | `act` 本地模拟 | act | .github/workflows/*.yml | exit code = 0 |

**测试数据样本设计**：

- **事件池样本**：5 日期 × 30 地区 × 3 语种 = 450 个 JSON 样本
- **AI 响应样本**：10 个高质量人工编写 + 440 个模板生成
- **图片样本**：用 `Pillow` 生成 100 张占位 WebP 图片（含事件标题水印）
- **边界用例**：空事件日、单事件日、超长事件标题、特殊字符事件

**测试覆盖矩阵**：

| 测试类型 | 工具 | 覆盖范围 | 目标覆盖率 | 执行时间 |
|---------|------|---------|----------|---------|
| 单元测试 | pytest | Provider + 管道函数 | 80% | < 30s |
| 契约测试 | schemathesis | 6 份 OpenAPI | 100% 端点 | < 60s |
| 集成测试 | pytest + Flask | 单日管道 | 5 日期样本 | < 5min |
| E2E 测试 | bash + curl | 完整流程 | 1 垂直切片 | < 20min |
| 性能测试 | wrk + Lighthouse | 关键指标 | 100% | < 10min |
| 链接检查 | linkchecker | 内部链接 | 0 死链 | < 5min |
| HTML 校验 | html5validator | HTML5 规范 | 0 错误 | < 2min |

**预期效果**：

- 本地一键测试：`make test` 在 5 分钟内完成单元 + 契约 + 集成测试
- 本地完整 E2E：`make e2e` 在 20 分钟内完成全链路验证
- 测试覆盖率：核心 Provider 100%，管道阶段 80%+
- Mock 数据质量：10 个高质量样本 + 440 个模板样本，覆盖主要场景
- 本地 CI 模拟：`act -j test` 可在本地执行 GitHub Actions workflow

**潜在风险**：

- **风险 1：Mock 数据失真**：模板生成的 440 个样本可能遗漏边界场景。**应对**：每月评审 Mock 数据质量，补充新发现的边界场景
- **风险 2：契约维护成本**：6 份 OpenAPI 契约需同步更新。**应对**：使用 `schemathesis` 自动生成契约测试，契约变更立即触发测试失败
- **风险 3：E2E 测试执行慢**：20 分钟的 E2E 在快速迭代时过长。**应对**：提供 `make e2e-quick`（仅垂直切片，5 分钟）
- **风险 4：act 与真实 GitHub Actions 行为差异**：部分 actions 可能不兼容。**应对**：关键 workflow 在生产环境复验
- **风险 5：Flask Mock Server 并发不足**：高并发测试时可能崩溃。**应对**：使用 `gunicorn -w 4` 或 `pytest-parallel`

**成本估算**：

- 人力：22 人天（Fixture: 3 + Mock Server: 3 + 单元测试: 4 + 契约测试: 2 + 集成测试: 3 + E2E: 3 + CI 模拟: 2 + 校验: 2）
- 时间：3 周（与开发并行）
- 技术债务：Mock 数据范围有限（5 日期 vs 366 天）
- 维护：长期投入 3-5 小时/周（Mock 数据更新 + 契约同步）
- 财务：本地 $0

**致命失败场景**：

1. **场景 A**：Mock 数据与真实 API 响应差异过大，本地测试通过但生产失败。**触发条件**：Mock 未覆盖真实 API 的边界字段。**应对**：生产迁移前用真实 API 录制响应（VCR.py），对比 Mock 差异。
2. **场景 B**：契约设计错误导致 schemathesis 误报。**触发条件**：OpenAPI 契约与真实 API 不一致。**应对**：契约必须基于真实 API 文档编写，且每次 API 升级同步更新契约。
3. **场景 C**：E2E 测试因环境问题（端口冲突、Mock Server 崩溃）频繁失败。**触发条件**：测试环境不稳定。**应对**：使用 `pytest-xdist` 隔离测试环境，每个测试用例启动独立 Mock Server 实例。
4. **场景 D**：act 无法模拟复杂的 GitHub Actions workflow（如 matrix、secrets）。**触发条件**：workflow 使用高级特性。**应对**：关键 workflow 必须在生产环境复验，act 仅用于快速反馈。

---

### 方案2：VCR.py 录制回放方案（生产数据驱动派）

**核心思路**（289 字）：

放弃人工编写 Mock 数据，改用 VCR.py 录制真实 API 响应。在首次运行时（需临时网络访问），用 VCR.py 录制 Wikipedia/Claude/GPT-4o/Gemini 的真实响应，保存为 YAML cassette。后续运行直接回放 cassette，无需网络访问。Provider 接口不变，但 Mock 实现改为"VCR 回放模式"。该方案核心优势是"Mock 数据 100% 真实"，能完全复现生产 API 行为；但要求首次运行时有网络访问，且 cassette 维护需要同步更新。

**实施步骤**：

1. **Phase A：首次录制（需临时网络）**
   - 安装 VCR.py：`pip install vcrpy`
   - 配置 `conftest.py`：`@vcr.use_cassette('fixtures/vcr/{test_name}.yaml')`
   - 在有网络的环境运行一次完整测试套件，录制所有 API 响应
   - 将 cassette 文件提交到 Git

2. **Phase B：回放模式**
   - 默认所有测试使用 VCR 回放
   - Provider Mock 实现改为：`httpx.get(url)` + VCR 拦截
   - 无需 Flask Mock Server（VCR 直接拦截 httpx 请求）

3. **Phase C：cassette 维护**
   - 编写 `scripts/refresh_cassettes.py`：重新录制所有 cassette
   - 每月或 API 升级时重新录制
   - 提供 `--record` flag 切换录制/回放模式

**Mock 体系设计**：

| 外部依赖 | Mock 策略 | 工具/库 | 响应数据来源 | 校验点 |
|---------|----------|---------|-------------|--------|
| Wikipedia API | VCR.py 录制回放 | vcrpy | fixtures/vcr/wikipedia/*.yaml | 真实响应 100% 复现 |
| Anthropic Claude | VCR.py 录制回放 | vcrpy | fixtures/vcr/anthropic/*.yaml | 真实响应 100% 复现 |
| OpenAI GPT-4o | VCR.py 录制回放 | vcrpy | fixtures/vcr/openai/*.yaml | 真实响应 100% 复现 |
| Google Gemini | VCR.py 录制回放 | vcrpy | fixtures/vcr/gemini/*.yaml | 真实响应 100% 复现 |

**预期效果**：

- Mock 数据 100% 真实，能完全复现生产 API 行为
- 无需 Flask Mock Server，简化架构
- cassette 文件可读性强，便于调试

**潜在风险**：

- **风险 1：首次录制需网络访问**：用户当前无法访问国外网站。**应对**：寻找有网络的环境（如朋友电脑、云服务器）录制，或将 cassette 文件作为项目资产分享
- **风险 2：cassette 维护成本**：API 升级后需重新录制。**应对**：编写 `refresh_cassettes.py` 自动化录制流程
- **风险 3：cassette 文件体积大**：单个 YAML 可能几 MB。**应对**：使用 `filter_post_data_parameters` 过滤敏感信息，`allow_playback_repeats=True` 减少重复录制
- **风险 4：无法模拟延迟**：VCR 回放是即时的。**应对**：在 Provider 层注入 `asyncio.sleep(delay)` 模拟延迟

**成本估算**：

- 人力：15 人天（录制: 3 + 集成: 5 + 测试: 5 + 维护脚本: 2）
- 时间：2 周
- 技术债务：cassette 维护依赖网络访问
- 维护：长期投入 2-3 小时/周
- 财务：本地 $0；首次录制可能需临时网络（$0-10）

**致命失败场景**：

1. **场景 A**：无法获得首次录制所需的网络访问。**触发条件**：用户长期无国外网络。**应对**：降级到方案1 的人工 Mock 数据。
2. **场景 B**：cassette 过期导致测试失败。**触发条件**：API 升级但 cassette 未更新。**应对**：建立月度 cassette 刷新流程。
3. **场景 C**：cassette 包含敏感信息（API Key）。**触发条件**：录制时未过滤。**应对**：使用 `before_record_request` 过滤敏感 header。

---

### 方案3：Property-Based Testing + Hypothesis 方案（边缘用例发现派）

**核心思路**（287 字）：

放弃"穷举测试用例"思路，改用 Property-Based Testing（基于属性的测试）。用 `hypothesis` 库自动生成测试输入，验证 Provider 接口和管道函数的"属性"（如：任意合法输入都应返回合法输出、任意日期都应生成非空事件池、任意语种都应完整翻译）。该方案核心优势是"自动发现边缘用例"，能暴露人工测试遗漏的边界场景；但测试执行时间较长，且属性定义需要深入理解业务。

**实施步骤**：

1. **Phase A：属性定义**
   - 为每个 Provider 接口定义属性：
     - WikipediaFetcher: `forall date in [01-01, 12-31]: fetch(date).events is non-empty`
     - Regionalizer: `forall events, countries: regionalize(events, countries).regional_events has same total count`
     - Translator: `forall events, langs: translate(events, langs).locales has all langs`
   - 编写 `tests/properties/test_providers_properties.py`

2. **Phase B：策略定义**
   - 用 `hypothesis.strategies` 定义输入生成策略：
     - `dates_strategy`: 生成 01-01 到 12-31 的日期
     - `countries_strategy`: 生成 30 地区的子集
     - `langs_strategy`: 生成 10 语种的子集
   - 编写 `tests/strategies.py`

3. **Phase C：属性测试执行**
   - 配置 hypothesis：`max_examples=100`，`deadline=5000ms`
   - 在 CI 中加入 `pytest tests/properties/ --hypothesis-show-statistics`
   - 发现的边缘用例自动保存为 regression test

**Mock 体系设计**：

| 外部依赖 | Mock 策略 | 工具/库 | 响应数据来源 | 校验点 |
|---------|----------|---------|-------------|--------|
| Wikipedia API | Flask + hypothesis 生成 | Flask + hypothesis | 动态生成 | 属性不变式 |
| Anthropic Claude | Flask + hypothesis 生成 | Flask + hypothesis | 动态生成 | 属性不变式 |
| OpenAI GPT-4o | Flask + hypothesis 生成 | Flask + hypothesis | 动态生成 | 属性不变式 |
| Google Gemini | Flask + hypothesis 生成 | Flask + hypothesis | 动态生成 | 属性不变式 |

**预期效果**：

- 自动发现边缘用例（如：闰年 02-29、空事件日、超长标题）
- 测试覆盖率从 80% 提升到 95%+
- 属性不变式作为"活文档"，明确接口契约

**潜在风险**：

- **风险 1：测试执行时间长**：100 个示例 × 10 个属性 = 1000 次测试。**应对**：在 CI 中分为快速测试（10 示例）和深度测试（100 示例）
- **风险 2：属性定义错误导致假阳性**：属性过严会阻塞开发，过松会遗漏 bug。**应对**：属性需代码评审，且定期回顾
- **风险 3：hypothesis 生成的输入超出 Mock 范围**：Mock Server 可能无法响应。**应对**：Mock Server 实现"通用回退"响应，对未知输入返回合理默认值

**成本估算**：

- 人力：12 人天（属性定义: 4 + 策略定义: 3 + 测试执行: 3 + 调优: 2）
- 时间：2 周
- 技术债务：属性维护成本（业务变更需同步更新属性）
- 维护：长期投入 2-3 小时/周
- 财务：本地 $0

**致命失败场景**：

1. **场景 A**：属性定义过严导致所有测试失败。**触发条件**：属性未考虑边界情况。**应对**：先放宽属性，再逐步收紧。
2. **场景 B**：hypothesis 发现的边缘用例无法修复（如：Mock Server 不支持某些输入）。**应对**：在 Mock Server 实现"通用回退"逻辑。
3. **场景 C**：属性测试执行时间超出 CI 预算。**应对**：分级执行，关键属性在 CI 跑，全量属性在夜间跑。

---

## 方案对比与测试架构师推荐

### 三方案测试对比矩阵

| 测试维度 | 方案1（分层 Mock + 金字塔） | 方案2（VCR 录制回放） | 方案3（Property-Based） |
|---------|--------------------------|---------------------|----------------------|
| **Mock 数据真实性** | ⭐⭐⭐ 中等（人工 + 模板） | ⭐⭐⭐⭐⭐ 高（真实响应） | ⭐⭐ 低（动态生成） |
| **边缘用例发现** | ⭐⭐⭐ 中等（依赖人工） | ⭐⭐ 低（仅录制场景） | ⭐⭐⭐⭐⭐ 高（自动生成） |
| **首次部署成本** | ⭐⭐⭐⭐ 低（无需网络） | ⭐ 低（需网络录制） | ⭐⭐⭐⭐ 低（无需网络） |
| **维护成本** | ⭐⭐⭐ 中等 | ⭐⭐ 高（cassette 同步） | ⭐⭐⭐⭐ 低（属性稳定） |
| **测试执行速度** | ⭐⭐⭐⭐ 快（< 5min） | ⭐⭐⭐⭐⭐ 最快（回放） | ⭐⭐ 慢（100 示例） |
| **架构复杂度** | ⭐⭐⭐ 中等（需 Flask Server） | ⭐⭐ 低（VCR 拦截） | ⭐⭐⭐ 中等（需属性定义） |

### 测试架构师推荐

**首选方案：方案1（分层 Mock + 测试金字塔方案）**

**推荐理由（压倒性优势）**：

1. **首次部署无需网络**：完全符合用户"无法访问国外网站"的约束
2. **测试金字塔清晰**：单元/集成/E2E 三层分工明确，覆盖率目标可量化
3. **Mock 数据可控**：人工编写 + 模板生成，可针对特定场景调试
4. **与方案1（技术实现者）完美配合**：Flask Mock Server 复用，无额外架构

**次选方案：方案3（Property-Based Testing）**

可作为方案1 的补充，用于发现边缘用例。建议在方案1 完成后，对核心 Provider 接口增加 Property-Based 测试。

**不推荐方案2（VCR 录制回放）**：

虽然 Mock 数据真实性最高，但首次录制需网络访问，不符合用户当前约束。可在生产迁移阶段使用 VCR.py 录制真实响应，作为生产验证手段。

### 测试架构师最终建议

采用**方案1 为主框架**，在核心接口上叠加方案3 的 Property-Based 测试：

- **方案1 提供**：完整的 Mock 体系 + 测试金字塔 + CI 模拟
- **方案3 补充**：对 WikipediaFetcher / Regionalizer / Translator 三个核心接口增加属性测试
- **方案2 延后**：生产迁移阶段用 VCR.py 录制真实响应，对比 Mock 差异

这样既保证了本地可执行性，又获得了边缘用例发现能力，还为生产验证预留了路径。

---

## 附录：每个开发步骤的测试验收清单

| 步骤号 | 步骤名称 | 测试验收清单 |
|--------|---------|------------|
| S01 | 环境搭建 | `pytest --version` / `hugo version` / `act --version` 可执行 |
| S02 | 配置双轨制 | `pytest tests/unit/test_config.py` 通过；`ENV=local` 和 `ENV=production` 切换生效 |
| S03 | Provider 接口 | `pytest tests/unit/test_providers.py` 通过；6 个接口的 Mock 实现可实例化 |
| S04 | Mock 实现 | `pytest tests/unit/test_mock_*.py` 全部通过；契约测试 100% 通过 |
| S05 | Flask Mock Server | `pytest tests/integration/test_mock_server.py` 通过；6 个端点返回符合契约的 JSON |
| S06 | Mock 数据生成 | `python -m src.scripts.gen_mock_data` 生成 450 个 fixture；`jsonschema` 校验通过 |
| S07 | Stage 1 fetch | `pytest tests/unit/test_fetch.py` 通过；5 日期样本全部 fetch 成功 |
| S08 | Stage 2 regionalize | `pytest tests/unit/test_regionalize.py` 通过；中立性评分 ≥ 0.7 |
| S09 | Stage 3 translate | `pytest tests/unit/test_translate.py` 通过；10 语种完整翻译 |
| S10 | Stage 4 illustrate | `pytest tests/unit/test_illustrate.py` 通过；图片 URL 可访问 |
| S11 | Stage 5 audit | `pytest tests/unit/test_audit.py` 通过；审核报告字段完整 |
| S12 | Stage 6 publish | `pytest tests/unit/test_publish.py` 通过；300 个 Markdown 文件生成 |
| S13 | Stage 7 build | `pytest tests/integration/test_hugo_build.py` 通过；HTML 校验 0 错误 |
| S14 | 管道编排 | `pytest tests/integration/test_pipeline_e2e.py` 通过；单日管道 < 5min |
| S15 | Hugo 骨架 | `hugo --templateMetrics` 输出正常；Lighthouse SEO > 95 |
| S16 | 10 万页生成 | 109,800 个 _index.md 生成；Hugo 构建 < 10min |
| S17 | 测试体系 | `make test` 全部通过；覆盖率 ≥ 80% |
| S18 | E2E 脚本 | `make e2e` 全部通过；端到端 < 20min |
| S19 | Makefile | `make ci` 全部通过；`act -j test` 通过 |
| S20 | 性能验证 | `make perf` 通过；性能预算达标率 100% |

---

**方案版本**：v1.0（第 1 轮独立分析）
**编写者**：测试架构师（R_test_architect）
**待第 2 轮融合**：与 R_tech_implementer 协调 Mock 端口（8765）与 fixture 路径；与 R_strategist 协调测试阶段划分；与 R_perf_engineer 协调性能测试工具；与 R_risk_analyst 协调测试风险登记。
