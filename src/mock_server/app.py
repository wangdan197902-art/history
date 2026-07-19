"""Flask Mock Server 主入口

启动方式:
    python -m src.mock_server.app
    或
    make mock-server

端口: 8765
"""
from flask import Flask, jsonify

from src.mock_server.data_loader import load_fixture
from src.mock_server.routes.wikipedia import wikipedia_bp
from src.mock_server.routes.anthropic import anthropic_bp
from src.mock_server.routes.openai import openai_bp
from src.mock_server.routes.gemini import gemini_bp
from src.mock_server.routes.buttondown import buttondown_bp
from src.mock_server.routes.gsc import gsc_bp
from src.mock_server.middleware import FaultInjectionMiddleware


def create_app(config: dict | None = None) -> Flask:
    """创建 Flask 应用

    Args:
        config: 可选配置字典

    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)

    # 加载配置
    if config:
        app.config.update(config)

    # 默认配置
    app.config.setdefault("FAULT_INJECTION_ENABLED", False)
    app.config.setdefault("FAULT_INJECTION_RATE", 0.0)

    # 注册故障注入中间件
    app.wsgi_app = FaultInjectionMiddleware(app.wsgi_app, app.config)

    # 注册 Blueprint
    app.register_blueprint(wikipedia_bp, url_prefix="/wikipedia")
    app.register_blueprint(anthropic_bp, url_prefix="/anthropic")
    app.register_blueprint(openai_bp, url_prefix="/openai")
    app.register_blueprint(gemini_bp, url_prefix="/gemini")
    app.register_blueprint(buttondown_bp, url_prefix="/buttondown")
    app.register_blueprint(gsc_bp, url_prefix="/gsc")

    # 健康检查端点
    @app.route("/health")
    def health_check():
        return jsonify({"status": "ok", "service": "mock-server", "version": "0.1.0"})

    # 根路径
    @app.route("/")
    def index():
        return jsonify({
            "service": "Today in History Mock Server",
            "version": "0.1.0",
            "endpoints": [
                "/wikipedia/onthisday/{type}/{month}/{day}",
                "/anthropic/messages",
                "/openai/chat/completions",
                "/gemini/models/{model}:generateContent",
                "/buttondown/emails",
                "/buttondown/subscribers",
                "/gsc/sites/{siteUrl}/sitemaps",
                "/health",
            ],
        })

    return app


if __name__ == "__main__":
    app = create_app()
    port = 8765
    print(f"Mock Server 启动中... 端口: {port}")
    print(f"健康检查: http://127.0.0.1:{port}/health")
    app.run(host="127.0.0.1", port=port, debug=True)
