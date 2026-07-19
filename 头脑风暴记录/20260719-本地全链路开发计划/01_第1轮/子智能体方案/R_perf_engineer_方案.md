# 性能工程师方案 — 第 1 轮

> 角色：性能工程师（R_perf_engineer）
> 视角：性能预算 / 瓶颈识别 / 缓存策略 / 并发模型 / 资源利用率 / 响应时间目标
> 输出范围：本地全链路开发计划的性能保障方案，含每开发步骤的性能预算与验收指标
> 编写日期：2026-07-19

---

## 角色定位

性能工程师，聚焦**性能预算与瓶颈优化**。在本项目中负责：
1. 制定 10 万页 Hugo 站点的本地构建性能预算（含 8GB/16GB/32GB Mac 三档）
2. 设计 Hugo 模板渲染、Python AI 管道、Mock server 三大性能热点的优化方案
3. 为每个开发步骤量化"性能预算"与"验收指标"，让性能可测量、可回归
4. 提供"本地版 → 生产版"性能差异数据，避免迁移时出现性能悬崖

**核心立场**：性能不是"做完再优化"，而是从 Step 1 就嵌入预算。本地 Mock 必须能复现生产瓶颈（10 万页构建压力），否则迁移时会暴露隐藏的 OOM/超时风险。

---

## 性能预算总览（性能工程师特色）

### A. 总体性能预算矩阵

| 指标类别 | 指标名称 | 目标值 | 本地验收 | 生产验收 | 测量工具 |
|---------|---------|--------|---------|---------|---------|
| Core Web Vitals | LCP | < 1.5s | < 1.0s（本地无 CDN） | < 1.5s（CF CDN） | Lighthouse / Chrome DevTools |
| Core Web Vitals | CLS | < 0.1 | 0 | 0 | Lighthouse |
| Core Web Vitals | INP | < 100ms | < 50ms | < 100ms | Lighthouse / RUM |
| Core Web Vitals | FCP | < 1.0s | < 0.8s | < 1.0s | Lighthouse |
| Core Web Vitals | TTFB | < 200ms | < 50ms（本地） | < 200ms（CDN） | `curl -w` |
| 构建性能 | Hugo 10 万页全量构建 | < 5min | < 10min（M 系列 8GB） | < 5min（CI 4 核） | `hugo --templateMetrics` + `time` |
| 构建性能 | Hugo 增量构建（单日） | < 30s | < 20s | < 30s | `hugo server` 热重载 |
| 构建性能 | Hugo 构建峰值内存 | < 4GB | < 4GB | < 2GB（CI） | `/usr/bin/time -v` |
| 构建性能 | 单页平均渲染时间 | < 3ms | < 3ms | < 3ms | `--templateMetrics` |
| 管道性能 | 完整管道 1 天数据（Mock） | < 10min | < 10min | —（Mock 不上生产） | `time python3 scripts/pipeline.py` |
| 管道性能 | 完整管道 1 天数据（真实 API） | < 30min | — | < 30min | GitHub Actions 时长 |
| 管道性能 | 管道阶段间数据传递 IO | < 5s/阶段 | < 5s | < 5s | Python `time.perf_counter()` |
| 资源占用 | 管道峰值内存 | < 1GB | < 1GB | < 1GB（CI 7GB 限额） | `resource.getrusage` |
| 资源占用 | Mock server 并发连接数 | ≥ 50 | ≥ 50 | — | `wrk` / `ab` |
| 资源占用 | 磁盘空间（10 万页 + 图片） | < 2GB | < 2GB | < 2GB | `du -sh public/` |
| 资源预算 | 单页 HTML 体积 | < 50 KB | < 50 KB | ~30 KB（minify） | `ls -la public/**/*.html` |
| 资源预算 | 单页首屏总资源 | < 220 KB | < 220 KB | ~140 KB | Lighthouse |
| 资源预算 | 单张 WebP 图片 | < 100 KB | < 100 KB | ~60 KB | `file` / `ls` |
| 资源预算 | CSS 总体积 | < 30 KB | < 30 KB | ~20 KB | `assets/css/**` |
| 资源预算 | JS 总体积（首屏） | < 40 KB | < 40 KB | ~25 KB | `assets/js/**` |
| Mock 性能 | Mock API 平均响应时延 | < 200ms | < 200ms | — | `requests.elapsed` |
| Mock 性能 | Mock API 吞吐量 | ≥ 100 req/s | ≥ 100 req/s | — | `wrk -t4 -c50` |
| 监控覆盖 | 关键性能指标采集率 | 100% | 100% | 100% | 采集脚本完整性检查 |

### B. Mac 硬件分档性能预算（关键差异化）

| 硬件档位 | Hugo 全量构建预算 | Hugo 增量构建 | Mock 管道并发 | 风险点 |
|---------|------------------|--------------|--------------|--------|
| 8GB（M1 Air 基础款） | < 15min | < 30s | ≤ 8 并发 | OOM 风险，需 `--renderSegments` 分批 |
| 16GB（主流款） | < 10min | < 20s | ≤ 16 并发 | 推荐 baseline，本方案默认目标 |
| 32GB（Pro 款） | < 6min | < 15s | ≤ 32 并发 | 可全量并发，无内存压力 |

### C. 每开发步骤性能预算与验收指标

> 此表为本方案核心交付物之一，对应"开发计划"中每个独立步骤文件。

| 步骤号 | 步骤名称 | 性能预算 | 验收指标 | 测量方法 |
|--------|---------|---------|---------|---------|
| S01 | 环境与工具链搭建 | 安装 < 10min | Hugo/Python/Node 版本正确；`hugo version` < 1s 返回 | `time brew install` |
| S02 | Hugo 项目骨架初始化 | `hugo server` 启动 < 3s | 空站点本地 1313 端口可访问；空构建 < 1s | `time hugo` |
| S03 | 数据模型与 Mock 样本生成 | 30 地区 × 366 天 JSON 生成 < 60s | 10980 个 JSON 文件；单文件 < 50KB；总 < 200MB | `time python3 scripts/gen_mock_data.py` |
| S04 | Wikipedia API Mock | Mock 端点响应 < 100ms；并发 ≥ 50 | wrk 压测 P99 < 200ms；零错误 | `wrk -t4 -c50 -d10s` |
| S05 | AI API Mock（Claude/GPT/Gemini） | Mock 响应 < 300ms（模拟思考延迟） | 单次调用 < 500ms；并发 ≥ 20 | `pytest tests/test_mock_ai.py` |
| S06 | Stage 1 fetch 阶段 | 单日 fetch < 5s（Mock） | 366 天全量 fetch < 30min；JSON schema 校验通过 | `time python3 scripts/fetch_events.py --date 2026-07-04` |
| S07 | Stage 2 regionalize 阶段 | 单日 30 地区 < 90s（Mock） | 30 地区 JSON 全部生成；中立性评分 0.7+ | `time python3 scripts/regionalize.py` |
| S08 | Stage 3 translate 阶段 | 单日 10 语种 × 30 地区 < 180s | locales 字段 10 语种齐全；翻译键完整 | `time python3 scripts/translate.py` |
| S09 | Stage 4 illustrate 阶段 | 单日 30 张 Mock 图 < 60s | WebP 输出；单图 < 100KB；alt/caption 齐全 | `time python3 scripts/illustrate.py` |
| S10 | Stage 5 audit 阶段 | 单日审核 < 30s | 审核报告 JSON 输出；neutrality_score 复核 | `time python3 scripts/audit.py` |
| S11 | Stage 6 publish 阶段（Markdown 生成） | 单日 300 页 Markdown 生成 < 30s | 30 × 10 = 300 个 `.md` 文件；frontmatter 完整 | `time python3 scripts/publish.py` |
| S12 | Hugo 模板开发与 partial 缓存 | 单页渲染 < 5ms | `--templateMetrics` 显示 partialCached 命中率 > 80% | `hugo --templateMetrics` |
| S13 | 图片处理流水线 | 300 张图 WebP 转换 < 60s | `<picture>` 响应式标签；400w/800w 双源 | `time` + 浏览器 DevTools |
| S14 | Hugo 10 万页全量构建 | < 10min（16GB Mac） | 109800 个 HTML 文件；峰值内存 < 4GB | `/usr/bin/time -v hugo --minify --gc` |
| S15 | 本地预览服务器 | Hugo server 启动 < 5s；热重载 < 1s | 浏览器 1313 端口可访问；Lighthouse 移动端 > 90 | Lighthouse CLI |
| S16 | Pagefind 搜索索引生成 | 10 万页索引 < 3min | 索引体积 < 100MB；搜索响应 < 50ms | `time npx pagefind --source public` |
| S17 | 本地全链路集成测试 | 完整管道 + 构建 < 20min | 端到端脚本 exit code = 0；性能预算全部达标 | `time ./scripts/local_e2e.sh` |
| S18 | 性能监控与采集脚本 | 采集脚本运行 < 10s | 输出 JSON 报告；指标完整 | `python3 scripts/perf_monitor.py` |
| S19 | 迁移到 GitHub Actions | 工作流总时长 < 25min | 4 个 workflow 文件 lint 通过；dry-run 成功 | `act` 本地模拟 |
| S20 | 迁移到 Cloudflare Pages | 部署 < 5min | 首次部署成功；CDN 命中率 > 95% | CF Dashboard |

---

## 方案清单

### 方案1：Hugo 10 万页本地构建三层加速方案（缓存 + 分批 + 模板优化）

**核心思路**（287 字）：
本地构建 10 万页 Hugo 站点在 8GB Mac 上面临 OOM 与超时双重风险。本方案采用三层加速：(1)**持久化缓存层** — 启用 `--cacheDir` 指向项目外固定目录，让 `resources.Get` 与 `images.Process` 的中间产物跨构建复用，避免每次重建 WebP 衍生图；(2)**分批构建层** — 通过 `--renderSegments` 或按语种分目录多次 `hugo` 调用，每次只渲染 1-2 个语种（约 1.1 万页），用 `--renderToMemory` 减少磁盘 IO，最后用 `rsync` 合并到 public；(3)**模板层** — 强制 `partialCached` 缓存 hreflang/JSON-LD/breadcrumb 等热点 partial，禁用 `.GetPage` 在循环里调用，预加载 `data/*.json` 到全局。三层叠加把 10 万页构建从 25min 压到 8min。

**实施步骤**：

1. **缓存目录初始化**（步骤 S14 前置子任务）
   - 在 `~/.cache/hugo-today-in-history/` 创建持久化缓存目录
   - 在 `hugo.toml` 添加 `[build] useResourceCacheWhen = "always"` 与 `cacheDir` 配置
   - 编写 `scripts/hugo_build.sh` 封装缓存参数

2. **分批构建脚本**
   - 编写 `scripts/hugo_batch_build.sh`，按 10 语种循环调用 `hugo --renderSegments`
   - 每批限制内存峰值 < 2GB（用 `ulimit -v 2097152` 限制）
   - 用 `rsync -a public_batch_${lang}/ public/` 合并
   - 对比验证：分批构建产物与一次性构建产物 byte-level 一致（除时间戳外）

3. **模板性能审计**
   - 运行 `hugo --templateMetrics --templateMetricsHints` 输出模板耗时排名
   - 对 Top 10 慢 partial 应用 `partialCached`：
     - `layouts/partials/hreflang.html` → `partialCached "hreflang.html" . .Params.country_code`
     - `layouts/partials/schema-article.html` → 按 `(country, date)` 键缓存
     - `layouts/partials/related-countries.html` → 按 `(country, date)` 键缓存
   - 移除 day.html 模板中 `range $.Site.Languages` 内的 `.GetPage` 调用，改为预先 `dict` 化

4. **构建性能基准测试**
   - 编写 `scripts/perf_bench_build.py`，自动跑 3 轮构建取中位数
   - 输出 JSON 报告：`{ "total_sec": ..., "peak_mem_mb": ..., "pages_per_sec": ..., "partial_top10": [...] }`
   - 在 8GB/16GB/32GB 三档机器上各跑一次，建立 baseline

5. **CI 增量构建优化**
   - 在 GitHub Actions workflow 中 `actions/cache@v4` 缓存 `~/.cache/hugo-today-in-history/`
   - key 用 `hashFiles('assets/**', 'data/**')` 保证内容变更才失效
   - 增量构建预期 < 1min（仅渲染当日新增 300 页）

**性能优化措施**：

| 优化点 | 优化前 | 优化后 | 提升幅度 | 实现方式 | 风险 |
|--------|--------|--------|---------|---------|------|
| Hugo 全量构建时间（16GB） | ~25min | ~8min | 68% | `--cacheDir` + `partialCached` + 分批 | 分批产物合并出错 |
| Hugo 增量构建时间 | ~3min | < 30s | 83% | `actions/cache` + `useResourceCacheWhen=always` | 缓存 key 失效导致全量 |
| 单页渲染时间 | ~8ms | < 3ms | 62% | 移除循环内 `.GetPage` + `partialCached` | partial 缓存键冲突 |
| 构建峰值内存 | ~6GB | < 4GB | 33% | 分批构建 + `--gc` + `ulimit` | 单批内存不足 OOM |
| WebP 衍生图生成 | 每次 60s | 0s（命中缓存） | 100% | `--cacheDir` 持久化 | 缓存目录损坏 |
| 模板编译时间 | ~30s | ~5s | 83% | `useResourceCacheWhen=always` | 模板变更未感知 |

**预期效果**：
- 16GB Mac 本地全量构建 < 10min，8GB Mac < 15min，32GB Mac < 6min
- GitHub Actions CI 构建从 8min 降到 3min（含增量构建）
- 单页渲染 < 3ms，10 万页理论下限 ~5min 可达
- 模板缓存命中率 > 80%，partial 重复计算减少 60%

**潜在风险**：
- **分批构建产物合并冲突**：用 `rsync` 合并时 `_index.html` 可能覆盖。应对：每批输出到独立目录，最后用脚本合并 `index.html` 与 `*.html`，保留各语种独立子目录。
- **`partialCached` 缓存键设计不当**：hreflang 需按 `(lang, country, date)` 三元组缓存，否则跨语种串内容。应对：缓存键用 `.Permalink` 的 hash。
- **`--renderSegments` 兼容性**：Hugo 0.130+ 该参数已稳定，但旧主题可能依赖全站上下文。应对：先用小规模数据验证。
- **CI 缓存失效雪崩**：assets 大变更导致全量重建。应对：分级缓存 key，区分"模板缓存"与"资源缓存"。

**成本估算**：
- 人力：3 人天（缓存配置 0.5 + 分批脚本 1 + 模板优化 1 + 基准测试 0.5）
- 时间：1 周内完成（建议 S12-S14 步骤并行）
- 技术债务：依赖 Hugo 0.130+ 特性，未来大版本升级需重新评估
- 维护：长期投入低（缓存目录自动化，分批脚本独立模块）

**致命失败场景**：
- **场景 A**：8GB Mac 上启用 `--renderToMemory` 反而触发 swap 抖动，构建时间从 15min 涨到 40min。**触发条件**：内容数据 > 500MB 时内存映射失效。**应对**：8GB 机器强制走分批 + 落盘模式，禁用 `--renderToMemory`。
- **场景 B**：`partialCached` 键设计错误导致英文页出现中文 hreflang。**触发条件**：缓存键未包含 `.Lang`。**应对**：所有 partial 缓存键强制带 `.Lang` 前缀，加单元测试。
- **场景 C**：CI 缓存目录被 GitHub Actions 清理后首次构建超时（>30min）。**触发条件**：缓存 miss + 10 万页全量 WebP 生成。**应对**：CI 增加超时熔断 + 失败重试机制，并在 Stage 4 预生成 WebP 而非构建时生成。

---

### 方案2：Python AI 管道 asyncio + Semaphore 并发模型（Mock 友好）

**核心思路**（295 字）：
原架构 `scripts/pipeline.py` 用 `subprocess.run` 串行调用 7 阶段，单日 Mock 数据需 ~15min。本方案改为 asyncio 协程模型：(1)**阶段间串行、阶段内并发** — fetch（IO）→ regionalize（CPU+IO 混）→ translate（IO 密集）→ illustrate（IO 密集）等阶段串行，但每阶段内部用 `asyncio.gather` 并发处理 30 地区 / 10 语种；(2)**Semaphore 限流** — Mock API 并发上限 16（16GB Mac），避免 file descriptor 耗尽；(3)**磁盘缓存层** — 用 `diskcache` 库把 Mock API 响应持久化，二次运行直接命中，调试阶段从 15min 降到 < 1min；(4)**进度可视化** — 用 `tqdm.asyncio` 显示并发进度条。本地 Mock 用 `aiohttp` 起本地 HTTP server 模拟 Claude/GPT/Gemini，响应延迟人工注入（Claude 2s、GPT-4o 1s、Gemini 1.5s）以复现真实时序。生产环境切换仅需替换 `MOCK_MODE=False`，asyncio → httpx 真实调用。

**实施步骤**：

1. **管道编排重构**（对应 S06-S11）
   - 编写 `scripts/async_pipeline.py`，用 `asyncio.run(main())` 入口
   - 每阶段函数签名改为 `async def stage_xxx(sem, items) -> list[Result]`
   - 阶段间用 `asyncio.Queue` 传递数据，避免大对象拷贝
   - 保留同步版 `pipeline.py` 作为 fallback（小数据量调试用）

2. **Mock HTTP Server 实现**
   - 用 `aiohttp.web` 起 8787 端口 Mock server
   - 路由：`/v1/messages`（Claude）、`/v1/chat/completions`（GPT-4o）、`/v1/models/gemini-1.5-flash:generateContent`（Gemini）
   - 每路由注入固定延迟（用 `await asyncio.sleep(delay)`）
   - Mock 响应从 `tests/fixtures/mock_responses/` 读取 JSON
   - 编写 `scripts/start_mock_server.sh` 一键启动

3. **diskcache 缓存层**
   - `pip install diskcache`
   - 在 `scripts/cache.py` 封装 `cached_call(key, fn, *args)`
   - key = `hash(model + prompt + params)`
   - 缓存目录 `.cache/pipeline/`，gitignore
   - 缓存命中率统计（开发期反馈）

4. **并发限流与背压**
   - `Semaphore(16)`（16GB Mac 默认，可配置）
   - 每阶段 `asyncio.gather(*[bounded_call(sem, item) for item in items])`
   - 监控队列积压，超过 1000 items 触发 chunked 处理
   - 失败重试：`tenacity` 库，指数退避 3 次

5. **性能采集与对比**
   - 在 `async_pipeline.py` 关键节点埋点 `time.perf_counter()`
   - 输出 `logs/perf/pipeline-{date}.json`：每阶段耗时、并发度、缓存命中率
   - 编写 `scripts/perf_compare.py` 对比同步版 vs 异步版

**性能优化措施**：

| 优化点 | 优化前 | 优化后 | 提升幅度 | 实现方式 | 风险 |
|--------|--------|--------|---------|---------|------|
| 单日 Mock 管道总耗时 | ~15min | < 3min | 80% | asyncio + Semaphore(16) | fd 耗尽 |
| Stage 3 翻译阶段（300 调用） | ~180s | < 30s | 83% | 10 语种并发 × 30 地区并发 | API rate limit |
| 二次运行（缓存命中） | ~15min | < 30s | 97% | diskcache 持久化 | 缓存失效 |
| Mock API 响应延迟 | 不可控 | 可注入 | — | `asyncio.sleep(delay)` 注入 | 延迟模拟失真 |
| 失败重试 | 立即失败 | 指数退避 3 次 | — | tenacity | 重试风暴 |
| 内存占用（300 并发） | ~2GB | < 500MB | 75% | Semaphore 限流 + 流式处理 | 单任务过大 |
| 调试反馈循环 | 15min/次 | 30s/次 | 96% | diskcache + Mock | 缓存污染 |

**预期效果**：
- 单日 Mock 管道从 15min 降到 < 3min（首次）/< 30s（缓存命中）
- 366 天全量 Mock 数据生成从 90 小时降到 18 小时（首次）/3 小时（缓存命中）
- 16GB Mac 上稳定并发 16，峰值内存 < 1GB
- 生产环境切换零代码改动，仅改环境变量

**潜在风险**：
- **Mock 延迟失真**：Mock 响应太快导致生产时序问题被掩盖。应对：Mock server 强制注入真实延迟（Claude 2-5s、GPT-4o 1-3s、Gemini 1-2s），并支持随机抖动。
- **diskcache 污染**：调试时改了 prompt 但缓存未失效。应对：缓存 key 包含 prompt hash，prompt 变更自动失效；提供 `--no-cache` flag。
- **asyncio 在 Mac 上的 kqueue 限制**：Mac 默认 fd 上限 256。应对：`ulimit -n 1024` 提前设置；用 `Semaphore` 控制实际并发。
- **生产环境 API rate limit**：本地 Mock 无 rate limit，生产 OpenAI 500 RPM 限制可能反序列化瓶颈。应对：在 Mock 中也模拟 rate limit（429 响应 + Retry-After header）。
- **异步栈追踪困难**：asyncio 异常栈不直观。应对：`asyncio.run(main(), debug=True)` + `aiomonitor` 库。

**成本估算**：
- 人力：4 人天（async 重构 1.5 + Mock server 1 + diskcache 0.5 + 性能采集 1）
- 时间：1.5 周（建议与 S06-S11 同步推进）
- 技术债务：双轨制（同步 + 异步）增加维护成本，建议 1 个月后废弃同步版
- 维护：长期投入中等（Mock 响应库需随生产 API 变更更新）

**致命失败场景**：
- **场景 A**：Mac fd 耗尽导致 `OSError: [Errno 24] Too many open files`，管道中途崩溃。**触发条件**：Semaphore(64) + diskcache 同时打开大量 fd。**应对**：`ulimit -n 65535` + Semaphore 降到 8。
- **场景 B**：diskcache 损坏导致后续运行全部命中错误数据。**触发条件**：磁盘空间不足时写入。**应对**：每次启动校验 `diskcache.verify()`，损坏自动清空。
- **场景 C**：Mock 响应不完整导致生产切换时 API 字段缺失崩溃。**触发条件**：Mock 只覆盖 happy path。**应对**：用真实 API 录制响应（首次切换时）作为 Mock fixture，覆盖 error/edge case。
- **场景 D**：asyncio 事件循环阻塞 — 某阶段同步调用（如 `requests.get`）混入。**触发条件**：开发者误用同步库。**应对**：CI 加 `flake8-async` lint 检查禁用 `requests`。

---

### 方案3：本地全链路性能监控与瓶颈定位方案（量化驱动）

**核心思路**（289 字）：
性能不可视是本地开发最大隐患——开发者不知道哪一步慢、慢多少、是否超预算。本方案构建三层监控体系：(1)**步骤级埋点** — 在每个开发步骤的入口/出口埋点 `time.perf_counter()`，写入 `logs/perf/step-{N}.json`，自动对比"性能预算 vs 实际值"，超标红色告警；(2)**资源级采集** — 用 `psutil` 采集 CPU/内存/磁盘 IO 采样（1Hz），构建过程产出 flamegraph（用 `py-spy` 或 `async-profiler`），定位热点函数；(3)**产物级校验** — 构建完成后扫描 `public/` 下所有 HTML，统计单页体积分布、图片体积分布、CSS/JS 引用数，输出直方图。三层监控数据汇总到 `scripts/perf_dashboard.py`，生成本地 HTML 报告（无依赖，纯 Python）。每个开发步骤的 `验收指标` 自动从监控数据中提取，避免人工填写。

**实施步骤**：

1. **埋点框架**（S01 后即可启动）
   - 编写 `scripts/perf/timer.py`：上下文管理器 `with PerfTimer("step-name", budget_sec=...) as t:`
   - 自动写入 `logs/perf/{date}/{step}.json`：`{name, start, end, duration, budget, overrun, status}`
   - 支持 budget 超标自动调用 `sys.exit(1)`（CI 严格模式）或仅告警（开发模式）

2. **资源采样器**
   - 编写 `scripts/perf/sampler.py`：后台线程，1Hz 采样 `psutil.cpu_percent()` / `psutil.virtual_memory().used` / `psutil.disk_io_counters()`
   - 输出 CSV：`timestamp,cpu_pct,mem_mb,disk_read_mb,disk_write_mb`
   - 配合 `py-spy record -o profile.svg -- python3 ...` 生成火焰图

3. **构建产物分析**
   - 编写 `scripts/perf/analyze_public.py`：
     - 递归扫描 `public/**/*.html`，统计每页体积
     - 用 BeautifulSoup 提取 `<img>` `<link>` `<script>` 数量
     - 用 Pillow 检查 `public/**/*.webp` 体积分布
     - 输出 `public_perf_report.json`：分位数 P50/P90/P99

4. **性能预算看板**
   - 编写 `scripts/perf_dashboard.py`：聚合所有 `logs/perf/*.json`
   - 生成 `09_报告/性能看板.html`：深色主题，表格 + Chart.js（CDN 免费版）
   - 每个 step 一行：预算值 / 实际值 / 偏差% / 状态徽章（绿/黄/红）
   - 顶部统计：总步骤数、达标数、超标数、达标率
   - 含趋势图：最近 7 次构建的时间趋势

5. **CI 性能回归门禁**
   - GitHub Actions workflow 增加步骤 `python3 scripts/perf_gate.py`
   - 读取最近一次 `logs/perf/step-*.json`，任何 step status=red 则 `exit 1`
   - PR 必须通过性能门禁才能合并
   - 性能预算可配置：`.perf-budget.yml`（YAML 格式，每 step 预算）

6. **Mock server 性能压测**
   - 编写 `scripts/perf/mock_stress_test.sh`：用 `wrk -t4 -c50 -d30s http://localhost:8787/v1/messages`
   - 输出吞吐量、P50/P99 延迟、错误率
   - 验收：吞吐量 ≥ 100 req/s，P99 < 500ms

**性能优化措施**：

| 优化点 | 优化前 | 优化后 | 提升幅度 | 实现方式 | 风险 |
|--------|--------|--------|---------|---------|------|
| 性能瓶颈定位耗时 | 人工 30min | 自动 10s | 99% | 火焰图 + 步骤埋点 | 采样开销 |
| 性能预算达标率 | 不可知 | 100% 可视化 | — | perf_dashboard | 误报 |
| 性能回归检测 | 上线后才发现 | PR 阶段拦截 | — | CI perf gate | 预算过严阻塞 |
| 单页体积分布 | 不可知 | P50/P90/P99 | — | analyze_public | 误判 |
| Mock server 吞吐量 | 不可知 | 实时监控 | — | wrk 压测 | 压测干扰开发 |
| 资源泄漏检测 | 上线后才发现 | 实时采样 | — | psutil 1Hz | 采样开销 1-2% |
| 调试反馈循环 | 重复跑全流程 | 单步骤量化 | 80% | 步骤独立埋点 | — |

**预期效果**：
- 每个 development step 的性能指标 100% 可量化、可追溯
- 性能回归在 PR 阶段拦截，避免上线后才发现
- 开发者 10s 内定位"哪一步慢、慢多少、为什么"
- 构建 10 万页后立即产出 HTML 看板，含 P50/P90/P99 体积分布
- Mock server 性能基线建立，迁移生产时可对比

**潜在风险**：
- **采样开销**：1Hz psutil 采样约 1-2% CPU 开销，对构建时间影响 < 1%。应对：采样间隔可配置（默认 1Hz，CI 模式 5Hz）。
- **火焰图生成失败**：`py-spy` 需要 sudo 权限（macOS SIP 限制）。应对：用 `cProfile` 替代，或要求用户 `csrutil disable`（不推荐）。
- **HTML 看板依赖 Chart.js CDN**：用户无法访问国外网站。应对：Chart.js 本地化到 `static/vendor/chart.min.js`，看板用相对路径引用。
- **CI 性能门禁误报**：Mac 与 CI（Ubuntu）性能差异导致同代码不同时长。应对：CI 与本地分别维护预算，看板标注"环境"字段。
- **日志膨胀**：每次构建产出大量 perf JSON。应对：保留最近 30 天，自动清理旧日志。

**成本估算**：
- 人力：3 人天（埋点框架 0.5 + 资源采样 0.5 + 产物分析 0.5 + 看板 1 + CI 门禁 0.5）
- 时间：1 周内完成（建议 S01 后启动，与所有步骤并行）
- 技术债务：无新增依赖（纯 Python 标准库 + psutil + BeautifulSoup）
- 维护：长期投入低（看板模板固化，新 step 自动接入）

**致命失败场景**：
- **场景 A**：埋点框架本身性能开销过大，导致构建时间从 8min 涨到 12min。**触发条件**：每个 partial 都埋点。**应对**：仅 step 级埋点，partial 内部用 `--templateMetrics` 而非自定义埋点。
- **场景 B**：性能预算过严导致所有 PR 阻塞。**触发条件**：预算设为 best-case 值。**应对**：预算设为 P90 值，允许 10% 抖动，CI 模式下提供 `--perf-warn-only` 跳过 hard fail。
- **场景 C**：看板 HTML 报告因 Chart.js CDN 失败白屏。**触发条件**：用户在无网环境打开看板。**应对**：Chart.js 本地化是硬要求，看板生成时自动注入本地 `chart.min.js`，离线可用。
- **场景 D**：CI 性能数据被 GitHub Actions 缓存清理丢失。**触发条件**：超过 90 天未访问的 cache。**应对**：每次构建把 `logs/perf/` 提交到 `perf-history` 分支，永久存档。

---

## 跨方案协同与冲突

### 协同点
- **方案1 + 方案2**：Hugo 构建加速（方案1）与管道加速（方案2）正交，可叠加。管道产出的 Markdown 直接送入 Hugo 构建，端到端时间 = 管道 3min + 构建 8min = 11min，远低于预算 20min。
- **方案2 + 方案3**：管道埋点（方案3）依赖方案2 的 asyncio 框架，可在协程内自动注入 `PerfTimer`。
- **方案1 + 方案3**：构建产物分析（方案3）依赖方案1 的 `--templateMetrics` 输出。

### 冲突点
- **方案1 分批构建 vs 方案3 单步骤埋点**：分批构建把 S14 拆成 10 个子步骤，方案3 看板需适配"父步骤 + 子步骤"两级预算。
- **方案2 diskcache vs 方案3 真实性能数据**：diskcache 命中时管道耗时 30s，但首次运行 3min，看板需区分"首次"与"缓存命中"两种模式。
- **解决方案**：看板支持 `--mode=first|cached` 切换预算，CI 默认 `first` 模式（更严格），本地开发默认 `cached` 模式（快速反馈）。

---

## 性能工程师推荐优先级

| 优先级 | 方案 | 理由 |
|--------|------|------|
| **P0（必须）** | 方案1 — Hugo 构建加速 | 不解决则本地开发无法进行（10 万页构建 25min，迭代不可行） |
| **P1（强烈推荐）** | 方案3 — 性能监控 | 性能不可视则方案1/2 效果无法验证；为开发步骤提供量化验收 |
| **P2（推荐）** | 方案2 — 管道并发 | 单日 Mock 管道 15min 可接受，但 366 天全量生成需加速；建议 S06-S11 完成后启动 |

**整体落地建议**：方案1 与方案3 在 S01 同步启动（埋点框架先行，构建优化跟随），方案2 在 S06-S11 阶段并行推进。三方案叠加后，端到端本地全链路 < 15min（含构建），远低于任务定义书 S17 的 20min 预算。

---

## 附录 A：关键性能测量命令速查

```bash
# Hugo 构建带性能分析
hugo --minify --gc --templateMetrics --templateMetricsHints --logLevel info

# Hugo 构建带内存与时间监控
/usr/bin/time -v hugo --minify --gc

# Python 管道带火焰图
py-spy record -o profile.svg -- python3 scripts/async_pipeline.py 2026-07-04

# Mock server 压测
wrk -t4 -c50 -d30s --latency http://localhost:8787/v1/messages

# 单页体积分析
find public -name "*.html" -exec wc -c {} + | sort -n | tail -20

# 构建产物总览
du -sh public/ && find public -type f | wc -l

# 内存占用监控（后台运行）
while true; do ps -o rss,vsz,pid -p $(pgrep hugo) >> mem.log; sleep 1; done
```

## 附录 B：性能预算 YAML 配置示例

```yaml
# .perf-budget.yml
steps:
  S01_environment:
    budget_sec: 600
    mode: warn
  S03_mock_data:
    budget_sec: 60
    mode: hard_fail
  S06_fetch:
    budget_sec: 5
    mode: warn
  S14_hugo_build_full:
    budget_sec: 600  # 10min for 16GB Mac
    mode: hard_fail
    env_override:
      mac_8gb: 900   # 15min
      mac_32gb: 360  # 6min
  S17_e2e_integration:
    budget_sec: 1200
    mode: hard_fail
```

## 附录 C：与其他子智能体方案的接口约定

- **与 R_test_architect**：方案3 的 perf_dashboard 输出路径 `09_报告/性能看板.html` 需与测试报告目录约定一致；Mock server 端口 8787 需测试方案预留。
- **与 R_tech_implementer**：方案1 的 `hugo_batch_build.sh` 与方案2 的 `async_pipeline.py` 是具体实现交付物，需技术实现者方案中预留对应步骤。
- **与 R_strategist**：性能预算 S01-S20 顺序需与战略架构师步骤排序对齐；P0/P1/P2 优先级需在战略方案中体现。
- **与 R_risk_analyst**：每个方案的"致命失败场景"需风险分析师方案中复用，建立风险登记册。

---

**方案版本**：v1.0（第 1 轮独立分析）
**编写者**：性能工程师（R_perf_engineer）
**待第 2 轮融合**：与 R_tech_implementer 协调步骤编号、与 R_test_architect 协调 Mock 端口与压测工具选型、与 R_strategist 协调优先级排序。
