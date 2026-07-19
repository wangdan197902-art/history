# 技术实现者方案 — 第 1 轮

> 角色：技术实现者（R_tech_implementer）
> 视角：实现路径细化 / 技术栈适配 / 编码规范 / 工程最佳实践 / 可维护性编码
> 输出范围：本地全链路开发计划的编码落地方案，含每步骤的文件清单、关键函数、依赖管理
> 编写日期：2026-07-19

---

## 角色定位

技术实现者，聚焦**工程落地能力**。在本项目中负责：

1. 将抽象的"本地全链路模拟"需求转化为具体可执行的编码任务清单
2. 设计 Mock 体系的代码骨架（Wikipedia/AI API/Cloudflare Pages Mock）
3. 设计 Python 管道脚本的本地可运行版本（基于 Provider 接口抽象）
4. 设计配置双轨制（local/production）的代码组织
5. 为每个开发步骤提供"文件路径 + 关键函数签名 + 依赖库 + 验收命令"的精确清单

**核心立场**：方案必须可落地，每个步骤的产出物是"可执行的代码"而非"待补充的伪代码"。

---

## 关键技术决策

### 1. 技术栈选型

| 模块 | 技术选型 | 理由 |
|------|---------|------|
| Mock Server | Flask 3.0+ | 轻量、生态成熟、与 Python 管道同语言、调试方便 |
| AI API Mock | 响应回放（VCR.py）+ 规则模板 | 无需本地 LLM，避免 Ollama 资源占用 |
| 管道编排 | Python asyncio + httpx | 异步 IO 提升并发，httpx 兼容 sync/async |
| 配置管理 | pydantic-settings + .env | 类型安全、双轨制切换零代码改动 |
| 数据校验 | pydantic v2 + JSON Schema | 与管道数据模型统一 |
| Hugo 资源管理 | Hugo Modules + assets pipeline | 原生支持，无外部依赖 |
| 测试框架 | pytest + pytest-asyncio + responses | 标准工具链 |
| Mock 数据存储 | tests/fixtures/{service}/{scenario}.json | 版本化、可追溯 |

### 2. 目录结构设计

```
03-地区化今天历史档案站/
├── docs/                              # 现有方案文档（不动）
├── 头脑风暴记录/                       # 头脑风暴产出
├── 开发计划/                           # 【新增】开发步骤独立文件
│   ├── 00_总览.md
│   ├── S01_环境搭建.md
│   ├── S02_Hugo骨架.md
│   ├── ...
│   └── S20_生产迁移.md
├── src/                               # 【新增】项目源码
│   ├── config/                        # 配置双轨制
│   │   ├── __init__.py
│   │   ├── base.py                    # Settings 基类
│   │   ├── local.py                   # 本地配置
│   │   └── production.py              # 生产配置
│   ├── providers/                     # Provider 接口抽象
│   │   ├── __init__.py
│   │   ├── base.py                    # 抽象基类
│   │   ├── wikipedia.py               # Wikipedia Provider
│   │   ├── anthropic.py               # Claude Provider
│   │   ├── openai.py                  # GPT-4o Provider
│   │   ├── gemini.py                  # Gemini Provider
│   │   └── impl/                      # 具体实现
│   │       ├── mock_wikipedia.py
│   │       ├── mock_anthropic.py
│   │       ├── mock_openai.py
│   │       ├── mock_gemini.py
│   │       ├── real_wikipedia.py
│   │       ├── real_anthropic.py
│   │       ├── real_openai.py
│   │       └── real_gemini.py
│   ├── pipeline/                      # 管道 7 阶段
│   │   ├── __init__.py
│   │   ├── fetch.py                   # Stage 1
│   │   ├── regionalize.py             # Stage 2
│   │   ├── translate.py               # Stage 3
│   │   ├── illustrate.py              # Stage 4
│   │   ├── audit.py                   # Stage 5
│   │   ├── publish.py                 # Stage 6
│   │   ├── build.py                   # Stage 7（Hugo 构建）
│   │   └── orchestrator.py            # 编排器
│   ├── mock_server/                   # Flask Mock Server
│   │   ├── __init__.py
│   │   ├── app.py                     # Flask 应用
│   │   ├── routes_wikipedia.py
│   │   ├── routes_anthropic.py
│   │   ├── routes_openai.py
│   │   ├── routes_gemini.py
│   │   └── data_loader.py             # Mock 数据加载器
│   ├── hugo/                          # Hugo 站点
│   │   ├── hugo.toml
│   │   ├── layouts/
│   │   │   ├── _default/
│   │   │   │   ├── day.html
│   │   │   │   ├── list.html
│   │   │   │   └── home.html
│   │   │   └── partials/
│   │   │       ├── hreflang.html
│   │   │       ├── schema-event.html
│   │   │       ├── breadcrumb.html
│   │   │       └── event-card.html
│   │   ├── content/                   # 生成的 Markdown
│   │   │   ├── en/on-this-day/us/07-04.md
│   │   │   └── ...
│   │   ├── assets/
│   │   │   ├── css/
│   │   │   ├── js/
│   │   │   └── images/
│   │   ├── static/
│   │   └── data/                      # 事件 JSON 数据
│   │       └── events/07-04.json
│   ├── scripts/                       # 运维脚本
│   │   ├── gen_mock_data.py           # 生成 Mock 数据
│   │   ├── gen_blank_pages.py         # 生成空白 _index.md
│   │   ├── batch_backfill.py          # 批量回填内容
│   │   ├── local_e2e.sh               # 本地 E2E 脚本
│   │   └── perf_monitor.py            # 性能监控
│   └── tests/                         # 测试
│       ├── fixtures/                  # Mock 数据
│       │   ├── wikipedia/
│       │   │   ├── 07-04.json
│       │   │   └── ...
│       │   ├── anthropic/
│       │   │   ├── us-07-04-regionalized.json
│       │   │   └── ...
│       │   ├── openai/
│       │   ├── gemini/
│       │   └── expected/              # 期望输出
│       ├── unit/
│       ├── integration/
│       └── e2e/
├── tests/contracts/                   # API 契约
│   ├── wikipedia-onthisday.openapi.yaml
│   ├── anthropic-messages.openapi.yaml
│   ├── openai-chat.openapi.yaml
│   ├── gemini-generate.openapi.yaml
│   ├── cloudflare-pages.openapi.yaml
│   └── buttondown.openapi.yaml
├── tech-debt-ledger.md                # 技术债务登记
├── requirements.txt
├── pyproject.toml
├── Makefile
└── .env.example
```

---

## 方案清单

### 方案1：Provider 抽象 + Flask Mock Server 单体方案（推荐 — 工程落地派）

**核心思路**（287 字）：

将所有外部依赖抽象为 `Provider` 接口（Python ABC），每个外部服务对应一个接口（WikipediaFetcher / Regionalizer / Translator / Illustrator / Auditor / Publisher）。每个接口有两个实现：`MockXxx`（本地用）和 `RealXxx`（生产用）。通过 pydantic-settings 的 `ENV` 环境变量切换实现，**代码零修改**。Mock 实现调用本地 Flask Server（端口 8765），Flask 从 `tests/fixtures/` 加载预录制的 JSON 响应。管道编排器 `orchestrator.py` 串联 7 阶段，每阶段用 asyncio 并发处理多地区/多语种。该方案核心优势是"一套代码双轨运行"，本地跑通后生产迁移是配置切换而非代码重写。

**实施步骤**：

1. **Phase A：项目骨架与配置双轨制**
   - 创建 `pyproject.toml`，依赖：flask、httpx、pydantic、pydantic-settings、pytest、pytest-asyncio
   - 实现 `src/config/base.py` 的 `Settings` 基类（pydantic-settings）
   - 实现 `src/config/local.py` 和 `src/config/production.py`
   - 编写 `.env.example` 文件
   - 编写 `Makefile`：`make setup` / `make mock` / `make pipeline` / `make build` / `make test`

2. **Phase B：Provider 接口与 Mock 实现**
   - 定义 6 个 Provider 抽象基类（`src/providers/base.py`）
   - 实现 6 个 Mock 实现（`src/providers/impl/mock_*.py`）
   - 每个 Mock 实现通过 httpx 调用 Flask Mock Server
   - 编写 `src/providers/__init__.py` 的 `get_provider(name)` 工厂函数

3. **Phase C：Flask Mock Server**
   - 实现 `src/mock_server/app.py`：Flask 应用入口
   - 实现 4 个路由模块：wikipedia / anthropic / openai / gemini
   - 实现 `src/mock_server/data_loader.py`：从 `tests/fixtures/` 加载 JSON
   - 编写 `scripts/start_mock_server.sh` 一键启动
   - 实现 Mock 数据生成器 `src/scripts/gen_mock_data.py`

4. **Phase D：管道 7 阶段实现**
   - 实现 `src/pipeline/fetch.py`：`async def fetch_events(date, fetcher) -> EventPool`
   - 实现 `src/pipeline/regionalize.py`：`async def regionalize(events, countries, regionalizer) -> RegionalEvents`
   - 实现 `src/pipeline/translate.py`：`async def translate(events, langs, translator) -> TranslatedEvents`
   - 实现 `src/pipeline/illustrate.py`：`async def illustrate(events, illustrator) -> IllustratedEvents`
   - 实现 `src/pipeline/audit.py`：`async def audit(events, auditor) -> AuditReport`
   - 实现 `src/pipeline/publish.py`：`async def publish(events, publisher) -> PublishResult`
   - 实现 `src/pipeline/build.py`：`def build_hugo() -> BuildResult`（subprocess 调用 hugo）
   - 实现 `src/pipeline/orchestrator.py`：`async def run_pipeline(date, config) -> PipelineResult`

5. **Phase E：Hugo 站点骨架**
   - 编写 `src/hugo/hugo.toml`（10 语种配置 + 30 地区 menus）
   - 实现 `layouts/_default/day.html`（日期页模板）
   - 实现 `layouts/_default/list.html`（列表页模板）
   - 实现 `layouts/_default/home.html`（首页模板）
   - 实现 5 个 partials：hreflang / schema-event / breadcrumb / event-card / related-countries
   - 编写 `assets/css/main.css`（响应式 + 30 地区导航）

6. **Phase F：测试与 E2E**
   - 编写单元测试 `tests/unit/test_providers.py`
   - 编写集成测试 `tests/integration/test_pipeline.py`
   - 编写 E2E 脚本 `scripts/local_e2e.sh`
   - 编写 Mock 数据生成器 `src/scripts/gen_mock_data.py`（30 地区 × 5 日期 × 3 语种样本）

**关键编码任务清单**：

| 序号 | 文件路径 | 关键函数/类 | 依赖库 | 验收命令 |
|------|---------|------------|--------|---------|
| 1 | src/config/base.py | `Settings(BaseSettings)` | pydantic-settings | `python -c "from src.config import get_settings; print(get_settings())"` |
| 2 | src/providers/base.py | `WikipediaFetcher(ABC)`, `Regionalizer(ABC)`, `Translator(ABC)`, `Illustrator(ABC)`, `Auditor(ABC)`, `Publisher(ABC)` | abc | `python -c "from src.providers.base import WikipediaFetcher"` |
| 3 | src/providers/__init__.py | `get_provider(name: str) -> Any` | — | `python -c "from src.providers import get_provider; print(get_provider('wikipedia'))"` |
| 4 | src/providers/impl/mock_wikipedia.py | `MockWikipediaFetcher(WikipediaFetcher)` | httpx | `pytest tests/unit/test_mock_wikipedia.py` |
| 5 | src/providers/impl/real_wikipedia.py | `RealWikipediaFetcher(WikipediaFetcher)` | httpx | `pytest tests/unit/test_real_wikipedia.py` |
| 6 | src/mock_server/app.py | `create_app() -> Flask` | flask | `flask --app src.mock_server.app run -p 8765` |
| 7 | src/mock_server/routes_wikipedia.py | `bp_wikipedia = Blueprint('wikipedia', __name__)` | flask | `curl http://localhost:8765/api/wikipedia/onthisday/07/04` |
| 8 | src/mock_server/data_loader.py | `load_fixture(service: str, scenario: str) -> dict` | — | `python -c "from src.mock_server.data_loader import load_fixture; print(load_fixture('wikipedia', '07-04'))"` |
| 9 | src/pipeline/fetch.py | `async def fetch_events(date: str, fetcher: WikipediaFetcher) -> EventPool` | httpx, pydantic | `pytest tests/unit/test_fetch.py` |
| 10 | src/pipeline/regionalize.py | `async def regionalize(events: EventPool, countries: list[str], regionalizer: Regionalizer) -> RegionalEvents` | — | `pytest tests/unit/test_regionalize.py` |
| 11 | src/pipeline/translate.py | `async def translate(events: RegionalEvents, langs: list[str], translator: Translator) -> TranslatedEvents` | — | `pytest tests/unit/test_translate.py` |
| 12 | src/pipeline/illustrate.py | `async def illustrate(events: TranslatedEvents, illustrator: Illustrator) -> IllustratedEvents` | — | `pytest tests/unit/test_illustrate.py` |
| 13 | src/pipeline/audit.py | `async def audit(events: IllustratedEvents, auditor: Auditor) -> AuditReport` | — | `pytest tests/unit/test_audit.py` |
| 14 | src/pipeline/publish.py | `async def publish(events: IllustratedEvents, publisher: Publisher) -> PublishResult` | — | `pytest tests/unit/test_publish.py` |
| 15 | src/pipeline/build.py | `def build_hugo(base_url: str = None) -> BuildResult` | subprocess | `python -c "from src.pipeline.build import build_hugo; print(build_hugo())"` |
| 16 | src/pipeline/orchestrator.py | `async def run_pipeline(date: str, config: Settings) -> PipelineResult` | asyncio | `ENV=local python -m src.pipeline.orchestrator 2026-07-04` |
| 17 | src/scripts/gen_mock_data.py | `def gen_wikipedia_fixtures() -> None`, `def gen_ai_fixtures() -> None` | — | `python -m src.scripts.gen_mock_data` |
| 18 | src/scripts/gen_blank_pages.py | `def gen_blank_pages(langs: list, countries: list, days: list) -> None` | — | `python -m src.scripts.gen_blank_pages` |
| 19 | src/scripts/batch_backfill.py | `def batch_backfill(date_range: tuple) -> None` | — | `python -m src.scripts.batch_backfill` |
| 20 | scripts/local_e2e.sh | bash 脚本：启动 mock → 跑管道 → 构建 Hugo → 启动预览 | — | `bash scripts/local_e2e.sh` |
| 21 | src/hugo/hugo.toml | Hugo 配置文件 | — | `cd src/hugo && hugo server` |
| 22 | src/hugo/layouts/_default/day.html | Hugo 日期页模板 | — | `hugo --templateMetrics` |
| 23 | src/hugo/layouts/partials/hreflang.html | hreflang partial | — | 检查 HTML 输出 |
| 24 | src/hugo/layouts/partials/schema-event.html | JSON-LD Event schema | — | 用 Schema.org validator 校验 |
| 25 | tests/contracts/wikipedia-onthisday.openapi.yaml | OpenAPI 契约 | — | `redocly lint tests/contracts/wikipedia-onthisday.openapi.yaml` |
| 26 | tests/fixtures/wikipedia/07-04.json | Mock 数据样本 | — | `python -m json.tool tests/fixtures/wikipedia/07-04.json` |
| 27 | tests/unit/test_providers.py | Provider 单元测试 | pytest | `pytest tests/unit/test_providers.py -v` |
| 28 | tests/integration/test_pipeline.py | 管道集成测试 | pytest | `pytest tests/integration/test_pipeline.py -v` |
| 29 | Makefile | `make setup / mock / pipeline / build / test / e2e` | — | `make e2e` |
| 30 | .env.example | 环境变量模板 | — | `cp .env.example .env` |
| 31 | requirements.txt | Python 依赖清单 | — | `pip install -r requirements.txt` |
| 32 | pyproject.toml | 项目配置 | — | `pip install -e .` |
| 33 | tech-debt-ledger.md | 技术债务登记表 | — | 人工检查 |

**预期效果**：

- 本地一键启动：`make e2e` 在 20 分钟内完成"启动 Mock → 跑管道 → 构建 Hugo → 启动预览"
- 生产迁移：仅修改 `.env` 文件，代码零修改
- 测试覆盖率：核心 Provider 100%，管道阶段 80%+
- 10 万页面 Hugo 构建能力验证通过
- 用户可在 `http://localhost:1313` 看到真实可浏览的网站

**潜在风险**：

- **风险 1：Mock 数据质量不足以验证模板**：通过 `gen_mock_data.py` 生成 30 地区 × 5 日期 × 3 语种样本，覆盖主要场景；后期扩展到 366 天
- **风险 2：Provider 接口设计过早抽象**：在 Phase B 完成后立即用 1 日 × 1 地区 × 1 语种做垂直切片验证，验证接口合理性
- **风险 3：Flask Mock Server 并发不足**：Flask 默认单线程，开发模式启用 `threaded=True`；高并发场景用 `gunicorn -w 4`
- **风险 4：Hugo 10 万页构建 OOM**：参考性能工程师方案，启用 `--cacheDir` + 分批构建
- **风险 5：asyncio 在 Mac 上的 fd 限制**：`ulimit -n 65535` 提前设置

**成本估算**：

- 人力：35 人天（Phase A: 3 + B: 5 + C: 5 + D: 8 + E: 6 + F: 5 + 联调: 3）
- 时间：5 周（含缓冲）
- 技术债务：8 项显式登记（Mock 数据范围、AI 响应质量、CDN 性能、CI 复杂度等）
- 维护：长期投入 5-8 小时/周
- 财务：本地 $0；生产迁移 $30-50

**致命失败场景**：

1. **场景 A**：Provider 接口设计错误导致 Real 实现无法满足。**触发条件**：接口未考虑真实 API 的分页、错误码、限流。**应对**：Phase B 完成后立即用真实 API 样本（即使少量）验证契约。
2. **场景 B**：Flask Mock Server 在高并发下崩溃。**触发条件**：30 地区 × 10 语种 = 300 并发请求。**应对**：使用 Semaphore(16) 限流，或切换到 gunicorn。
3. **场景 C**：Hugo 10 万页构建持续 OOM。**触发条件**：本地机器 < 16GB 内存。**应对**：参考性能工程师方案 1，启用分批构建 + `--cacheDir`。
4. **场景 D**：管道某阶段数据格式不一致导致下游崩溃。**触发条件**：pydantic 模型未覆盖所有字段。**应对**：所有阶段间数据用 pydantic 模型校验，启用 `strict=True`。

---

### 方案2：基于 Ollama 本地 LLM 的"真实 AI 验证"方案（质量优先派）

**核心思路**（295 字）：

方案1 的 Mock AI 响应是预录制的，无法验证"AI 提示词工程"的有效性。本方案在方案1 基础上，新增本地 LLM 验证层：用 Ollama 运行 Qwen2.5-7B（中文强）和 Llama-3.1-8B（英文强）作为 Claude/GPT-4o 的本地替代，让 AI 管道在本地跑真实的 LLM 推理。Provider 接口扩展为三实现：`MockXxx`（Flask 回放）、`LocalLLMXxx`（Ollama 真实推理）、`RealXxx`（生产 API）。开发期默认用 MockXxx（快速反馈），关键节点切换到 LocalLLMXxx 验证提示词效果，生产切换到 RealXxx。该方案核心优势是"提示词工程在本地可验证"，避免生产迁移时才发现提示词失效。

**实施步骤**：

1. **Phase A-G**：与方案1 完全相同
2. **Phase H（新增）：Ollama 集成**
   - 安装 Ollama（Mac 版本）
   - 下载模型：`ollama pull qwen2.5:7b-instruct` 和 `ollama pull llama3.1:8b-instruct`
   - 实现 `src/providers/impl/local_llm_anthropic.py`：调用 Ollama API 模拟 Claude
   - 实现 `src/providers/impl/local_llm_openai.py`：调用 Ollama API 模拟 GPT-4o
   - 实现 `src/providers/impl/local_llm_gemini.py`：用 Stable Diffusion 本地生成图片
   - 扩展 `Settings`：新增 `AI_MODE = mock | local_llm | real`
   - 编写提示词验证脚本 `scripts/validate_prompts.py`

3. **Phase I（新增）：提示词工程验证**
   - 编写 10 个测试用例（3 地区 × 3 日期 + 1 边界）
   - 对每个用例用 LocalLLM 跑完整管道
   - 人工评估输出质量（中立性、准确性、流畅度）
   - 调优提示词模板，迭代到质量可接受

**关键编码任务清单**（在方案1 基础上新增）：

| 序号 | 文件路径 | 关键函数/类 | 依赖库 | 验收命令 |
|------|---------|------------|--------|---------|
| 34 | src/providers/impl/local_llm_anthropic.py | `LocalLLMAnthropic(Regionalizer)` | ollama | `pytest tests/unit/test_local_llm_anthropic.py` |
| 35 | src/providers/impl/local_llm_openai.py | `LocalLLMOpenAI(Translator)` | ollama | `pytest tests/unit/test_local_llm_openai.py` |
| 36 | src/providers/impl/local_llm_gemini.py | `LocalLLMGemini(Illustrator)` | diffusers | `pytest tests/unit/test_local_llm_gemini.py` |
| 37 | scripts/validate_prompts.py | `def validate_prompts(test_cases: list) -> Report` | — | `python scripts/validate_prompts.py` |
| 38 | tests/fixtures/prompts/regionalize.txt | Claude 提示词模板 | — | 人工审阅 |
| 39 | tests/fixtures/prompts/translate.txt | GPT-4o 提示词模板 | — | 人工审阅 |

**预期效果**：

- 提示词工程在本地可验证，避免生产迁移时才发现提示词失效
- 10 个测试用例的 AI 输出质量可接受（中立性评分 ≥ 0.7）
- 生产迁移时 Real API 输出质量与 LocalLLM 输出质量差异 < 20%

**潜在风险**：

- **风险 1：Ollama 模型占用资源大**：Qwen2.5-7B 约 4.5GB 内存，Llama-3.1-8B 约 5GB 内存，两模型同时运行需 10GB+。**应对**：分时运行，或仅运行一个模型
- **风险 2：本地 LLM 输出质量与 Claude/GPT-4o 差异大**：7B 模型远逊于 Claude 3.5 Sonnet。**应对**：仅用于验证提示词结构有效性，不用于验证最终质量
- **风险 3：推理速度慢**：7B 模型在 Mac M1 上约 10-20 tokens/s，单次调用 30-60 秒。**应对**：仅用于关键节点验证，不用于日常开发
- **风险 4：Stable Diffusion 本地生成图片质量差**：可能无法替代 Gemini 配图。**应对**：图片生成保留 Mock 模式，仅文本生成用 LocalLLM

**成本估算**：

- 人力：42 人天（方案1 的 35 + Phase H: 4 + Phase I: 3）
- 时间：6 周
- 技术债务：本地 LLM 与生产 AI 的质量差异（需在生产环境最终验证）
- 维护：长期投入 8-10 小时/周（含 Ollama 模型更新）
- 财务：本地 $0；生产迁移 $30-50

**致命失败场景**：

1. **场景 A**：本地 LLM 输出质量过差，导致提示词调优无效。**触发条件**：7B 模型无法理解复杂的历史地区化任务。**应对**：降级到方案1 的纯 Mock 模式，提示词调优延迟到生产环境。
2. **场景 B**：Mac 资源不足导致 Ollama 崩溃。**触发条件**：8GB Mac 同时运行 Hugo 构建 + Ollama。**应对**：分时运行，构建时不跑 LLM。
3. **场景 C**：Ollama API 与 OpenAI/Anthropic API 差异大，Real 实现需要重写。**触发条件**：Ollama 不支持某些 API 特性（如 system prompt 格式）。**应对**：在 Provider 接口层抽象这些差异。

---

### 方案3：Docker Compose 一键环境方案（环境对等派）

**核心思路**（289 字）：

将方案1 的所有组件容器化：Flask Mock Server、Hugo、Python 管道、Ollama（可选）全部用 Docker Compose 编排。开发者只需 `docker-compose up`，无需手动安装 Hugo/Python/Node 等依赖。配置通过 `docker-compose.yml` 的 environment 字段注入，本地/生产切换通过 `docker-compose.override.yml`（本地）和 `docker-compose.prod.yml`（生产）实现。该方案核心优势是"环境一致性"和"零依赖安装"，但代价是 Docker Desktop 资源占用（建议 16GB+ Mac）。

**实施步骤**：

1. **Phase A**：编写 `Dockerfile`（Python 管道 + Flask Mock）和 `Dockerfile.hugo`（Hugo Extended）
2. **Phase B**：编写 `docker-compose.yml`，定义服务：
   - `mock-server`（Flask，端口 8765）
   - `pipeline`（Python 管道，按需运行）
   - `hugo`（Hugo server，端口 1313）
   - `ollama`（可选，端口 11434）
3. **Phase C**：编写 `docker-compose.override.yml`（本地开发配置）
4. **Phase D**：编写 `docker-compose.prod.yml`（生产部署配置，仅用于参考）
5. **Phase E**：编写 `scripts/docker_setup.sh` 一键初始化
6. **Phase F-G**：与方案1 相同的编码任务

**关键编码任务清单**（在方案1 基础上替换部分）：

| 序号 | 文件路径 | 关键函数/类 | 依赖库 | 验收命令 |
|------|---------|------------|--------|---------|
| 1 | Dockerfile | Python 管道镜像 | docker | `docker build -t today-in-history-pipeline .` |
| 2 | Dockerfile.hugo | Hugo 镜像 | docker | `docker build -t today-in-history-hugo -f Dockerfile.hugo .` |
| 3 | docker-compose.yml | 服务编排 | docker-compose | `docker-compose up -d` |
| 4 | docker-compose.override.yml | 本地覆盖配置 | docker-compose | `docker-compose config` |
| 5 | docker-compose.prod.yml | 生产参考配置 | docker-compose | `docker-compose -f docker-compose.yml -f docker-compose.prod.yml config` |
| 6 | scripts/docker_setup.sh | 一键初始化 | bash | `bash scripts/docker_setup.sh` |
| 7-33 | （同方案1） | — | — | — |

**预期效果**：

- 开发者无需安装任何依赖，`docker-compose up` 一键启动全部服务
- 环境一致性：本地、CI、生产环境使用相同 Docker 镜像
- 资源隔离：每个服务独立容器，互不干扰

**潜在风险**：

- **风险 1：Docker Desktop 资源占用大**：建议 16GB+ Mac，8GB Mac 可能卡顿。**应对**：提供"轻量模式"（仅启动 mock-server 和 hugo）
- **风险 2：Hugo 热重载在容器内可能有延迟**：volume 挂载的性能损耗。**应对**：使用 `:cached` 或 `:delegated` 挂载选项
- **风险 3：Docker 镜像构建时间长**：首次构建 5-10 分钟。**应对**：使用 BuildKit 缓存 + 多阶段构建
- **风险 4：Mac 上 Docker volume 性能差**：Hugo 构建 10 万页可能慢 2-3 倍。**应对**：使用 Docker Volume 而非 Bind Mount

**成本估算**：

- 人力：40 人天（方案1 的 35 + Docker 化: 5）
- 时间：5-6 周
- 技术债务：Docker volume 性能损耗、镜像构建时间
- 维护：长期投入 6-8 小时/周
- 财务：本地 $0；生产迁移 $30-50

**致命失败场景**：

1. **场景 A**：8GB Mac 运行 Docker 卡顿严重。**触发条件**：同时运行 mock-server + hugo + ollama 容器。**应对**：降级到方案1 的本地安装模式。
2. **场景 B**：Docker volume 性能差导致 Hugo 构建超时。**触发条件**：10 万页构建 > 30 分钟。**应对**：使用 Docker Volume + rsync 同步。
3. **场景 C**：Docker Compose 配置复杂度爆炸。**触发条件**：环境变量过多导致维护困难。**应对**：使用 `.env` 文件 + 环境变量分组。

---

## 方案对比与技术实现者推荐

### 三方案技术对比矩阵

| 技术维度 | 方案1（Provider+Flask） | 方案2（Ollama 增强） | 方案3（Docker Compose） |
|---------|----------------------|---------------------|----------------------|
| **编码复杂度** | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐ 较高 | ⭐⭐⭐ 中等 |
| **本地资源要求** | ⭐⭐⭐⭐⭐ 低（仅需 Python/Hugo） | ⭐⭐ 低（需 Ollama + 10GB+ 内存） | ⭐⭐ 低（需 Docker + 16GB+ 内存） |
| **环境一致性** | ⭐⭐⭐ 中等 | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐⭐ 高 |
| **生产迁移成本** | ⭐⭐⭐⭐⭐ 低（改 .env） | ⭐⭐⭐⭐ 低（改 .env） | ⭐⭐⭐⭐ 低（改 compose） |
| **提示词可验证性** | ⭐⭐ 低（纯 Mock） | ⭐⭐⭐⭐⭐ 高（真实 LLM） | ⭐⭐ 低（纯 Mock） |
| **开发反馈速度** | ⭐⭐⭐⭐⭐ 快 | ⭐⭐⭐ 中（LLM 推理慢） | ⭐⭐⭐⭐ 快 |
| **维护成本** | ⭐⭐⭐⭐ 低 | ⭐⭐ 高（Ollama 维护） | ⭐⭐⭐ 中（Docker 维护） |
| **测试便利性** | ⭐⭐⭐⭐⭐ 高 | ⭐⭐⭐⭐ 高 | ⭐⭐⭐ 中（容器调试） |

### 技术实现者推荐

**首选方案：方案1（Provider 抽象 + Flask Mock Server 单体方案）**

**推荐理由（压倒性优势）**：

1. **本地资源要求最低**：仅需 Python + Hugo，符合用户"无法访问国外网站"的约束
2. **生产迁移成本最低**：`ENV=production` 切换，代码零修改
3. **开发反馈速度最快**：Flask Mock 响应 < 100ms，单日管道 < 5 分钟
4. **维护成本最低**：无 Ollama/Docker 等额外依赖
5. **测试便利性最高**：pytest 直接运行，无需容器编排

**次选方案：方案2（Ollama 增强）**

如果用户本地具备 16GB+ 内存且对提示词工程有强烈验证需求，可在方案1 基础上叠加方案2 的 Ollama 集成。但需注意 7B 模型与 Claude 3.5 Sonnet 的质量差距。

**不推荐方案3（Docker Compose）**：

虽然环境对等性优秀，但 Docker Desktop 在 Mac 上的资源占用和 volume 性能损耗对开发体验影响较大。除非用户有强烈的"环境一致性"需求，否则方案1 已足够。

### 技术实现者最终建议

采用**方案1 为主框架**，预留方案2 的扩展点：

- **Provider 接口设计**时预留 `LocalLLMXxx` 实现的扩展点（接口方法签名兼容 Ollama）
- **配置系统**预留 `AI_MODE = mock | local_llm | real` 三态切换
- **文档**中说明如何按需启用 Ollama 验证（附录形式）

这样既保留了方案1 的轻量级优势，又为未来提示词验证预留了路径。

---

## 附录：开发步骤与编码任务映射表

| 开发步骤 | 对应方案1 编码任务 | 优先级 | 预估人天 |
|---------|------------------|--------|---------|
| S01 环境搭建 | 31, 32, 33 | P0 | 0.5 |
| S02 配置双轨制 | 1, 30 | P0 | 1 |
| S03 Provider 接口 | 2, 3 | P0 | 2 |
| S04 Mock 实现 | 4, 5 | P0 | 3 |
| S05 Flask Mock Server | 6, 7, 8 | P0 | 3 |
| S06 Mock 数据生成 | 17, 26 | P0 | 2 |
| S07 Stage 1 fetch | 9 | P0 | 1 |
| S08 Stage 2 regionalize | 10 | P0 | 1.5 |
| S09 Stage 3 translate | 11 | P0 | 1.5 |
| S10 Stage 4 illustrate | 12 | P0 | 1 |
| S11 Stage 5 audit | 13 | P0 | 1 |
| S12 Stage 6 publish | 14 | P0 | 1 |
| S13 Stage 7 build | 15 | P0 | 1 |
| S14 管道编排 | 16 | P0 | 2 |
| S15 Hugo 骨架 | 21, 22, 23, 24 | P0 | 3 |
| S16 10 万页生成 | 18, 19 | P0 | 2 |
| S17 测试体系 | 25, 27, 28 | P0 | 3 |
| S18 E2E 脚本 | 20 | P0 | 1 |
| S19 Makefile | 29 | P0 | 0.5 |
| S20 性能验证 | （参考性能工程师方案） | P1 | 1 |
| **合计** | — | — | **35 人天** |

---

**方案版本**：v1.0（第 1 轮独立分析）
**编写者**：技术实现者（R_tech_implementer）
**待第 2 轮融合**：与 R_test_architect 协调 Mock 端口与测试数据格式；与 R_strategist 协调阶段划分；与 R_perf_engineer 协调步骤编号；与 R_risk_analyst 协调风险登记项。
