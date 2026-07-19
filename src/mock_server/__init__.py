"""Flask Mock Server 包 - 本地全链路模拟环境

端口: 8765
启动: python -m src.mock_server.app

提供 6 个外部 API 的 Mock 实现:
  /wikipedia/*     - Wikipedia OnThisDay API
  /anthropic/*     - Anthropic Claude Messages API
  /openai/*        - OpenAI Chat Completions API
  /gemini/*        - Google Gemini API
  /buttondown/*    - Buttondown Newsletter API
  /gsc/*           - Google Search Console API
"""
from src.mock_server.app import create_app

__all__ = ["create_app"]
