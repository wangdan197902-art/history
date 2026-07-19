# OpenAPI 契约目录

## 契约清单

| 文件 | API | 用途 | Mock 端点 |
|------|-----|------|----------|
| openapi_wikipedia.yaml | Wikipedia OnThisDay | 获取历史事件 | /wikipedia |
| openapi_anthropic.yaml | Anthropic Claude | 地区化重写 | /anthropic |
| openapi_openai.yaml | OpenAI GPT-4o | 多语种翻译 | /openai |
| openapi_gemini.yaml | Google Gemini | 配图描述生成 | /gemini |
| openapi_buttondown.yaml | Buttondown | 邮件订阅 | /buttondown |
| openapi_gsc.yaml | Google Search Console | SEO 提交 | /gsc |

## 使用方式

### 1. 契约语法验证

```bash
. .venv/bin/activate

# 验证 YAML 语法
for f in tests/contracts/*.yaml; do
  python -c "import yaml; yaml.safe_load(open('$f'))" && echo "OK: $f"
done
```

### 2. 契约测试(schemathesis)

```bash
# 启动 Mock Server
make mock-server &

# 运行契约测试
schemathesis run tests/contracts/openapi_wikipedia.yaml \
  --checks all \
  --base-url=http://127.0.0.1:8765
```

## 设计原则

1. **Mock 与生产对等**: 每份契约含 `servers` 字段,同时列出 Mock 与生产 URL
2. **完整 Schema**: 所有请求/响应字段定义完整,含字段类型、约束、示例
3. **错误响应标准化**: 所有错误响应使用 `ErrorResponse` schema
4. **认证分离**: 不同 API 使用不同认证(ApiKey/Bearer/OAuth2)
5. **示例完整**: 每个端点至少 1 个完整请求/响应示例

## 维护

- 契约变更需同步更新 Mock Server 实现
- Phase 4 用 VCR.py 录制真实 API 响应,与 Mock 对比验证
