"""配置基类 - pydantic-settings 双轨制

通过 ENV 环境变量切换:
  ENV=local       → Mock 模式(默认)
  ENV=production  → Real 模式(Phase 4)
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置 - 通过 .env 文件加载"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # === 环境标识 ===
    ENV: str = "local"  # local | production

    # === Mock Server ===
    MOCK_SERVER_HOST: str = "127.0.0.1"
    MOCK_SERVER_PORT: int = 8765

    # === Provider 切换 ===
    WIKIPEDIA_PROVIDER: str = "mock"  # mock | real
    ANTHROPIC_PROVIDER: str = "mock"
    OPENAI_PROVIDER: str = "mock"
    GEMINI_PROVIDER: str = "mock"
    BUTTONDOWN_PROVIDER: str = "mock"
    GSC_PROVIDER: str = "mock"

    # === 管道并发 ===
    ASYNCIO_SEMAPHORE: int = 16
    DISKCACHE_DIR: str = ".cache/pipeline"

    # === Hugo ===
    HUGO_CACHE_DIR: str = "~/.cache/hugo-today-in-history"

    # === 内容范围 ===
    COUNTRIES: str = "CN,US,JP,KR,UK,DE,FR,RU,BR,IN,AU,CA,IT,ES,MX,ID,TH,VN,SG,MY,PH,SA,AE,EG,ZA,NG,TR,PL,NL,SE"
    LANGUAGES: str = "zh,en,ja,ko,es,fr,de,pt,ru,ar,it,nl,pl,tr,vi,th,id,sv,cs,da"

    # === 故障注入测试 ===
    FAULT_INJECTION_ENABLED: bool = False
    FAULT_INJECTION_RATE: float = 0.0

    # === 生产环境(Phase 4) ===
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    BUTTONDOWN_API_KEY: Optional[str] = None
    WIKIPEDIA_USER_AGENT: Optional[str] = None
    GSC_SERVICE_ACCOUNT_JSON: Optional[str] = None

    @property
    def countries_list(self) -> list[str]:
        """地区列表"""
        return [c.strip() for c in self.COUNTRIES.split(",") if c.strip()]

    @property
    def languages_list(self) -> list[str]:
        """语种列表"""
        return [l.strip() for l in self.LANGUAGES.split(",") if l.strip()]

    @property
    def mock_server_base_url(self) -> str:
        """Mock Server 基础 URL"""
        return f"http://{self.MOCK_SERVER_HOST}:{self.MOCK_SERVER_PORT}"

    @property
    def is_local(self) -> bool:
        """是否本地环境"""
        return self.ENV == "local"

    @property
    def is_production(self) -> bool:
        """是否生产环境"""
        return self.ENV == "production"

    def validate_for_production(self) -> list[str]:
        """生产环境配置校验,返回缺失配置列表"""
        missing = []
        if self.is_production:
            if not self.ANTHROPIC_API_KEY:
                missing.append("ANTHROPIC_API_KEY")
            if not self.OPENAI_API_KEY:
                missing.append("OPENAI_API_KEY")
            if not self.GEMINI_API_KEY:
                missing.append("GEMINI_API_KEY")
        return missing


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置(单例)"""
    return Settings()
