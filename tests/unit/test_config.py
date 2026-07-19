"""配置模块测试"""
import pytest

from src.config.base import Settings, get_settings
from src.config.local import LocalSettings
from src.config.production import ProductionSettings


class TestSettings:
    """基础 Settings 测试"""

    def test_default_env(self):
        """默认 ENV 为 local"""
        s = Settings()
        assert s.ENV == "local"

    def test_default_providers_are_mock(self):
        """默认所有 provider 为 mock"""
        s = Settings()
        assert s.WIKIPEDIA_PROVIDER == "mock"
        assert s.ANTHROPIC_PROVIDER == "mock"
        assert s.OPENAI_PROVIDER == "mock"
        assert s.GEMINI_PROVIDER == "mock"
        assert s.BUTTONDOWN_PROVIDER == "mock"
        assert s.GSC_PROVIDER == "mock"

    def test_countries_list(self):
        """地区列表 30 个"""
        s = Settings()
        assert len(s.countries_list) == 30
        assert "CN" in s.countries_list
        assert "US" in s.countries_list

    def test_languages_list(self):
        """语种列表 10 个"""
        s = Settings()
        assert len(s.languages_list) == 10
        assert "zh" in s.languages_list
        assert "ar" in s.languages_list

    def test_mock_server_base_url(self):
        """Mock Server URL"""
        s = Settings()
        assert s.mock_server_base_url == "http://127.0.0.1:8765"

    def test_is_local_is_production(self):
        s = Settings()
        assert s.is_local is True
        assert s.is_production is False

    def test_get_settings_singleton(self):
        """get_settings 返回单例"""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


class TestSettingsValidation:
    """生产环境校验"""

    def test_validate_for_production_local(self):
        """local 模式下 validate_for_production 返回空列表"""
        s = Settings(ENV="local")
        assert s.validate_for_production() == []

    def test_validate_for_production_missing_keys(self):
        """production 模式下缺失 API key"""
        s = Settings(ENV="production")
        missing = s.validate_for_production()
        assert "ANTHROPIC_API_KEY" in missing
        assert "OPENAI_API_KEY" in missing
        assert "GEMINI_API_KEY" in missing

    def test_validate_for_production_with_keys(self):
        """production 模式下配置了 API key"""
        s = Settings(
            ENV="production",
            ANTHROPIC_API_KEY="sk-ant-test",
            OPENAI_API_KEY="sk-test",
            GEMINI_API_KEY="gemini-test",
        )
        assert s.validate_for_production() == []


class TestLocalSettings:
    """LocalSettings 测试"""

    def test_local_settings_force_mock(self):
        """LocalSettings 强制 mock"""
        s = LocalSettings()
        assert s.ENV == "local"
        assert s.is_local is True
        assert s.WIKIPEDIA_PROVIDER == "mock"
        assert s.ANTHROPIC_PROVIDER == "mock"

    def test_local_settings_ignore_real_env(self):
        """即使 ENV=production 也强制 mock provider"""
        s = LocalSettings(ENV="production")
        # LocalSettings 仍可设为 production ENV(不强制),但 provider 仍为 mock
        assert s.WIKIPEDIA_PROVIDER == "mock"


class TestProductionSettings:
    """ProductionSettings 测试"""

    def test_production_settings_default_real(self):
        """ProductionSettings 默认 real"""
        s = ProductionSettings()
        assert s.ENV == "production"
        assert s.is_production is True
        assert s.WIKIPEDIA_PROVIDER == "real"
        assert s.ANTHROPIC_PROVIDER == "real"
        assert s.OPENAI_PROVIDER == "real"
        assert s.GEMINI_PROVIDER == "real"
        assert s.BUTTONDOWN_PROVIDER == "real"
