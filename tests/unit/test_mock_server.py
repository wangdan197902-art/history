"""Mock Server 单元测试"""
import pytest
from src.mock_server.app import create_app


@pytest.fixture
def client():
    """Flask 测试客户端"""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestHealthCheck:
    """健康检查测试"""

    def test_health(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert data["service"] == "mock-server"

    def test_index(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.get_json()
        assert "service" in data
        assert "endpoints" in data


class TestWikipediaRoutes:
    """Wikipedia 路由测试"""

    def test_get_onthisday_events(self, client):
        """测试获取事件列表"""
        response = client.get("/wikipedia/onthisday/all/07/04?country=CN")
        assert response.status_code == 200
        data = response.get_json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_invalid_month(self, client):
        """测试无效月份"""
        response = client.get("/wikipedia/onthisday/all/13/01")
        assert response.status_code == 400

    def test_invalid_day(self, client):
        """测试无效日期"""
        response = client.get("/wikipedia/onthisday/all/01/32")
        assert response.status_code == 400


class TestAnthropicRoutes:
    """Anthropic 路由测试"""

    def test_create_message(self, client):
        """测试创建消息"""
        response = client.post(
            "/anthropic/messages",
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": "事件:1921年中国共产党成立\n地区:中国\n请重写:"}],
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "content" in data
        assert data["role"] == "assistant"

    def test_missing_body(self, client):
        """测试缺失请求体"""
        response = client.post("/anthropic/messages")
        assert response.status_code == 400


class TestOpenAIRoutes:
    """OpenAI 路由测试"""

    def test_chat_completions(self, client):
        """测试聊天补全"""
        response = client.post(
            "/openai/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "你是翻译"},
                    {"role": "user", "content": "原文:中国共产党成立\n目标语言:en\n请翻译:"},
                ],
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "choices" in data


class TestGeminiRoutes:
    """Gemini 路由测试"""

    def test_generate_content(self, client):
        """测试内容生成"""
        response = client.post(
            "/gemini/models/gemini-1.5-flash:generateContent",
            json={
                "contents": [{"parts": [{"text": "为以下事件生成图片:1921年中国共产党成立"}]}],
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "candidates" in data


class TestButtondownRoutes:
    """Buttondown 路由测试"""

    def test_create_email(self, client):
        """测试创建邮件"""
        response = client.post(
            "/buttondown/emails",
            json={"subject": "Test Email", "body": "Test body"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert "id" in data

    def test_list_emails(self, client):
        """测试获取邮件列表"""
        # 先创建一封
        client.post("/buttondown/emails", json={"subject": "Test", "body": "Body"})
        response = client.get("/buttondown/emails")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] >= 1

    def test_create_subscriber(self, client):
        """测试添加订阅者"""
        response = client.post(
            "/buttondown/subscribers",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["email"] == "test@example.com"


class TestGSCRoutes:
    """GSC 路由测试"""

    def test_list_sitemaps(self, client):
        """测试获取 sitemap 列表"""
        response = client.get("/gsc/sites/https%3A%2F%2Fexample.com%2F/sitemaps")
        assert response.status_code == 200
        data = response.get_json()
        assert "sitemap" in data

    def test_search_analytics(self, client):
        """测试搜索分析查询"""
        response = client.post(
            "/gsc/sites/https%3A%2F%2Fexample.com%2F/searchAnalytics/query",
            json={"startDate": "2026-06-01", "endDate": "2026-06-30"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "rows" in data
