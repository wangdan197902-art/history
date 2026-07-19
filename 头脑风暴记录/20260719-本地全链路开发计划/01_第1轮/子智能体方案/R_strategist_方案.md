# 战略架构师方案 — 第 1 轮

## 角色定位

战略架构师，聚焦**全局规划与长期演进路径**。本方案从以下战略维度切入：

- 开发阶段划分（Phase 0~Phase 4 的精确定义，每阶段入站/出站条件）
- 阶段间依赖关系（串行/并行的精确判定）
- 关键里程碑（每个里程碑的可验证产出物）
- 本地 → 生产迁移路径（Mock 替换、配置切换、域名切换的精确步骤）
- 技术债务管理（本地版妥协了什么、何时偿还、如何偿还）
- 长期演进路径（10→30 地区、3→10 语种的扩展路径）
- 风险对齐（与现有 07_风险管理与合规方案.md 的对齐）
- 资源投入规划（每阶段人力/时间/成本预估）

## 战略层面的核心洞察

阅读三份前置文档后，战略层面识别出 5 个关键张力点：

| 张力点 | 现有文档假设 | 现实约束 | 战略影响 |
|--------|------------|---------|---------|
| **网络可达性** | 路线图假设可直连 GitHub/Cloudflare/AI API/Wikipedia | 用户无法访问国外网站 | 整个生产路径在开发阶段不可达，必须本地 Mock |
| **AI API 调用** | Claude/GPT-4o/Gemini 直接调用 | 同上，且无法注册海外账号 | AI 管道核心环节无法验证，需本地 LLM 或预录响应 |
| **10 万页面规模** | Hugo 构建 < 10 分钟 | 本地机器性能受限，且 10 万页面首次构建可能 OOM | 必须验证本地构建可行性，否则需切片策略 |
| **CI/CD 调度** | GitHub Actions cron 触发 | 本地无法模拟 GitHub Actions | 需用 `act` 或自建 cron + 日志系统模拟 |
| **域名/DNS/CDN** | Cloudflare Pages 边缘缓存 | 本地无 CDN 环境 | 性能验证只能延迟到生产环境 |

这 5 个张力点决定了**任何方案都必须显式回答"本地版妥协了什么、何时偿还"**。

---

## 方案清单

### 方案1：分层渐进式 Mock→生产切换方案（推荐 — 战略稳健派）

**核心思路**：

将开发严格划分为 Phase 0~4 五个阶段，每阶段有明确入站/出站条件。本地用 Flask Mock Server 模拟全部外部依赖（Wikipedia API、AI API、Cloudflare Pages API、Buttondown API、GSC API），Mock 响应数据预先通过合规渠道采集并版本化到 `tests/fixtures/`。Hugo 构建在本地完整跑通 10 万页面规模，CI/CD 用 `act` 本地模拟。生产迁移是"Provider 接口实现切换"而非"代码重写"，技术债务通过 `tech-debt-ledger.md` 显式登记。该方案强调**阶段可验证性**和**迁移零事故**。

**实施步骤**：

#### 步骤 1.1：Phase 0 — 环境与契约基础（Week 0，5 人天）

**前置条件**：项目目录已建立；用户本地具备 macOS + 网络访问国内镜像源能力。

**任务清单**：
1. 安装 Hugo Extended 0.130+（通过 Homebrew 国内镜像）
2. 安装 Python 3.11+ / Node.js 20+ / Git 2.40+
3. 创建 `tech-debt-ledger.md`（技术债务登记表）
4. 创建 `tests/contracts/` 目录，编写 6 份 API 契约文件：
   - `wikipedia-onthisday.openapi.yaml`
   - `anthropic-messages.openapi.yaml`
   - `openai-chat.openapi.yaml`
   - `gemini-generate.openapi.yaml`
   - `cloudflare-pages-deploy.openapi.yaml`
   - `buttondown-subscribe.openapi.yaml`
5. 安装 `act`（GitHub Actions 本地模拟器）
6. 配置 Python 虚拟环境，安装 `requirements.txt` 中的依赖（使用国内 pip 镜像）

**验收标准**：
- [ ] `hugo version` 输出 ≥ 0.130
- [ ] `python3 --version` 输出 ≥ 3.11
- [ ] `act --version` 可执行
- [ ] 6 份 OpenAPI 契约文件通过 `redocly lint` 校验
- [ ] `tech-debt-ledger.md` 包含表头模板

**产出物**：本地开发环境 + 6 份 API 契约 + 技术债务登记表

---

#### 步骤 1.2：Phase 1 — Mock 体系建设（Week 1，8 人天）

**前置条件**：Phase 0 验收通过；6 份 API 契约已定稿。

**任务清单**：
1. 搭建 Flask Mock Server（端口 8765），按 6 份契约实现响应端点
2. 采集 Mock 响应数据样本：
   - Wikipedia OnThisDay：采集 5 个日期 × 9 语种的真实响应（合规渠道）
   - AI 响应：人工编写 3 个地区 × 3 个日期的高质量响应样本
   - Cloudflare Pages 部署响应：模拟成功/失败两种
   - Buttondown 订阅响应：模拟成功/已存在/失败三种
3. 实现 Mock 数据版本化（`tests/fixtures/{service}/{scenario}.json`）
4. 实现 `scripts/config_provider.py` — 环境变量驱动的 Provider 切换器：
   - `ENV=local` → 走 Mock Server
   - `ENV=staging` → 走测试环境
   - `ENV=production` → 走真实 API
5. 编写 Mock Server 的自检脚本 `tests/test_mock_server.py`
6. 文档化 Mock 数据采集来源与采集日期（合规审计用）

**验收标准**：
- [ ] `curl http://localhost:8765/api/wikipedia/onthisday/07/04` 返回符合契约的 JSON
- [ ] `curl http://localhost:8765/api/anthropic/messages` 返回符合契约的 JSON
- [ ] `ENV=local python3 scripts/test_provider.py` 全部通过
- [ ] `ENV=production python3 scripts/test_provider.py` 因网络不可达而失败（验证切换生效）
- [ ] Mock 数据采集来源 100% 可追溯

**产出物**：Mock Server + Provider 切换器 + 版本化 Mock 数据

**技术债务登记**：
- TD-001：Mock 数据仅覆盖 5 个日期，生产需扩展到 366 天
- TD-002：AI 响应样本人工编写，质量与真实 AI 输出有差距
- TD-003：Mock Server 单机部署，无并发限流模拟

---

#### 步骤 1.3：Phase 2 — 内容生产管道实现（Week 2-3，12 人天）

**前置条件**：Phase 1 Mock Server 稳定运行；Provider 切换器通过测试。

**任务清单**：
1. 实现 `scripts/fetch_events.py`（Wikipedia 采集 + 多语种去重）
2. 实现 `scripts/regionalize.py`（Claude 地区化重写）
3. 实现 `scripts/translate.py`（GPT-4o 翻译）
4. 实现 `scripts/illustrate.py`（Gemini/Wikimedia 配图）
5. 实现 `scripts/audit.py`（AI 中立性审核）
6. 实现 `scripts/publish.py`（Markdown 生成 + git commit）
7. 实现 `scripts/pipeline.py`（编排器，串联上述 6 步）
8. 每个脚本必须支持 `--dry-run` 和 `--mock` 两种模式
9. 单元测试覆盖率 ≥ 70%（核心逻辑）
10. 端到端测试：`ENV=local python3 scripts/pipeline.py 2026-07-04` 完整跑通

**验收标准**：
- [ ] 7 个脚本均可独立运行并通过单元测试
- [ ] `pipeline.py 2026-07-04 --mock` 在 5 分钟内完成（本地 Mock 数据）
- [ ] 输出的 `data/events/07-04.json` 符合 `01_技术架构体系.md §4.1` 的 JSON Schema
- [ ] 输出的 30 地区 × 1 语种 = 30 个 Markdown 文件结构正确
- [ ] 中立性评分字段完整填充
- [ ] 错误处理：Mock 故障时管道优雅降级而非崩溃

**产出物**：完整 AI 内容生产管道 + 单元测试 + 端到端测试

**技术债务登记**：
- TD-004：本地用 Mock AI 响应，无法验证真实 AI 输出质量
- TD-005：30 地区过滤逻辑本地验证仅覆盖 5 个代表性地区

---

#### 步骤 1.4：Phase 3 — Hugo 集成与 10 万页面构建验证（Week 4，7 人天）

**前置条件**：Phase 2 管道可产出 30 地区 × 1 语种内容；Hugo 项目骨架已搭建。

**任务清单**：
1. 完成 Hugo 配置（hugo.toml + languages.toml + params.toml + menus.toml）
2. 开发 layouts 模板（day.html / list.html / partials/）
3. 开发样式（响应式 + 30 地区导航 + 日历组件）
4. 编写 `scripts/generate_blank_pages.py` — 生成 366 × 30 = 10,980 个空白 _index.md
5. 编写 `scripts/batch_backfill.py` — 用 Mock 数据批量回填内容
6. **10 万页面构建压力测试**：
   - Step 1：1 语种 × 30 地区 × 366 天 = 10,980 页面，目标 < 2 分钟
   - Step 2：3 语种 × 30 地区 × 366 天 = 32,940 页面，目标 < 5 分钟
   - Step 3：10 语种 × 30 地区 × 366 天 = 109,800 页面，目标 < 10 分钟
7. 配置 Pagefind 搜索索引生成
8. 配置 sitemap.xml / robots.txt / llms.txt / _headers / _redirects
9. Lighthouse 本地测试（首页 + 日期页 + 列表页）> 90 分

**验收标准**：
- [ ] 10,980 空白页 Hugo 构建成功，时长 < 2 分钟
- [ ] 109,800 页面（Mock 内容）Hugo 构建成功，时长 < 10 分钟，内存峰值 < 8GB
- [ ] 30 地区首页 + 366 日期页全部可访问
- [ ] 多语言切换正常（10 语种 hreflang 互链）
- [ ] sitemap.xml 包含全部 109,800 URL
- [ ] Pagefind 索引生成成功，搜索可用
- [ ] Lighthouse 性能 > 90，SEO > 95

**产出物**：完整 Hugo 站点 + 10 万页面本地构建能力 + 搜索/SEO 配置

**技术债务登记**：
- TD-006：本地 10 万页面内容为 Mock，真实内容质量待生产验证
- TD-007：本地无 CDN，性能数据与生产有差距
- TD-008：Pagefind 索引在 10 万页面规模下首次构建时长待优化

---

#### 步骤 1.5：Phase 4 — 生产迁移（Week 5，6 人天）

**前置条件**：Phase 3 本地全链路通过；用户已获得访问国外网站的临时通道（VPN/代理）或委托有访问能力的运维人员。

**任务清单**：
1. **配置切换演练**（本地执行）：
   - 创建 `.env.production` 文件，填入真实 API Key
   - 运行 `ENV=production python3 scripts/pipeline.py 2026-07-04 --dry-run` 验证连通
   - 修复任何因 Mock/真实 API 差异导致的失败
2. **域名与 DNS 配置**（Namecheap + Cloudflare）：
   - 注册域名，转入 Cloudflare DNS
   - 配置 SSL/TLS 完全严格模式 + HSTS
   - 配置 Email Routing
3. **GitHub 仓库与 Secrets 配置**：
   - 创建 GitHub 仓库，配置分支保护
   - 配置 11 个 GitHub Secrets（API Key / Token）
4. **Cloudflare Pages 项目创建**：
   - 连接 GitHub 仓库，配置构建命令
   - 配置自定义域名
   - 配置 _headers / _redirects / Cache Rules
5. **首次生产部署**：
   - 推送代码到 main 分支，触发 deploy.yml
   - 验证部署成功，HTTPS 可访问
   - 提交 sitemap 到 GSC/Bing/Yandex/Baidu
6. **生产环境验收**：
   - 首页 Lighthouse > 90
   - 30 地区首页可访问
   - 单日内容（2026-07-04）完整呈现
   - GitHub Actions daily-history.yml 手动触发成功
7. **技术债务偿还计划启动**：
   - TD-001~008 逐项评估，制定偿还时间表
   - 优先偿还 TD-004（真实 AI 输出质量验证）

**验收标准**：
- [ ] 生产域名 HTTPS 可访问
- [ ] 30 地区首页全部 200 OK
- [ ] daily-history.yml 在 GitHub Actions 上成功执行
- [ ] sitemap.xml 被 GSC 抓取
- [ ] 生产环境首页 LCP < 1.5s
- [ ] 技术债务登记表中至少 TD-001~004 有明确的偿还时间表

**产出物**：生产环境上线 + 技术债务偿还计划

---

**阶段划分与依赖图**：

```
Phase 0 (环境与契约) ────────┬─→ Phase 1 (Mock 体系) ─→ Phase 2 (管道实现) ─→ Phase 3 (Hugo 集成) ─→ Phase 4 (生产迁移)
                              │                              ↑                    ↑                       ↑
                              │                              │                    │                       │
Phase 0.5 (测试数据准备) ─────┘──────────────────────────────┘                    │                       │
                                                                                   │                       │
Phase 1.5 (Hugo 骨架并行) ────────────────────────────────────────────────────────┘                       │
                                                                                                           │
Phase 3.5 (CI/CD 本地模拟) ────────────────────────────────────────────────────────────────────────────────┘
```

**串行/并行判定**：
- **必须串行**：Phase 0 → Phase 1（Mock 依赖契约）；Phase 2 → Phase 3（Hugo 依赖管道产出）；Phase 3 → Phase 4（生产依赖本地验证）
- **可并行**：Phase 0.5（测试数据准备）与 Phase 1 并行；Phase 1.5（Hugo 骨架）与 Phase 2 并行；Phase 3.5（CI/CD 本地模拟）与 Phase 3 并行

---

**关键里程碑**：

| 里程碑 | 完成阶段 | 可验证产出物 | 验收标准 |
|--------|---------|-------------|---------|
| M1: 本地环境就绪 | Phase 0 | Hugo/Python/Node/act 环境 + 6 份 API 契约 | `hugo version` / `act --version` 可执行；契约通过 redocly lint |
| M2: Mock 体系运行 | Phase 1 | Flask Mock Server + Provider 切换器 | 6 个 Mock 端点全部通过契约测试；ENV 切换生效 |
| M3: 单日管道跑通 | Phase 2 | pipeline.py + 7 个子脚本 | `pipeline.py 2026-07-04 --mock` 5 分钟内完成；JSON Schema 校验通过 |
| M4: 10 万页面构建成功 | Phase 3 | Hugo 站点 + 109,800 页面 | 10 万页面构建 < 10 分钟；Lighthouse > 90 |
| M5: 生产域名上线 | Phase 4 | Cloudflare Pages 部署 | HTTPS 可访问；30 地区首页 200 OK |
| M6: 生产管道自动化 | Phase 4 | GitHub Actions daily-history.yml | 手动触发成功；sitemaps 被 GSC 抓取 |
| M7: 技术债务偿还启动 | Phase 4 后 | tech-debt-ledger.md 更新 | TD-001~008 均有偿还时间表 |

---

**本地 → 生产迁移路径**：

| 迁移项 | 本地版 | 生产版 | 切换方式 | 回滚方案 |
|--------|--------|--------|---------|---------|
| Wikipedia API | Flask Mock（5 日期 × 9 语种样本） | 真实 OnThisDay API | `ENV=production` 环境变量切换 | 回退 `ENV=local` |
| Anthropic Claude API | Flask Mock（人工编写响应） | 真实 Claude 3.5 API | 同上 | 同上 |
| OpenAI GPT-4o API | Flask Mock | 真实 GPT-4o API | 同上 | 同上 |
| Google Gemini API | Flask Mock | 真实 Gemini 1.5 API | 同上 | 同上 |
| Wikimedia Commons | Flask Mock（预录图片 URL） | 真实 Commons API | 同上 | 同上 |
| Cloudflare Pages 部署 | 本地 `hugo server` | Cloudflare Pages | git push 触发 Actions | `git revert` + 重新部署 |
| GitHub Actions CI/CD | `act` 本地模拟 | GitHub Actions 真实运行 | 推送 `.github/workflows/*.yml` | 保留 act 配置作为本地验证 |
| Buttondown 邮件 | Flask Mock | 真实 Buttondown API | `ENV=production` | 同上 |
| GSC sitemap 提交 | 跳过（本地无 SEO） | 真实 GSC API | 配置 `GSC_SERVICE_ACCOUNT` Secret | 跳过该步骤 |
| 域名/DNS/CDN | `localhost:1313` | today-in-history.example.com | Cloudflare DNS 配置 | 保留本地访问能力 |
| 监控告警 | 控制台日志 | Slack/Discord Webhook | 配置 `ALERT_WEBHOOK` Secret | 日志降级到文件 |

**迁移执行顺序（关键）**：
1. 先切换 AI API Provider（最易回滚）
2. 再切换 Wikipedia API Provider
3. 验证内容质量后，推送代码触发 GitHub Actions
4. 验证 Cloudflare Pages 部署成功
5. 最后切换 SEO/邮件订阅/监控告警
6. 全程保留 `ENV=local` 回滚能力

---

**长期演进路径**：

- **短期（Month 1-3）**：本地全链路稳定运行，10 万页面生产部署完成，启动 AdSense 申请准备
- **中期（Month 4-12）**：偿还技术债务 TD-001~008；扩展到 10 语种全覆盖；启动 API 上线（Cloudflare Workers）
- **长期（Year 2+）**：从 30 地区扩展到 100+ 地区；从 10 语种扩展到 20+ 语种；启动多站点矩阵化

**地区/语种扩展路径（战略规划）**：
| 扩展批次 | 地区数 | 语种数 | 页面数 | 触发条件 | 技术准备 |
|---------|--------|--------|--------|---------|---------|
| 基线（Phase 4 完成） | 30 | 1（en） | 10,980 | 本地全链路通过 | 已就绪 |
| 第 1 扩展 | 30 | 5（+zh/es/fr/de/pt） | 54,900 | 月 UV > 5k | 翻译 Prompt 优化 + 母语者抽检 |
| 第 2 扩展 | 30 | 10（+it/ru/ja/ko/） | 109,800 | 月 UV > 10k | 10 万页面构建稳定性验证 |
| 第 3 扩展 | 60 | 10 | 219,600 | 月 UV > 50k | 子站点矩阵化 |
| 第 4 扩展 | 100+ | 20+ | 500,000+ | Year 2-3 | 多仓库架构 + API 服务化 |

---

**预期效果**：
- 本地全链路可在 5 周内稳定跑通，10 万页面构建能力验证通过
- 生产迁移零事故（Mock/生产切换是配置而非代码重写）
- 技术债务显式可追溯，避免"本地能跑生产不能跑"的隐性债务
- 长期演进路径清晰，每批次扩展有明确触发条件

**潜在风险**：
- **风险 1：Mock 数据与真实 API 响应差异大**：通过契约测试 + 真实样本采集缓解；首次生产部署前必须用真实 API 跑一次 `--dry-run`
- **风险 2：本地 10 万页面构建 OOM**：通过分阶段压力测试（1→3→10 语种）提前发现；必要时增加 `--cacheDir` 和分批构建
- **风险 3：生产迁移时网络通道不稳定**：通过 `ENV` 切换支持部分迁移（先迁移 Wikipedia，再迁移 AI）；保留本地回滚能力
- **风险 4：技术债务积累超出可控范围**：通过 `tech-debt-ledger.md` 显式登记 + 每月评审偿还进度
- **风险 5：`act` 与真实 GitHub Actions 行为差异**：关键 Workflow 必须在 Phase 4 用真实 GitHub Actions 复验

**成本估算**：
- 人力：38 人天（Phase 0: 5 + Phase 1: 8 + Phase 2: 12 + Phase 3: 7 + Phase 4: 6）
- 时间：5 周（含缓冲）
- 技术债务：8 项显式登记（TD-001~008），预计 Month 4-12 偿还完毕
- 维护：长期投入 5-10 小时/周（与 06_路线图一致）
- 财务：本地阶段 $0（Mock 全免费）；生产迁移阶段 $30-50（域名 + 首月 AI 调用）

**致命失败场景**：
1. **Mock 数据采样渠道不合规** → 项目启动即面临法律风险 → 必须在 Phase 0 确认 Wikipedia API 的合规访问途径（API 与网页爬取的合规性不同）
2. **本地 10 万页面构建持续 OOM** → Phase 3 无法验收 → 必须在 Phase 0 评估本地机器内存（建议 ≥ 16GB），否则需切换到云开发环境
3. **生产迁移时 API 契约不一致** → 真实 API 调用全部失败 → 必须在 Phase 1 用真实样本（即使少量）验证契约
4. **用户长期无法获得国外网络访问** → Phase 4 无法执行 → 需提前与用户确认是否有委托运维或临时 VPN 方案，否则项目卡在 Phase 3

---

### 方案2：契约驱动 + 垂直切片方案（技术先行派）

**核心思路**：

将所有外部依赖抽象为"契约接口"（Python Protocol / ABC），本地实现与生产实现是同一契约的两个 Provider。开发采用"垂直切片"：先用 1 日 × 1 地区 × 1 语种跑通从 Wikipedia 抓取到 Hugo 部署的完整链路，再横向扩展到 366 × 30 × 10。Mock 数据通过契约自动生成（基于 OpenAPI 的 `examples` 字段），减少人工编写成本。该方案强调**契约即真理**和**最小可验证切片**。

**实施步骤**：

#### 步骤 2.1：契约接口定义（Week 0，4 人天）

**前置条件**：项目目录已建立。

**任务清单**：
1. 用 Python Protocol 定义 6 个抽象接口：
   - `WikipediaFetcher`（fetch_on_this_day(month, day) → EventPool）
   - `Regionalizer`（regionalize(events, countries) → RegionalEvents）
   - `Translator`（translate(events, lang) → TranslatedEvents）
   - `Illustrator`（illustrate(events) → IllustratedEvents）
   - `Auditor`（audit(events) → AuditReport）
   - `Publisher`（publish(events) → DeployResult）
2. 为每个接口编写 Mock 实现和 Production 实现
3. 用 `pytest` + `hypothesis` 编写契约测试（基于属性测试）
4. 定义"垂直切片"数据集：1 日（07-04）× 1 地区（us）× 1 语种（en）

**验收标准**：
- [ ] 6 个接口的 Mock 和 Production 实现均通过契约测试
- [ ] `hypothesis` 属性测试发现 0 个契约违反
- [ ] 垂直切片数据集准备完成（5 个事件的 JSON 样本）

**产出物**：6 个契约接口 + Mock/Production 双实现 + 契约测试套件

---

#### 步骤 2.2：垂直切片全链路（Week 1，5 人天）

**前置条件**：契约接口定义完成。

**任务清单**：
1. 用垂直切片数据集跑通完整管道（仅 1 日 × 1 地区 × 1 语种）
2. 实现 Hugo 单页模板（day.html）
3. 本地 Hugo 构建单页，验证渲染正确
4. 验证 JSON-LD / hreflang / canonical 等 SEO 元素
5. 用 `act` 模拟 GitHub Actions 部署到本地"伪 Cloudflare Pages"（用 Nginx 容器模拟）

**验收标准**：
- [ ] 垂直切片管道在 30 秒内完成
- [ ] Hugo 单页构建成功，HTML 符合 SEO 规范
- [ ] `act` 模拟部署成功，本地 Nginx 可访问

**产出物**：垂直切片全链路 + 单页 Hugo 模板 + 本地部署模拟

---

#### 步骤 2.3：横向扩展 — 地区维度（Week 2，4 人天）

**前置条件**：垂直切片全链路通过。

**任务清单**：
1. 扩展到 30 地区 × 1 日 × 1 语种 = 30 页面
2. 验证地区过滤逻辑、local_angle 字段、地区导航组件
3. 扩展 Mock 数据集到 30 地区

**验收标准**：
- [ ] 30 地区页面全部构建成功
- [ ] 地区导航组件正常工作

**产出物**：30 地区横向扩展 + 地区级 Mock 数据集

---

#### 步骤 2.4：横向扩展 — 日期维度（Week 3，6 人天）

**前置条件**：30 地区扩展通过。

**任务清单**：
1. 扩展到 366 日 × 30 地区 × 1 语种 = 10,980 页面
2. 编写 `generate_blank_pages.py` 批量生成脚本
3. Mock 数据集扩展到 366 日（部分日期复用样本 + 参数化生成）
4. Hugo 10,980 页面构建性能验证

**验收标准**：
- [ ] 10,980 页面 Hugo 构建 < 2 分钟
- [ ] sitemap.xml 包含全部 10,980 URL

**产出物**：10,980 页面全量构建 + 日期维度 Mock 数据集

---

#### 步骤 2.5：横向扩展 — 语种维度（Week 4，5 人天）

**前置条件**：10,980 页面构建通过。

**任务清单**：
1. 扩展到 10 语种 × 30 地区 × 366 日 = 109,800 页面
2. 翻译 Mock 数据集扩展（10 语种 × 5 事件样本）
3. hreflang 互链验证
4. 10 万页面 Hugo 构建压力测试
5. Pagefind 索引生成验证

**验收标准**：
- [ ] 109,800 页面 Hugo 构建 < 10 分钟
- [ ] 10 语种 hreflang 互链全部正确
- [ ] Pagefind 索引生成成功

**产出物**：10 万页面全量构建 + 多语种 Mock 数据集

---

#### 步骤 2.6：生产迁移（Week 5，6 人天）

**前置条件**：10 万页面本地构建通过。

**任务清单**：
1. 切换 6 个契约接口的实现：Mock → Production
2. 验证每个接口的真实 API 调用
3. 配置 GitHub 仓库 + Cloudflare Pages + 域名
4. 首次生产部署
5. 契约测试在生产环境复验

**验收标准**：
- [ ] 6 个接口的生产实现全部通过契约测试
- [ ] 生产环境 30 地区首页可访问
- [ ] GitHub Actions daily-history.yml 成功执行

**产出物**：生产环境上线 + 契约测试生产复验报告

---

**阶段划分与依赖图**：

```
Phase A (契约定义) ─→ Phase B (垂直切片) ─→ Phase C (地区扩展) ─→ Phase D (日期扩展) ─→ Phase E (语种扩展) ─→ Phase F (生产迁移)
                                              │                       │                       │
                                              └─ Phase C.5 (地区Mock) ─┴─ Phase D.5 (日期Mock) ┴─ Phase E.5 (语种Mock)
```

**串行/并行判定**：
- **必须串行**：Phase A → B（契约是切片基础）；B → C → D → E（每个维度扩展依赖前一个）
- **可并行**：Phase C/D/E 与对应的 Mock 数据扩展（C.5/D.5/E.5）可并行

---

**关键里程碑**：

| 里程碑 | 完成阶段 | 可验证产出物 | 验收标准 |
|--------|---------|-------------|---------|
| M1: 契约接口定稿 | Phase A | 6 个 Python Protocol + 契约测试 | 契约测试 100% 通过 |
| M2: 垂直切片跑通 | Phase B | 1 日 × 1 地区 × 1 语种全链路 | 30 秒内完成；HTML 合规 |
| M3: 30 地区扩展 | Phase C | 30 地区页面 | 地区导航正常 |
| M4: 10,980 页面 | Phase D | 全量日期页面 | 构建 < 2 分钟 |
| M5: 109,800 页面 | Phase E | 10 语种全量页面 | 构建 < 10 分钟 |
| M6: 生产上线 | Phase F | Cloudflare Pages 部署 | 契约测试生产复验通过 |

---

**本地 → 生产迁移路径**：

| 迁移项 | 本地版 | 生产版 | 切换方式 | 回滚方案 |
|--------|--------|--------|---------|---------|
| 6 个核心接口 | Mock 实现（基于契约） | Production 实现（基于契约） | 依赖注入切换（`provider.py`） | 切回 Mock 实现 |
| Hugo 构建 | 本地 hugo server | Cloudflare Pages | git push 触发 Actions | git revert |
| GitHub Actions | `act` 本地模拟 | 真实 GitHub Actions | 推送 workflow 文件 | 保留 act 配置 |
| 域名/DNS | localhost | 真实域名 | Cloudflare DNS 配置 | 保留本地访问 |

**迁移执行顺序**：
1. 接口实现切换（6 个接口逐个切换，每个切换后跑契约测试）
2. 推送代码触发 GitHub Actions
3. 验证 Cloudflare Pages 部署
4. 生产环境契约测试复验

---

**长期演进路径**：

- **短期（Month 1-3）**：垂直切片稳定，10 万页面生产部署
- **中期（Month 4-12）**：契约扩展（新增 API 服务接口）；偿还 Mock 数据债务
- **长期（Year 2+）**：契约复用到子站点矩阵；多仓库架构

**地区/语种扩展路径**：
| 扩展批次 | 地区数 | 语种数 | 页面数 | 触发条件 |
|---------|--------|--------|--------|---------|
| 垂直切片 | 1 | 1 | 1 | 契约定义完成 |
| 地区扩展 | 30 | 1 | 10,980 | 垂直切片通过 |
| 日期扩展 | 30 | 1 | 10,980 | 地区扩展通过 |
| 语种扩展 | 30 | 10 | 109,800 | 日期扩展通过 |
| 长期扩展 | 100+ | 20+ | 500,000+ | Year 2-3 |

---

**预期效果**：
- 垂直切片在 1 周内验证全链路，降低后期返工风险
- 契约驱动保证 Mock/生产实现一致性，迁移是依赖注入切换
- 横向扩展路径清晰，每个维度独立验证

**潜在风险**：
- **风险 1：契约设计过早抽象** → 接口可能不适合真实业务变化 → 通过 Phase B 切片验证后再固化契约
- **风险 2：垂直切片过小，无法暴露规模问题** → 10 万页面构建问题在 Phase E 才暴露 → Phase E 必须做完整压力测试
- **风险 3：Mock 数据自动生成质量低** → 影响开发体验 → 关键场景仍需人工编写高质量样本
- **风险 4：契约维护成本高** → 接口变更需同步改 Mock/Production/测试 → 通过代码生成工具缓解

**成本估算**：
- 人力：30 人天（Phase A: 4 + B: 5 + C: 4 + D: 6 + E: 5 + F: 6）
- 时间：5 周
- 技术债务：契约抽象过早可能导致 2-3 项隐性债务
- 维护：5-10 小时/周
- 财务：本地 $0；生产迁移 $30-50

**致命失败场景**：
1. **契约设计错误导致生产实现无法满足** → Phase F 全部失败 → 必须在 Phase B 用真实 API 样本（即使少量）验证契约
2. **垂直切片过于简化，掩盖规模问题** → Phase E 暴露严重性能问题 → Phase E 必须做完整 10 万页面压力测试
3. **契约变更频率过高** → 开发效率急剧下降 → Phase B 后冻结契约，变更需评审
4. **Mock 自动生成数据与真实数据分布差异大** → 本地测试通过但生产失败 → 关键场景必须用真实样本

---

### 方案3：本地镜像生产环境方案（环境对等派）

**核心思路**：

用 Docker Compose 在本地构建一个完整的"镜像生产环境"，所有外部服务用本地镜像服务替代：Flask Mock Server 替代 Wikipedia/AI API、本地 Ollama 替代 Claude/GPT-4o（用 Qwen/Llama 开源模型）、本地 Gitea 替代 GitHub、本地 MinIO 替代 Cloudflare R2、本地 Nginx 替代 Cloudflare Pages、本地 MailHog 替代 Buttondown。本地环境与生产环境**架构对等**，迁移只是"端点地址切换"。该方案强调**环境对等性**和**迁移零事故**。

**实施步骤**：

#### 步骤 3.1：Docker Compose 镜像环境搭建（Week 0-1，8 人天）

**前置条件**：本地具备 Docker Desktop（建议 16GB+ 内存）。

**任务清单**：
1. 编写 `docker-compose.yml`，定义 8 个服务：
   - `mock-wikipedia`（Flask，端口 8765）
   - `mock-anthropic`（Flask，端口 8766）
   - `mock-openai`（Flask，端口 8767）
   - `mock-gemini`（Flask，端口 8768）
   - `local-llm`（Ollama，端口 11434，可选，用于真实 AI 调用验证）
   - `local-gitea`（GitHub 替代，端口 3000）
   - `local-minio`（R2 替代，端口 9000）
   - `local-nginx`（Cloudflare Pages 替代，端口 8080）
   - `local-mailhog`（Buttondown 替代，端口 8025）
2. 编写每个服务的 Dockerfile 和初始数据卷
3. 编写 `scripts/init_local_env.sh` 一键启动脚本
4. 编写 `scripts/health_check.sh` 健康检查脚本

**验收标准**：
- [ ] `docker-compose up -d` 一键启动全部 8 个服务
- [ ] 健康检查脚本全部通过
- [ ] 每个服务可通过 `curl` 访问并返回预期响应

**产出物**：Docker Compose 镜像环境 + 一键启动脚本

---

#### 步骤 3.2：镜像服务实现与契约对齐（Week 1-2，7 人天）

**前置条件**：Docker Compose 环境运行正常。

**任务清单**：
1. 实现每个镜像服务的 API 端点，与 6 份契约对齐
2. 配置 `local-gitea` 替代 GitHub：
   - 创建仓库
   - 配置 Gitea Actions（兼容 GitHub Actions 语法）
3. 配置 `local-nginx` 替代 Cloudflare Pages：
   - 配置静态文件服务
   - 配置 _headers / _redirects 规则
4. 配置 `local-mailhog` 替代 Buttondown：
   - 实现订阅 API
   - 实现邮件发送 API
5. 配置 `local-minio` 替代 Cloudflare R2：
   - 创建 bucket
   - 配置 S3 兼容 API

**验收标准**：
- [ ] 8 个镜像服务的 API 全部通过契约测试
- [ ] Gitea Actions 可执行 `.github/workflows/*.yml`
- [ ] Nginx 可服务 Hugo 构建产物
- [ ] MailHog 可接收订阅请求
- [ ] MinIO 可上传/下载文件

**产出物**：完整镜像服务实现 + Gitea Actions 配置 + Nginx/MinIO/MailHog 配置

---

#### 步骤 3.3：内容管道在镜像环境运行（Week 2-3，8 人天）

**前置条件**：镜像服务全部通过契约测试。

**任务清单**：
1. 实现 `scripts/pipeline.py`，所有外部调用指向镜像服务
2. 配置环境变量：
   - `WIKI_API_BASE=http://mock-wikipedia:8765`
   - `ANTHROPIC_API_BASE=http://mock-anthropic:8766`
   - `OPENAI_API_BASE=http://mock-openai:8767`
   - `GEMINI_API_BASE=http://mock-gemini:8768`
   - `GIT_REMOTE=http://local-gitea:3000/git/today-in-history.git`
   - `R2_ENDPOINT=http://local-minio:9000`
   - `EMAIL_API=http://local-mailhog:8025/api`
3. 端到端测试：`docker-compose exec pipeline python3 scripts/pipeline.py 2026-07-04`
4. 验证 Gitea Actions 自动触发部署到 Nginx
5. 验证 Nginx 服务的内容可访问

**验收标准**：
- [ ] 单日管道在镜像环境完整跑通
- [ ] Gitea Actions 自动部署到 Nginx
- [ ] Nginx 服务的页面可访问
- [ ] MinIO 备份成功
- [ ] MailHog 收到订阅邮件

**产出物**：镜像环境端到端管道 + Gitea Actions 自动部署

---

#### 步骤 3.4：Hugo 10 万页面构建（Week 3-4，5 人天）

**前置条件**：镜像环境管道跑通。

**任务清单**：
1. 批量回填 366 × 30 × 10 = 109,800 页面内容（Mock 数据）
2. Hugo 构建 10 万页面
3. Pagefind 索引生成
4. Nginx 服务 10 万页面
5. 性能测试：Lighthouse + Core Web Vitals

**验收标准**：
- [ ] 109,800 页面 Hugo 构建 < 10 分钟
- [ ] Nginx 服务 10 万页面正常
- [ ] Lighthouse > 90

**产出物**：10 万页面镜像环境部署 + 性能测试报告

---

#### 步骤 3.5：生产迁移 — 端点切换（Week 5，5 人天）

**前置条件**：10 万页面镜像环境稳定运行。

**任务清单**：
1. 配置 `.env.production`，将所有端点切换到真实服务：
   - `WIKI_API_BASE=https://api.wikimedia.org`
   - `ANTHROPIC_API_BASE=https://api.anthropic.com`
   - `OPENAI_API_BASE=https://api.openai.com`
   - `GEMINI_API_BASE=https://generativelanguage.googleapis.com`
   - `GIT_REMOTE=https://github.com/your-org/today-in-history.git`
   - `R2_ENDPOINT=https://<account>.r2.cloudflarestorage.com`
   - `EMAIL_API=https://api.buttondown.email`
2. 配置 GitHub 仓库 + Cloudflare Pages + 域名
3. 推送代码到 GitHub，触发 GitHub Actions
4. 验证生产环境部署

**验收标准**：
- [ ] 生产环境 30 地区首页可访问
- [ ] GitHub Actions daily-history.yml 成功
- [ ] sitemap 提交到 GSC

**产出物**：生产环境上线 + 端点切换配置

---

**阶段划分与依赖图**：

```
Phase α (Docker 环境) ─→ Phase β (镜像服务) ─→ Phase γ (管道运行) ─→ Phase δ (10万页面) ─→ Phase ε (生产迁移)
                              ↑
                              │
Phase α.5 (真实 AI 验证) ─────┘（可选：用 local-llm 验证 AI 调用逻辑）
```

**串行/并行判定**：
- **必须串行**：Phase α → β → γ → δ → ε（每阶段依赖前一阶段的环境）
- **可并行**：Phase α.5（用 Ollama 验证 AI 调用）与 Phase β 并行

---

**关键里程碑**：

| 里程碑 | 完成阶段 | 可验证产出物 | 验收标准 |
|--------|---------|-------------|---------|
| M1: Docker 环境就绪 | Phase α | docker-compose.yml + 8 个服务 | 一键启动 + 健康检查通过 |
| M2: 镜像服务契约对齐 | Phase β | 8 个镜像服务实现 | 契约测试 100% 通过 |
| M3: 管道在镜像环境跑通 | Phase γ | 端到端管道 | Gitea Actions 自动部署成功 |
| M4: 10 万页面镜像部署 | Phase δ | Nginx 服务 10 万页面 | 构建 < 10 分钟；Lighthouse > 90 |
| M5: 生产端点切换 | Phase ε | 生产环境上线 | 30 地区首页可访问 |

---

**本地 → 生产迁移路径**：

| 迁移项 | 本地版（镜像） | 生产版 | 切换方式 | 回滚方案 |
|--------|--------------|--------|---------|---------|
| Wikipedia API | mock-wikipedia 容器 | 真实 Wikipedia API | `WIKI_API_BASE` 环境变量 | 切回容器地址 |
| AI API | mock-anthropic/openai/gemini 容器 | 真实 AI API | 各 `*_API_BASE` 环境变量 | 切回容器地址 |
| Git 托管 | local-gitea 容器 | GitHub | `GIT_REMOTE` 环境变量 | 切回 Gitea |
| CI/CD | Gitea Actions | GitHub Actions | 推送 workflow 文件到 GitHub | 保留 Gitea 配置 |
| 静态托管 | local-nginx 容器 | Cloudflare Pages | git push 触发 Actions | 切回 Nginx |
| 对象存储 | local-minio 容器 | Cloudflare R2 | `R2_ENDPOINT` 环境变量 | 切回 MinIO |
| 邮件订阅 | local-mailhog 容器 | Buttondown | `EMAIL_API` 环境变量 | 切回 MailHog |
| 域名 | localhost:8080 | today-in-history.example.com | Cloudflare DNS | 保留本地访问 |

**迁移执行顺序**：
1. 端点环境变量切换（一次性切换所有 `*_BASE` 变量）
2. 验证每个真实 API 连通性
3. 推送代码到 GitHub
4. 触发 GitHub Actions 部署到 Cloudflare Pages
5. 配置真实域名/DNS
6. 全程保留镜像环境作为回滚方案

---

**长期演进路径**：

- **短期（Month 1-3）**：镜像环境稳定运行，10 万页面生产部署
- **中期（Month 4-12）**：镜像环境作为持续集成测试环境（CI 用 Docker Compose 跑端到端测试）；偿还 Mock 数据债务
- **长期（Year 2+）**：镜像环境扩展到子站点矩阵测试；多仓库架构

**地区/语种扩展路径**：
| 扩展批次 | 地区数 | 语种数 | 页面数 | 触发条件 | 镜像环境验证 |
|---------|--------|--------|--------|---------|------------|
| 基线 | 30 | 1 | 10,980 | 镜像环境跑通 | ✅ |
| 第 1 扩展 | 30 | 5 | 54,900 | 月 UV > 5k | 镜像环境预验证 |
| 第 2 扩展 | 30 | 10 | 109,800 | 月 UV > 10k | 镜像环境预验证 |
| 第 3 扩展 | 60 | 10 | 219,600 | 月 UV > 50k | 镜像环境扩展 |
| 第 4 扩展 | 100+ | 20+ | 500,000+ | Year 2-3 | 镜像环境扩展 |

---

**预期效果**：
- 本地环境与生产环境架构对等，迁移是端点切换而非代码重写
- Docker Compose 一键启动，开发体验优秀
- 镜像环境可长期作为 CI 测试环境复用
- 真实 AI 调用逻辑可通过 local-llm（Ollama）验证

**潜在风险**：
- **风险 1：本地资源占用大** → Docker Desktop 8 个容器需 8GB+ 内存 → 必须在 Phase α 评估本地机器配置
- **风险 2：镜像服务与真实服务行为差异** → Nginx 与 Cloudflare Pages 的 _headers/_redirects 解析差异 → 必须在 Phase ε 用真实 Cloudflare 复验
- **风险 3：Gitea Actions 与 GitHub Actions 兼容性** → 部分 actions 可能不兼容 → 关键 workflow 必须在 GitHub 复验
- **风险 4：local-llm（Ollama）输出质量与 Claude/GPT-4o 差异大** → 无法完全验证 AI 管道质量 → local-llm 仅作为调用逻辑验证，质量验证必须延迟到生产
- **风险 5：Docker Compose 启动顺序依赖** → 服务间依赖可能导致启动失败 → 用 `depends_on` + `healthcheck` 解决

**成本估算**：
- 人力：33 人天（Phase α: 8 + β: 7 + γ: 8 + δ: 5 + ε: 5）
- 时间：5 周
- 技术债务：镜像服务与真实服务差异（4-5 项隐性债务）
- 维护：镜像环境长期维护 2-3 小时/周
- 财务：本地 $0（Docker 免费）；生产迁移 $30-50

**致命失败场景**：
1. **本地机器内存不足** → Docker 容器全部崩溃 → 必须在 Phase α 评估硬件，建议 ≥ 16GB 内存
2. **Gitea Actions 与 GitHub Actions 严重不兼容** → workflow 无法迁移 → 必须在 Phase β 验证关键 actions 兼容性
3. **镜像服务行为与真实服务差异导致生产失败** → 端点切换后全部失败 → 必须在 Phase ε 用真实 API 跑一次 dry-run
4. **Docker Compose 配置复杂度爆炸** → 维护成本超出预期 → 关键服务用配置文件而非环境变量
5. **local-llm 误导 AI 管道开发** → 开发基于 Ollama 输出，生产用 Claude 输出差异大 → local-llm 仅作调用逻辑验证，不作为质量验证依据

---

## 方案对比与战略建议

### 三方案战略对比矩阵

| 战略维度 | 方案1（分层渐进） | 方案2（契约+切片） | 方案3（镜像环境） |
|---------|-----------------|------------------|-----------------|
| **阶段划分精度** | ⭐⭐⭐⭐⭐ 5 阶段严格定义 | ⭐⭐⭐⭐ 6 阶段切片式 | ⭐⭐⭐ 5 阶段环境式 |
| **阶段依赖清晰度** | ⭐⭐⭐⭐⭐ 串行/并行明确 | ⭐⭐⭐⭐ 切片扩展依赖 | ⭐⭐⭐ 环境依赖 |
| **里程碑可验证性** | ⭐⭐⭐⭐⭐ 每里程碑产出物明确 | ⭐⭐⭐⭐ 切片验证 | ⭐⭐⭐ 环境验证 |
| **本地→生产迁移** | ⭐⭐⭐⭐ 配置切换 + 回滚 | ⭐⭐⭐⭐⭐ 依赖注入切换 | ⭐⭐⭐⭐⭐ 端点切换 |
| **技术债务管理** | ⭐⭐⭐⭐⭐ 显式登记表 | ⭐⭐⭐ 契约抽象隐性债务 | ⭐⭐⭐ 镜像差异隐性债务 |
| **长期演进路径** | ⭐⭐⭐⭐⭐ 5 批次扩展明确 | ⭐⭐⭐⭐ 切片式扩展 | ⭐⭐⭐⭐ 镜像环境复用 |
| **风险对齐** | ⭐⭐⭐⭐⭐ 与 07 文档对齐 | ⭐⭐⭐⭐ 契约风险 | ⭐⭐⭐ 资源风险 |
| **资源投入** | 38 人天（最高） | 30 人天（中） | 33 人天（中高） |
| **本地资源要求** | 低（仅需 Python/Hugo） | 低（仅需 Python/Hugo） | 高（需 Docker + 16GB 内存） |
| **首次验证速度** | 慢（Phase 2 才跑通管道） | 快（Phase B 1 周跑通切片） | 中（Phase γ 跑通管道） |

### 战略架构师推荐

**首选方案：方案1（分层渐进式 Mock→生产切换方案）**

**推荐理由（压倒性优势）**：

1. **阶段可验证性最强**：每阶段有明确的入站/出站条件和可验证产出物，符合战略架构师"证据驱动"原则。Phase 0~4 的划分与现有 06_路线图的 Phase 0~4 对齐，团队认知成本低。

2. **技术债务显式管理**：`tech-debt-ledger.md` 是本方案的灵魂。本地版妥协了什么（TD-001~008）、何时偿还、如何偿还，全部显式登记。这避免了"本地能跑生产不能跑"的隐性债务陷阱，是战略层面的核心保障。

3. **本地资源要求最低**：仅需 Python + Hugo + act，无需 Docker Desktop 和 16GB 内存。这对用户在本地的开发体验最友好。

4. **风险对齐最佳**：本方案的 5 大潜在风险与 07_风险管理与合规方案.md 的风险矩阵高度对齐（网络风险、API 风险、规模风险、迁移风险、债务风险）。

5. **长期演进路径最清晰**：5 批次地区/语种扩展路径有明确触发条件，与 06_路线图的 Phase 2-4 完美衔接。

**次选方案：方案2（契约驱动+垂直切片）**

如果团队偏好"快速验证全链路"且能接受契约抽象的隐性债务，方案2 的垂直切片在 1 周内跑通全链路是巨大优势。但契约设计过早抽象是潜在风险。

**不推荐方案3（镜像环境）**：

虽然"环境对等"理念优秀，但 Docker Compose 8 个容器的资源占用对本地机器要求过高（16GB+ 内存），且镜像服务与真实服务的行为差异（Nginx vs Cloudflare Pages、Gitea Actions vs GitHub Actions）会引入新的隐性债务。除非用户本地具备强大的硬件配置，否则不建议。

### 战略架构师最终建议

采用**方案1 为主框架，吸收方案2 的垂直切片思想**：

- **Phase 2.5（新增）**：在 Phase 2 完成后、Phase 3 之前，先用 1 日 × 1 地区 × 1 语种跑通完整 Hugo 单页构建，验证模板和 SEO 元素。这是方案2 垂直切片的精华。
- **Phase 1.5（新增）**：在 Phase 1 Mock 体系完成后，立即用 `hypothesis` 对 6 份契约做属性测试，提前发现契约设计问题。这是方案2 契约驱动的精华。

这样既保留了方案1 的阶段严谨性和技术债务显式管理，又获得了方案2 的早期验证优势。

---

## 附录：与现有风险合规文档的对齐矩阵

| 07_风险文档中的风险 | 本方案应对措施 | 对齐阶段 |
|-------------------|--------------|---------|
| 网络不可达风险 | Mock Server 全覆盖外部依赖 | Phase 1 |
| AI API 故障风险 | Provider 切换器支持降级 | Phase 1/2 |
| Wikipedia API 限流 | Mock 数据预采集 + 缓存机制 | Phase 1/2 |
| Hugo 构建性能风险 | 分阶段压力测试（1→3→10 语种） | Phase 3 |
| 敏感事件合规风险 | AI 审核模块 + 人工抽检流程 | Phase 2 |
| GitHub Actions 故障 | `act` 本地模拟 + 真实复验 | Phase 3/4 |
| Cloudflare 服务中断 | 保留本地 Nginx 备用方案 | Phase 4 |
| 域名/DNS 配置错误 | Phase 4 严格按 05_部署方案执行 | Phase 4 |
| API Key 泄露风险 | `.env.production` 不入 Git | Phase 4 |
| 法律合规风险 | Wikipedia API 合规访问 + AI 内容披露 | Phase 0/2 |

---

**方案版本**：v1.0
**编写日期**：2026-07-19
**编写者**：战略架构师（R_strategist）
**适用轮次**：第 1 轮（共 2 轮）
**下次评审**：第 2 轮（基于第 1 轮反馈细化）
