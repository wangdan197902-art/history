"""Google Search Console Mock 路由"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from src.mock_server.data_loader import load_fixture

gsc_bp = Blueprint("gsc", __name__)


@gsc_bp.route("/sites/<path:site_url>/sitemaps", methods=["GET"])
def list_sitemaps(site_url: str):
    """获取 sitemap 列表"""
    return jsonify({
        "sitemap": [
            {
                "path": f"https://{site_url}/sitemap.xml",
                "lastSubmitted": datetime.now(timezone.utc).isoformat(),
                "isPending": False,
                "isSitemapsIndex": False,
                "type": "sitemap",
                "errors": "0",
                "warnings": "0",
                "contents": [
                    {"type": "web", "submitted": 109800, "indexed": 95000}
                ],
            }
        ],
        "nextPageToken": None,
    })


@gsc_bp.route("/sites/<path:site_url>/sitemaps", methods=["POST", "PUT"])
def submit_sitemap(site_url: str):
    """提交 sitemap (支持 POST/PUT)"""
    feedpath = request.args.get("feedpath")
    if not feedpath:
        # 尝试从 JSON body 获取
        data = request.get_json(silent=True) or {}
        feedpath = data.get("sitemap_url") or data.get("feedpath")
    if not feedpath:
        return jsonify({"code": "INVALID_REQUEST", "message": "Missing feedpath"}), 400
    return jsonify({"status": "submitted", "feedpath": feedpath, "site": site_url})


@gsc_bp.route("/sites/<path:site_url>/sitemaps/<path:feedpath>", methods=["DELETE"])
def delete_sitemap(site_url: str, feedpath: str):
    """删除 sitemap"""
    return "", 204


@gsc_bp.route("/sites/<path:site_url>/searchAnalytics/query", methods=["POST"])
def query_search_analytics(site_url: str):
    """查询搜索分析数据"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"code": "INVALID_REQUEST", "message": "Missing or invalid body"}), 400

    # Mock: 返回模拟的搜索分析数据
    return jsonify({
        "rows": [
            {
                "keys": ["today in history", f"https://{site_url}/zh/on-this-day/CN/07-04/"],
                "clicks": 1200,
                "impressions": 35000,
                "ctr": 0.034,
                "position": 2.5,
            },
            {
                "keys": ["历史上的今天", f"https://{site_url}/zh/on-this-day/CN/10-01/"],
                "clicks": 980,
                "impressions": 28000,
                "ctr": 0.035,
                "position": 3.1,
            },
        ]
    })
