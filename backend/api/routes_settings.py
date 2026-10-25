"""设置路由：LLM 配置读写（写入 backend/.env 并热加载，无需重启服务）。

GET  /api/settings —— 当前配置（Key 只返回掩码，永不回传明文）
POST /api/settings —— 保存：更新 .env 对应键 + 同步环境变量 + 热加载
"""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import config as config_module
from config import reload_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


class LLMSettingsRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = None  # None 或空字符串 = 保持不变
    model: str | None = None
    mock: bool | None = None


def _masked(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 10:
        return "****"
    return f"{key[:6]}****{key[-4:]}"


def _current() -> dict:
    s = config_module.settings
    return {
        "base_url": s.LLM_BASE_URL,
        "model": s.LLM_MODEL,
        "mock": s.MOCK_LLM,
        "has_key": bool(s.LLM_API_KEY),
        "api_key_masked": _masked(s.LLM_API_KEY),
    }


def _write_env(updates: dict[str, str]) -> None:
    """保留 .env 其余行（含注释），更新指定键，不存在则追加。"""
    lines: list[str] = []
    if _ENV_PATH.exists():
        for ln in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = ln.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                if stripped.split("=", 1)[0].strip() in updates:
                    continue
            lines.append(ln)
    lines.extend(f"{k}={v}" for k, v in updates.items())
    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


@router.get("")
def get_settings():
    return _current()


@router.post("")
def save_settings(req: LLMSettingsRequest):
    updates: dict[str, str] = {}
    if req.base_url and req.base_url.strip():
        updates["LLM_BASE_URL"] = req.base_url.strip()
    if req.model and req.model.strip():
        updates["LLM_MODEL"] = req.model.strip()
    if req.api_key and req.api_key.strip():
        updates["LLM_API_KEY"] = req.api_key.strip()
    if req.mock is not None:
        updates["REWIND_MOCK_LLM"] = "1" if req.mock else "0"
    if not updates:
        raise HTTPException(status_code=400, detail="没有需要保存的设置")

    _write_env(updates)
    for k, v in updates.items():
        os.environ[k] = v
    reload_settings()
    return _current()


class LLMTestRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = None  # 空 = 使用已保存的 Key
    model: str | None = None


@router.post("/test")
async def test_llm(req: LLMTestRequest):
    """连通性测试：用表单当前值（未填的项回退已保存配置）发一条 1-token 迷你请求。

    不用 models.list —— 部分服务（如 OpenRouter）该端点不校验 Key，假 Key 也会通过。
    """
    s = config_module.settings
    base = (req.base_url or s.LLM_BASE_URL).strip().rstrip("/")
    key = (req.api_key or "").strip() or s.LLM_API_KEY
    model = (req.model or s.LLM_MODEL).strip()
    if not key:
        return {"ok": False, "detail": "没有可用的 API Key"}
    if not base:
        return {"ok": False, "detail": "没有 API 地址"}
    if not model:
        return {"ok": False, "detail": "没有模型名"}

    from openai import AsyncOpenAI

    try:
        client = AsyncOpenAI(base_url=base, api_key=key, timeout=20)
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        n = len(resp.choices) if resp.choices else 0
        return {"ok": True, "detail": f"连接成功：{model} 可用（返回 {n} 条候选）"}
    except Exception as e:  # noqa: BLE001 — 网络/鉴权/模型名错误统一回报
        return {"ok": False, "detail": f"连接失败：{e}"}
