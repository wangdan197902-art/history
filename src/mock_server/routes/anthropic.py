"""Anthropic Claude Mock 路由"""
from flask import Blueprint, jsonify, request

from src.mock_server.data_loader import load_fixture

anthropic_bp = Blueprint("anthropic", __name__)


@anthropic_bp.route("/messages", methods=["POST"])
def create_message():
    """Mock Claude Messages API

    请求体示例:
        {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2048,
            "system": "...",
            "messages": [{"role": "user", "content": "..."}]
        }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"code": "INVALID_REQUEST", "message": "Missing or invalid JSON body"}), 400

    model = data.get("model", "claude-3-5-sonnet-20241022")
    messages = data.get("messages", [])
    if not messages:
        return jsonify({"code": "INVALID_REQUEST", "message": "Missing messages"}), 400

    # 从最后一条 user 消息中提取场景
    user_content = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_content = msg.get("content", "")
            break

    # 尝试加载场景 fixture(如 "regionalize_CN" / "regionalize")
    scenario = "regionalize"
    if "中国" in user_content or "CN" in user_content:
        scenario = "regionalize_CN"
    elif "美国" in user_content or "US" in user_content:
        scenario = "regionalize_US"

    try:
        fixture = load_fixture("anthropic", scenario)
    except FileNotFoundError:
        # 降级: 返回基于用户输入的 Mock 响应
        return jsonify({
            "id": "msg_mock_" + str(hash(user_content))[:8],
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [
                {
                    "type": "text",
                    "text": f"Mock 地区化重写: {user_content[:100]}... (Mock Claude 响应)",
                }
            ],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": len(user_content) // 4 + 10, "output_tokens": 80},
        })

    # 返回 fixture(可能需要更新 model 字段)
    if "model" in fixture:
        fixture["model"] = model
    return jsonify(fixture)
