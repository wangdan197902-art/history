"""故障注入中间件

通过环境变量控制:
  FAULT_INJECTION_ENABLED=true 开启
  FAULT_INJECTION_RATE=0.1 10% 请求注入故障
"""
import random
import time

from flask import Flask, jsonify


class FaultInjectionMiddleware:
    """故障注入 WSGI 中间件"""

    def __init__(self, app, config):
        self.app = app
        self.enabled = config.get("FAULT_INJECTION_ENABLED", False)
        self.rate = config.get("FAULT_INJECTION_RATE", 0.0)

    def __call__(self, environ, start_response):
        if not self.enabled:
            return self.app(environ, start_response)

        # 按概率注入故障
        if random.random() < self.rate:
            return self._inject_fault(environ, start_response)

        return self.app(environ, start_response)

    def _inject_fault(self, environ, start_response):
        """注入故障响应"""
        fault_type = random.choice(["500", "timeout", "429"])

        if fault_type == "500":
            status = "500 INTERNAL SERVER ERROR"
            response = jsonify({"error": "INJECTED_FAULT", "type": "server_error"})
        elif fault_type == "429":
            status = "429 TOO MANY REQUESTS"
            response = jsonify({"error": "INJECTED_FAULT", "type": "rate_limit"})
            response.headers["Retry-After"] = "60"
        else:  # timeout
            time.sleep(30)  # 模拟超时
            status = "504 GATEWAY TIMEOUT"
            response = jsonify({"error": "INJECTED_FAULT", "type": "timeout"})

        # 转换为 WSGI 响应
        from werkzeug.wrappers import Response

        wsgi_response = Response(response.get_data(), status=status, mimetype="application/json")
        return wsgi_response(environ, start_response)
