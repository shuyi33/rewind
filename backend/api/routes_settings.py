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


def _find_bad_char(value: str) -> tuple[int, str] | None:
    """定位第一个非 ASCII 字符（粘贴混入符号/中文时的友好报错）。"""
    for i, ch in enumerate(value):
        if ord(ch) > 127:
            return i, ch
    return None


@router.post("/test")
async def test_llm(req: LLMTestRequest):
    """连通性测试：用表单当前值（未填的项回退已保存配置）发一条 1-token 迷你请求。

    不用 models.list —— 部分服务（如 OpenRouter）该端点不校验 Key，假 Key 也会通过。
    """
    s = config_module.settings
    base = (req.base_url or s.LLM_BASE_URL).strip().rstrip("/")
    key = (req.api_key or "").strip() or s.LLM_API_KEY
    model = (req.model or s.LLM_MODEL).strip()
    for name, value in (("API Key", key), ("API 地址", base)):
        bad = _find_bad_char(value)
        if bad:
            pos, ch = bad
            return {"ok": False, "detail": f"{name}的第 {pos + 1} 个字符是「{ch}」——粘贴时混入了符号，"
                                           f"请清空后重新只复制 Key 本身（仅含字母、数字、连字符）"}
    if not key:
        return {"ok": False, "detail": "没有可用的 API Key"}
    if not base:
        return {"ok": False, "detail": "没有 API 地址"}
    if not model:
        return {"ok": False, "detail": "没有模型名"}

    from openai import AsyncOpenAI

    # 诊断信息：Key 到达后端时的长度与前缀（不回传内容本身）
    key_len = len(key)
    prefix_ok = key.startswith("sk-or-v1-") if "openrouter" in base else key.startswith("sk-")
    diag = f"（后端收到 {key_len} 字符，前缀{'正确' if prefix_ok else '异常'}）"

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
        msg = str(e)
        # OpenRouter 对无效/不完整 Key 报 "Missing Authentication header"，极具误导性
        if "401" in msg or "Authentication" in msg or "User not found" in msg:
            if "openrouter" in base:
                if key_len >= 60 and prefix_ok:
                    return {"ok": False, "detail": f"Key 已完整送达后端{diag}，但被 OpenRouter 拒绝 —— "
                                   "这不再是复制问题，请依次检查：① openrouter.ai 账户邮箱是否已验证；"
                                   "② Keys 页面里这个 Key 的状态是否为 Active（未吊销/未删除）；"
                                   "③ 账户余额是否可用（deepseek/deepseek-chat 需要充值额度）"}
                return {"ok": False, "detail": f"Key 未完整到达后端{diag} —— OpenRouter 的 Key 约 70+ 字符、"
                                               "以 sk-or-v1- 开头；请点输入框右侧「眼睛」核对明文后再测一次"}
            return {"ok": False, "detail": f"Key 无效或未授权（401）{diag} —— 请检查 Key 是否属于该服务商"}
        return {"ok": False, "detail": f"连接失败{diag}：{msg}"}
