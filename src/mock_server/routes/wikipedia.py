"""Wikipedia OnThisDay Mock 路由"""
from flask import Blueprint, jsonify, request

from src.mock_server.data_loader import load_fixture

wikipedia_bp = Blueprint("wikipedia", __name__)


@wikipedia_bp.route("/onthisday/<string:event_type>/<string:month>/<string:day>", methods=["GET"])
def get_onthisday_events(event_type: str, month: str, day: str):
    """获取某月某日的历史事件

    Args:
        event_type: all/selected/births/deaths/holidays/events
        month: 月份(01-12)
        day: 日期(01-31)
    """
    # 校验日期格式
    if not (month.isdigit() and 1 <= int(month) <= 12):
        return jsonify({"code": "INVALID_MONTH", "message": f"Invalid month: {month}"}), 400
    if not (day.isdigit() and 1 <= int(day) <= 31):
        return jsonify({"code": "INVALID_DAY", "message": f"Invalid day: {day}"}), 400

    # 默认查询 CN 地区(可由 query 参数指定)
    country = request.args.get("country", "CN")
    date_str = f"{month}-{day}"

    # 加载 fixture
    try:
        pool_data = load_fixture("wikipedia", f"{date_str}_{country}")
    except FileNotFoundError:
        return jsonify({"code": "NOT_FOUND", "message": f"No data for {date_str}_{country}"}), 404

    # 转换为 Wikipedia API 响应格式
    events = []
    for evt in pool_data.get("events", []):
        events.append({
            "text": evt.get("description", evt.get("title", "")),
            "year": evt.get("year", 2000),
            "pages": [
                {
                    "title": evt.get("title", ""),
                    "content_urls": {
                        "page": evt.get("wikipedia_url", "")
                    },
                }
            ],
            "categories": evt.get("categories", []),
        })

    response = {"events": events}
    if event_type in ("all", "selected"):
        response["selected"] = events[:1]  # 第一个作为 selected
    if event_type == "births":
        response["births"] = []
    if event_type == "deaths":
        response["deaths"] = []
    if event_type == "holidays":
        response["holidays"] = []

    return jsonify(response)
