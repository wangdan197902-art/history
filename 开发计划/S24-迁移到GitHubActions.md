# S24 - 迁移到 GitHub Actions

> 阶段：Phase 4 - 生产迁移
> 人天：2 | 依赖：S23 + 网络可用 | 前置：本地全链路通过

---

## 一、步骤概述

编写 4 个 GitHub Actions workflow 文件，用 `act` 本地模拟验证，待网络可用后推送到 GitHub。包含：daily-pipeline / build-deploy / scheduled-backfill / performance-test。

## 二、任务清单

### 2.1 GitHub Actions workflow 文件

文件：`.github/workflows/daily-pipeline.yml`

```yaml
name: Daily Pipeline

on:
  schedule:
    - cron: '0 0 * * *'  # 每天 UTC 0:00
  workflow_dispatch:

jobs:
  pipeline:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Setup Hugo
        uses: peaceiris/actions-hugo@v3
        with:
          hugo-version: '0.130.0'
          extended: true

      - name: Install dependencies
        run: |
          python -m venv .venv
          . .venv/bin/activate
          pip install -r requirements.txt

      - name: Get today's date
        id: date
        run: echo "date=$(date +'%m-%d')" >> $GITHUB_OUTPUT

      - name: Run pipeline (production)
        env:
          ENV: production
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          . .venv/bin/activate
          python -m src.pipeline.orchestrator ${{ steps.date.outputs.date }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: pipeline-output-${{ steps.date.outputs.date }}
          path: site/content/
          retention-days: 7
```

文件：`.github/workflows/build-deploy.yml`

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - name: Setup Hugo
        uses: peaceiris/actions-hugo@v3
        with:
          hugo-version: '0.130.0'
          extended: true

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Hugo cache
        uses: actions/cache@v4
        with:
          path: ~/.cache/hugo-today-in-history
          key: ${{ runner.os }}-hugo-${{ hashFiles('site/assets/**', 'site/data/**') }}
          restore-keys: |
            ${{ runner.os }}-hugo-

      - name: Build Hugo
        run: |
          cd site
          hugo --minify --gc --cacheDir ~/.cache/hugo-today-in-history

      - name: Build Pagefind index
        run: |
          cd site/public
          npx pagefind --source . --bundle-dir pagefind

      - name: Deploy to Cloudflare Pages
        uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          projectName: today-in-history
          directory: site/public
          gitHubAccessToken: ${{ secrets.GITHUB_TOKEN }}
```

文件：`.github/workflows/scheduled-backfill.yml`

```yaml
name: Scheduled Backfill

on:
  workflow_dispatch:
    inputs:
      start_date:
        description: 'Start date (MM-DD)'
        required: true
      end_date:
        description: 'End date (MM-DD)'
        required: true

jobs:
  backfill:
    runs-on: ubuntu-latest
    timeout-minutes: 360
    strategy:
      matrix:
        date: ${{ github.event.inputs.dates }}
    steps:
      - uses: actions/checkout@v4
      # ... 类似 daily-pipeline
```

文件：`.github/workflows/performance-test.yml`

```yaml
name: Performance Test

on:
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  perf:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run performance tests
        run: |
          python scripts/perf_bench_build.py
          python scripts/analyze_public.py
```

### 2.2 act 本地模拟脚本

文件：`scripts/test_github_actions.sh`

```bash
#!/bin/bash
set -e

echo "=== act 本地模拟 GitHub Actions ==="

# 检查 act 是否安装
command -v act >/dev/null 2>&1 || {
    echo "❌ act 未安装，请运行: brew install act"
    exit 1
}

# 模拟 daily-pipeline
echo "[1/4] 模拟 daily-pipeline..."
act -W .github/workflows/daily-pipeline.yml \
    --secret-file .env.production \
    --dryrun

# 模拟 build-deploy
echo "[2/4] 模拟 build-deploy..."
act -W .github/workflows/build-deploy.yml \
    --secret-file .env.production \
    --dryrun

# 模拟 performance-test
echo "[3/4] 模拟 performance-test..."
act -W .github/workflows/performance-test.yml \
    --dryrun

# YAML 语法验证
echo "[4/4] 验证 workflow YAML..."
for f in .github/workflows/*.yml; do
    python -c "import yaml; yaml.safe_load(open('$f'))" && echo "  ✅ $f"
done

echo ""
echo "=== act 模拟完成 ==="
```

### 2.3 Secrets 配置文档

文件：`docs/github-secrets.md`

```markdown
# GitHub Actions Secrets 配置

## 必需 Secrets

| Secret 名称 | 用途 | 获取方式 |
|------------|------|---------|
| ANTHROPIC_API_KEY | Claude API | https://console.anthropic.com/ |
| OPENAI_API_KEY | GPT-4o API | https://platform.openai.com/api-keys |
| GEMINI_API_KEY | Gemini API | https://aistudio.google.com/ |
| CLOUDFLARE_API_TOKEN | Cloudflare Pages 部署 | https://dash.cloudflare.com/ |
| CLOUDFLARE_ACCOUNT_ID | Cloudflare 账户 ID | Cloudflare Dashboard |
| BUTTONDOWN_API_KEY | 邮件订阅（可选） | https://buttondown.email/ |

## 配置步骤

1. 进入 GitHub 仓库 → Settings → Secrets and variables → Actions
2. 点击 "New repository secret"
3. 添加上述每个 Secret
```

## 三、实施步骤

1. 创建 `.github/workflows/` 目录
2. 编写 4 个 workflow YAML 文件
3. 编写 `scripts/test_github_actions.sh` act 模拟脚本
4. 编写 `docs/github-secrets.md` Secrets 文档
5. 本地用 `act --dryrun` 验证 workflow 语法
6. 待网络可用后，推送到 GitHub 触发实际运行

## 四、验收命令

```bash
# 1. YAML 语法验证
for f in .github/workflows/*.yml; do
    python -c "import yaml; yaml.safe_load(open('$f'))" && echo "OK: $f"
done

# 2. act 本地模拟
bash scripts/test_github_actions.sh
# 期望: 所有 workflow dryrun 通过

# 3. 待网络可用后推送
git add .github/workflows/
git commit -m "ci: 添加 GitHub Actions workflows"
git push origin main
```

## 五、依赖关系

- 前置：S23 + 网络可用
- 后续：S25（Cloudflare Pages 部署）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| act 与真实 Actions 行为差异 | 中 | 关键 workflow 在生产复验 |
| Secrets 配置遗漏 | 中 | 文档清单检查 |
| workflow 超时 | 低 | timeout-minutes 设置 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| daily-pipeline 工作流总时长 | < 25min | GitHub Actions 日志 |
| build-deploy 工作流总时长 | < 15min | GitHub Actions 日志 |
| act dryrun 验证 | < 5min | `time` |

## 八、测试要求

- 4 个 workflow YAML 语法正确
- act dryrun 全部通过
- Secrets 文档完整
- 待网络可用后推送 GitHub 实际运行
