"""OpenAI Chat Completions Mock 路由"""
from flask import Blueprint, jsonify, request

from src.mock_server.data_loader import load_fixture

openai_bp = Blueprint("openai", __name__)


@openai_bp.route("/chat/completions", methods=["POST"])
def create_chat_completion():
    """Mock OpenAI Chat Completions API"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"code": "INVALID_REQUEST", "message": "Missing or invalid JSON body"}), 400

    model = data.get("model", "gpt-4o")
    messages = data.get("messages", [])
    if not messages:
        return jsonify({"code": "INVALID_REQUEST", "message": "Missing messages"}), 400

    # 从最后一条 user 消息中提取目标语言
    user_content = ""
    target_lang = "en"
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_content = msg.get("content", "")
            # 简单解析目标语言
            for lang in ["zh", "en", "ja", "ko", "es", "fr", "de", "pt", "ru", "ar",
                          "it", "nl", "pl", "tr", "vi", "th", "id", "sv", "cs", "da"]:
                if f"目标语言:{lang}" in user_content or f"target language: {lang}" in user_content.lower():
                    target_lang = lang
                    break
            break

    # 尝试加载翻译 fixture
    scenario = f"translate_{target_lang}"
    try:
        fixture = load_fixture("openai", scenario)
    except FileNotFoundError:
        # 降级: 返回基于用户输入的 Mock 翻译
        return jsonify({
            "id": "chatcmpl-mock_" + str(hash(user_content))[:8],
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"[Mock {target_lang}] {user_content[:80]}...",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(user_content) // 4 + 10,
                "completion_tokens": 30,
                "total_tokens": len(user_content) // 4 + 40,
            },
        })

    if "model" in fixture:
        fixture["model"] = model
    return jsonify(fixture)
