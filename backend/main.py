"""Rewind 后端入口。

本地运行：
    cd backend
    uvicorn main:app --reload --port 8000
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes_analysis import router as analysis_router
from api.routes_projects import router as projects_router
from config import llm_configured, settings
from models import db

app = FastAPI(title="Rewind", version="0.1.0",
              description="Project Recovery Agent — 重新捡起烂尾项目的诊断工具")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(analysis_router)


@app.get("/api/health")
def health():
    return {"ok": True, "llm_configured": llm_configured(), "mock": settings.MOCK_LLM}


# ---------------------------------------------------------------- 静态托管（单端口部署形态）
# npm run build 产出 frontend/dist 后，后端可同时 serve 前端与 API（同源，无 CORS）。
# 本地开发时（dist 不存在）该段自动跳过，仍走 Vite 5173 + 代理模式。

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    _assets_dir = FRONTEND_DIST / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/favicon.svg", include_in_schema=False)
    def favicon():
        f = FRONTEND_DIST / "favicon.svg"
        return FileResponse(f) if f.exists() else FileResponse(_assets_dir.parent / "favicon.svg")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        """前端 SPA 路由回退（/scan/:id、/report/:id 等）。API 未匹配的路径返回 404 JSON。"""
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
        target = FRONTEND_DIST / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()
    mode = "MOCK" if settings.MOCK_LLM else ("real LLM" if settings.LLM_API_KEY else "未配置 ⚠")
    print(f"[rewind] db ready: {settings.DB_PATH}")
    print(f"[rewind] llm: {settings.LLM_MODEL} @ {settings.LLM_BASE_URL} ({mode})")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
