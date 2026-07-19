"""Buttondown Newsletter Mock 路由"""
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from src.mock_server.data_loader import load_fixture

buttondown_bp = Blueprint("buttondown", __name__)

# 内存存储(Mock 数据)
_mock_emails = []
_mock_subscribers = []


@buttondown_bp.route("/emails", methods=["GET"])
def list_emails():
    """获取邮件列表"""
    page = int(request.args.get("page", 1))
    page_size = 20
    start = (page - 1) * page_size
    end = start + page_size
    return jsonify({
        "count": len(_mock_emails),
        "next": f"?page={page+1}" if end < len(_mock_emails) else None,
        "previous": f"?page={page-1}" if page > 1 else None,
        "results": _mock_emails[start:end],
    })


@buttondown_bp.route("/emails", methods=["POST"])
def create_email():
    """创建邮件"""
    data = request.get_json(silent=True)
    if not data or "subject" not in data or "body" not in data:
        return jsonify({"code": "INVALID_REQUEST", "message": "Missing subject or body"}), 400

    email = {
        "id": str(uuid.uuid4()),
        "subject": data["subject"],
        "body": data["body"],
        "publish_date": data.get("publish_date", datetime.now(timezone.utc).isoformat()),
        "email_type": data.get("email_type", "public"),
        "secondary_subject": data.get("secondary_subject"),
    }
    _mock_emails.append(email)
    return jsonify(email), 201


@buttondown_bp.route("/emails/<string:email_id>", methods=["GET"])
def get_email(email_id: str):
    """获取单封邮件"""
    for email in _mock_emails:
        if email["id"] == email_id:
            return jsonify(email)
    return jsonify({"code": "NOT_FOUND", "message": f"Email {email_id} not found"}), 404


@buttondown_bp.route("/subscribers", methods=["GET"])
def list_subscribers():
    """获取订阅者列表"""
    return jsonify({
        "count": len(_mock_subscribers),
        "results": _mock_subscribers,
    })


@buttondown_bp.route("/subscribers", methods=["POST"])
def create_subscriber():
    """添加订阅者"""
    data = request.get_json(silent=True)
    if not data or "email" not in data:
        return jsonify({"code": "INVALID_REQUEST", "message": "Missing email"}), 400

    email = data["email"]
    # 检查是否已订阅
    for sub in _mock_subscribers:
        if sub["email"] == email:
            return jsonify({"code": "ALREADY_SUBSCRIBED", "message": "Email already subscribed"}), 400

    subscriber = {
        "id": str(uuid.uuid4()),
        "email": email,
        "creation_date": datetime.now(timezone.utc).isoformat(),
        "ref": data.get("ref"),
        "tags": [],
        "unsubscribed": False,
    }
    _mock_subscribers.append(subscriber)
    return jsonify(subscriber), 201
