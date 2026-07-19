"""Google Gemini Mock 路由"""
import json

from flask import Blueprint, jsonify, request

from src.mock_server.data_loader import load_fixture

gemini_bp = Blueprint("gemini", __name__)


@gemini_bp.route("/models/<string:model>:generateContent", methods=["POST"])
def generate_content(model: str):
    """Mock Gemini generateContent API"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"code": "INVALID_REQUEST", "message": "Missing or invalid JSON body"}), 400

    # 从请求中提取 prompt
    contents = data.get("contents")
    if not contents:
        return jsonify({"code": "INVALID_REQUEST", "message": "Missing contents"}), 400

    prompt_text = ""
    if contents:
        parts = contents[0].get("parts", [])
        for part in parts:
            if "text" in part:
                prompt_text += part["text"]

    # 根据内容判断场景
    scenario = "illustrate"
    if "审核" in prompt_text or "audit" in prompt_text.lower():
        scenario = "audit"
    elif "翻译" in prompt_text or "translate" in prompt_text.lower():
        scenario = "translate"

    try:
        fixture = load_fixture("gemini", scenario)
    except FileNotFoundError:
        # 降级: 返回 Mock 配图描述
        return jsonify({
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "image_url": f"https://mock.example.com/image_{hash(prompt_text) & 0xFFFF}.jpg",
                                    "image_alt": prompt_text[:50] if prompt_text else "Mock image",
                                    "image_caption": f"Mock caption for: {prompt_text[:30]}...",
                                    "search_keywords": ["mock", "history"],
                                }, ensure_ascii=False)
                            }
                        ]
                    },
                    "finishReason": "STOP",
                    "index": 0,
                }
            ],
            "usageMetadata": {
                "promptTokenCount": len(prompt_text) // 4 + 10,
                "candidatesTokenCount": 80,
                "totalTokenCount": len(prompt_text) // 4 + 90,
            },
        })

    return jsonify(fixture)
