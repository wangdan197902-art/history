# S25 - 迁移到 Cloudflare Pages

> 阶段：Phase 4 - 生产迁移
> 人天：2 | 依赖：S24 | 前置：GitHub Actions 就绪

---

## 一、步骤概述

配置 Cloudflare Pages 项目，绑定 GitHub 仓库，设置构建命令与输出目录，配置自定义域名。生产环境通过 git push 触发自动部署。

## 二、任务清单

### 2.1 Cloudflare Pages 配置

文件：`docs/cloudflare-pages-setup.md`

```markdown
# Cloudflare Pages 配置

## 项目信息

| 项目 | 值 |
|------|-----|
| 项目名称 | today-in-history |
| 生产分支 | main |
| 构建命令 | `cd site && hugo --minify --gc && cd public && npx pagefind --source .` |
| 构建输出目录 | `site/public` |
| Node 版本 | 20 |
| Hugo 版本 | 0.130.0 Extended |

## 环境变量

| 变量名 | 值 |
|--------|-----|
| HUGO_VERSION | 0.130.0 |
| NODE_VERSION | 20 |
| GO_VERSION | 1.22 |

## 创建步骤

1. 登录 Cloudflare Dashboard → Pages → Create a project
2. Connect to Git → 选择 GitHub 仓库
3. 配置构建命令与输出目录
4. 添加环境变量
5. Save and Deploy

## 自定义域名

1. Pages 项目 → Custom domains → Set up a domain
2. 添加域名（如 today-in-history.example.com）
3. 按提示添加 CNAME 记录到 Cloudflare DNS
4. 等待 DNS 生效（< 5min）
```

### 2.2 构建命令优化

文件：`scripts/production_build.sh`

```bash
#!/bin/bash
set -e

echo "=== 生产环境构建 ==="

# 1. Hugo 构建
cd site
hugo --minify --gc \
     --cacheDir /tmp/hugo-cache \
     --baseURL https://today-in-history.example.com/

# 2. Pagefind 索引
cd public
npx pagefind \
  --source . \
  --bundle-dir pagefind

# 3. 生成 sitemap.xml（Hugo 自动生成）
ls -la sitemap.xml

# 4. 生成 robots.txt
cat > robots.txt <<EOF
User-agent: *
Allow: /
Sitemap: https://today-in-history.example.com/sitemap.xml
EOF

echo "=== 构建完成 ==="
echo "输出目录: $(pwd)"
echo "HTML 文件数: $(find . -name '*.html' | wc -l)"
echo "总体积: $(du -sh . | cut -f1)"
```

### 2.3 部署脚本

文件：`scripts/deploy_cloudflare.sh`

```bash
#!/bin/bash
set -e

echo "=== 部署到 Cloudflare Pages ==="

# 检查环境变量
: "${CLOUDFLARE_API_TOKEN:?需要设置 CLOUDFLARE_API_TOKEN}"
: "${CLOUDFLARE_ACCOUNT_ID:?需要设置 CLOUDFLARE_ACCOUNT_ID}"

PROJECT_NAME="today-in-history"
DEPLOY_DIR="site/public"

# 1. 构建生产版本
bash scripts/production_build.sh

# 2. 使用 wrangler 部署
npx wrangler pages deploy "$DEPLOY_DIR" \
    --project-name "$PROJECT_NAME" \
    --commit-message "$(git log -1 --pretty=%B)"

echo "=== 部署完成 ==="
echo "🌐 访问: https://$PROJECT_NAME.pages.dev"
```

### 2.4 域名与 DNS 配置

文件：`docs/dns-setup.md`

```markdown
# DNS 配置

## Cloudflare DNS 记录

| 类型 | 名称 | 内容 | 代理 |
|------|------|------|------|
| CNAME | today-in-history | today-in-history.pages.dev | 已代理 |
| CNAME | www | today-in-history.pages.dev | 已代理 |

## 验证

```bash
dig today-in-history.example.com
# 应返回 CNAME → today-in-history.pages.dev

curl -I https://today-in-history.example.com/
# 应返回 200 + cf-cache-status: HIT
```

## SSL 证书

Cloudflare 自动签发 Universal SSL，无需手动配置。
```

### 2.5 回滚脚本

文件：`scripts/rollback_cloudflare.sh`

```bash
#!/bin/bash
set -e

echo "=== Cloudflare Pages 回滚 ==="

PROJECT_NAME="today-in-history"

# 列出最近 5 次部署
echo "最近部署列表:"
npx wrangler pages deployment list \
    --project-name "$PROJECT_NAME" | head -20

read -p "输入要回滚的 deployment ID: " DEPLOY_ID

if [ -z "$DEPLOY_ID" ]; then
    echo "❌ 未输入 deployment ID"
    exit 1
fi

# 回滚
npx wrangler pages deployment delete "$DEPLOY_ID" \
    --project-name "$PROJECT_NAME"

echo "✅ 回滚完成"
```

## 三、实施步骤

1. 编写 `docs/cloudflare-pages-setup.md` 配置文档
2. 编写 `scripts/production_build.sh` 生产构建
3. 编写 `scripts/deploy_cloudflare.sh` 部署脚本
4. 编写 `docs/dns-setup.md` DNS 配置
5. 编写 `scripts/rollback_cloudflare.sh` 回滚脚本
6. 待网络可用后：
   - 在 Cloudflare Dashboard 创建 Pages 项目
   - 绑定 GitHub 仓库
   - 推送代码触发首次部署
   - 配置自定义域名
   - 验证部署成功

## 四、验收命令

```bash
# 1. 本地构建生产版本
bash scripts/production_build.sh
# 期望:
# - HTML 文件数 ≥ 100,000
# - 总体积 < 2GB
# - sitemap.xml 存在
# - robots.txt 存在

# 2. 待网络可用后部署
export CLOUDFLARE_API_TOKEN=...
export CLOUDFLARE_ACCOUNT_ID=...
bash scripts/deploy_cloudflare.sh
# 期望: 部署成功，访问 https://today-in-history.pages.dev

# 3. 配置自定义域名后验证
curl -I https://today-in-history.example.com/
# 期望: 200 + cf-cache-status: HIT
```

## 五、依赖关系

- 前置：S24
- 后续：S26（生产验证）

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| Cloudflare Pages 构建超时 | 中 | 优化 Hugo 构建，< 10min |
| 部署失败 | 低 | 回滚脚本 |
| DNS 未生效 | 低 | 等待 5min，联系 Cloudflare 支持 |
| 自定义域名 SSL 错误 | 低 | Cloudflare Universal SSL 自动 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 首次部署时间 | < 15min | Cloudflare Dashboard |
| CDN 命中率 | > 95% | Cloudflare Analytics |
| TTFB | < 200ms | `curl -w "%{time_total}"` |
| 全球访问延迟 | < 500ms | Cloudflare Analytics |

## 八、测试要求

- 生产构建成功
- 部署到 Cloudflare Pages
- 自定义域名可访问
- SSL 证书有效
- CDN 命中率 > 95%
