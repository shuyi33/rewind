"""环境变量配置。

所有配置只来自环境变量（或 backend/.env），代码零硬编码。
真实环境变量优先于 .env 文件中的值。
"""

import os
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> None:
    """极简 .env 加载器：一行一项 KEY=VALUE，# 开头为注释。"""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(_BACKEND_DIR / ".env")


def _env_str(key: str, default: str) -> str:
    value = os.environ.get(key, "").strip()
    return value or default


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _env_bool(key: str) -> bool:
    return os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on")


class _Settings:
    def __init__(self):
        # LLM（任何 OpenAI-compatible 服务）
        self.LLM_BASE_URL = _env_str("LLM_BASE_URL", "https://api.openai.com/v1")
        self.LLM_API_KEY = _env_str("LLM_API_KEY", "")
        self.LLM_MODEL = _env_str("LLM_MODEL", "gpt-4o")
        self.MOCK_LLM = _env_bool("REWIND_MOCK_LLM")

        # Agent Loop 安全上限
        self.MAX_AGENT_STEPS = _env_int("REWIND_MAX_AGENT_STEPS", 30)

        # SQLite 数据目录
        self.DATA_DIR = _BACKEND_DIR / "data"
        self.DB_PATH = self.DATA_DIR / "rewind.db"

        # run_project_check 安全限制
        self.CHECK_TIMEOUT_SECONDS = _env_int("REWIND_CHECK_TIMEOUT", 120)
        self.CHECK_OUTPUT_LIMIT = _env_int("REWIND_CHECK_OUTPUT_LIMIT", 4000)


settings = _Settings()


def reload_settings() -> None:
    """从环境变量重读 LLM 配置（设置页保存后热加载，无需重启服务）。"""
    s = settings
    s.LLM_BASE_URL = _env_str("LLM_BASE_URL", s.LLM_BASE_URL)
    s.LLM_API_KEY = _env_str("LLM_API_KEY", s.LLM_API_KEY)
    s.LLM_MODEL = _env_str("LLM_MODEL", s.LLM_MODEL)
    s.MOCK_LLM = _env_bool("REWIND_MOCK_LLM")


def llm_configured() -> bool:
    """是否具备 LLM 能力（真实 Key 或 Mock 引擎）。"""
    return settings.MOCK_LLM or bool(settings.LLM_API_KEY)
