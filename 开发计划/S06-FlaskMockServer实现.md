# S06 - Flask Mock Server 实现

> 阶段：Phase 1 - Mock 体系建设
> 人天：3 | 依赖：S03、S04、S05 | 前置：Provider 接口已定义

---

## 一、步骤概述

实现 Flask Mock Server（端口 8765），统一响应 6 个外部 API（Wikipedia / Anthropic / OpenAI / Gemini / Buttondown / GSC），从 fixture 加载 Mock 数据，支持故障注入（500/超时/限流/字段缺失）用于增强包 2。

## 二、任务清单

### 2.1 Flask 应用入口

文件：`src/mock_server/app.py`

```python
from flask import Flask, jsonify, request, Response
from src.mock_server.routes.wikipedia import wikipedia_bp
from src.mock_server.routes.anthropic import anthropic_bp
from src.mock_server.routes.openai import openai_bp
from src.mock_server.routes.gemini import gemini_bp
from src.mock_server.routes.buttondown import buttondown_bp
from src.mock_server.routes.gsc import gsc_bp
from src.mock_server.middleware import FaultInjectionMiddleware

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False

    # 故障注入中间件（增强包 2 用）
    app.wsgi_app = FaultInjectionMiddleware(app.wsgi_app)

    # 注册 Blueprint
    app.register_blueprint(wikipedia_bp, url_prefix="/wikipedia")
    app.register_blueprint(anthropic_bp, url_prefix="/anthropic")
    app.register_blueprint(openai_bp, url_prefix="/openai")
    app.register_blueprint(gemini_bp, url_prefix="/gemini")
    app.register_blueprint(buttondown_bp, url_prefix="/buttondown")
    app.register_blueprint(gsc_bp, url_prefix="/gsc")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "mock-server"})

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=8765, debug=True)
```

### 2.2 Mock 数据加载器

文件：`src/mock_server/data_loader.py`

```python
import json
from pathlib import Path
from typing import Any

FIXTURE_BASE = Path("tests/fixtures/mock_responses")

def load_fixture(service: str, scenario: str) -> Any:
    """加载 Mock fixture
    service: wikipedia | anthropic | openai | gemini | buttondown | gsc
    scenario: 文件名（不含扩展名）
    """
    fixture_path = FIXTURE_BASE / service / f"{scenario}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture 不存在: {fixture_path}")
    return json.loads(fixture_path.read_text(encoding="utf-8"))

def list_fixtures(service: str) -> list[str]:
    """列出某服务的所有 fixture"""
    service_dir = FIXTURE_BASE / service
    if not service_dir.exists():
        return []
    return [f.stem for f in service_dir.glob("*.json")]
```

### 2.3 Wikipedia 路由

文件：`src/mock_server/routes/wikipedia.py`

```python
from flask import Blueprint, jsonify, request
from src.mock_server.data_loader import load_fixture

wikipedia_bp = Blueprint("wikipedia", __name__)

@wikipedia_bp.route("/onthisday/events/<month>/<day>", methods=["GET"])
def get_events(month: str, day: str):
    """Mock Wikipedia OnThisDay API
    URL: /wikipedia/onthisday/events/{MM}/{DD}
    """
    country = request.args.get("country", "CN")
    scenario = f"{month}-{day}_{country}"
    try:
        data = load_fixture("wikipedia", scenario)
        return jsonify(data)
    except FileNotFoundError:
        # 返回空事件池
        return jsonify({
            "events": [],
            "births": [],
            "deaths": [],
            "holidays": []
        }), 200
```

### 2.4 Anthropic 路由（地区化重写）

文件：`src/mock_server/routes/anthropic.py`

```python
from flask import Blueprint, jsonify, request
import time

anthropic_bp = Blueprint("anthropic", __name__)

@anthropic_bp.route("/messages", methods=["POST"])
def messages():
    """Mock Anthropic Claude Messages API"""
    body = request.json
    # 模拟思考延迟
    time.sleep(0.3)
    # 从请求中提取关键信息，返回 Mock 地区化内容
    user_msg = body.get("messages", [{}])[-1].get("content", "")
    return jsonify({
        "content": [{
            "type": "text",
            "text": f"【Mock 地区化内容】{user_msg[:100]}..."
        }],
        "usage": {"input_tokens": 100, "output_tokens": 200}
    })
```

### 2.5 OpenAI 路由（翻译）

文件：`src/mock_server/routes/openai.py`

```python
from flask import Blueprint, jsonify, request
import time

openai_bp = Blueprint("openai", __name__)

@openai_bp.route("/chat/completions", methods=["POST"])
def chat_completions():
    """Mock OpenAI Chat Completions API"""
    body = request.json
    time.sleep(0.2)
    user_msg = body.get("messages", [{}])[-1].get("content", "")
    return jsonify({
        "choices": [{
            "message": {
                "role": "assistant",
                "content": f"【Mock 翻译】{user_msg[:100]}..."
            }
        }],
        "usage": {"prompt_tokens": 50, "completion_tokens": 100}
    })
```

### 2.6 Gemini 路由（配图）

文件：`src/mock_server/routes/gemini.py`

```python
from flask import Blueprint, jsonify, request
import time

gemini_bp = Blueprint("gemini", __name__)

@gemini_bp.route("/models/<model>:generateContent", methods=["POST"])
def generate_content(model: str):
    """Mock Gemini API"""
    time.sleep(0.25)
    return jsonify({
        "candidates": [{
            "content": {
                "parts": [{
                    "text": "https://mock-image.example.com/image_001.webp"
                }]
            }
        }]
    })
```

### 2.7 Buttondown 与 GSC 路由

文件：`src/mock_server/routes/buttondown.py` / `src/mock_server/routes/gsc.py`

```python
# Buttondown: 邮件订阅 API（返回 mock 邮件 ID）
# GSC: sitemap 提交（返回 mock 成功响应）
```

### 2.8 故障注入中间件（增强包 2）

文件：`src/mock_server/middleware.py`

```python
class FaultInjectionMiddleware:
    """故障注入中间件（增强包 2 启用）"""
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # 检查查询参数 ?fail=500 / ?delay=5000 / ?rate_limit=429
        qs = environ.get("QUERY_STRING", "")
        if "fail=500" in qs:
            start_response("500 Internal Server Error", [("Content-Type", "application/json")])
            return [b'{"error": "injected 500"}']
        if "rate_limit=429" in qs:
            start_response("429 Too Many Requests", [("Content-Type", "application/json")])
            return [b'{"error": "rate limited"}']
        return self.app(environ, start_response)
```

## 三、实施步骤

1. 编写 `src/mock_server/app.py`（Flask 入口）
2. 编写 `src/mock_server/data_loader.py`（fixture 加载器）
3. 创建 `src/mock_server/routes/` 目录
4. 编写 6 个路由 Blueprint（wikipedia/anthropic/openai/gemini/buttondown/gsc）
5. 编写 `src/mock_server/middleware.py`（故障注入）
6. 编写 `scripts/start_mock_server.sh` 一键启动
7. 用 `wrk` 压测验证性能

## 四、验收命令

```bash
. .venv/bin/activate
python -m src.mock_server.app &
sleep 2

# 健康检查
curl http://127.0.0.1:8765/health
# 期望 {"status": "ok"}

# Wikipedia Mock
curl http://127.0.0.1:8765/wikipedia/onthisday/events/07/04?country=CN
# 期望返回 Mock 事件池

# Anthropic Mock
curl -X POST http://127.0.0.1:8765/anthropic/messages \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-3-5-sonnet","max_tokens":1024,"messages":[{"role":"user","content":"test"}]}'

# 性能压测
wrk -t4 -c50 -d10s http://127.0.0.1:8765/health
# 期望 P99 < 200ms，零错误
```

## 五、依赖关系

- **前置依赖**：S03（fixture）、S04（契约）、S05（Provider 接口）
- **后续依赖**：S07（数据加载器完善）、S08（Provider 切换器）、S09-S14（管道使用）
- **阻塞关系**：Mock Server 未启动则管道无法运行

## 六、风险提示

| 风险 | 等级 | 应对 |
|------|------|------|
| Flask 单线程并发不足 | 高 | 生产用 gunicorn -w 4，本地开发足够 |
| fixture 路径错误 | 中 | data_loader 抛 FileNotFoundError |
| 端口 8765 被占用 | 低 | 启动前 `lsof -i:8765` 检查 |
| 故障注入中间件误触发 | 中 | 仅在查询参数显式指定时触发 |

## 七、性能预算

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| Mock API 响应延迟 | < 200ms | `requests.elapsed` |
| Mock API 吞吐量 | ≥ 100 req/s | `wrk -t4 -c50` |
| 健康检查响应 | < 50ms | `curl -w "%{time_total}"` |
| 启动时间 | < 3s | `time python -m src.mock_server.app` |

## 八、测试要求

- `/health` 端点返回 200
- 6 个 API 端点全部可访问
- fixture 数据正确加载
- wrk 压测 P99 < 200ms，零错误
