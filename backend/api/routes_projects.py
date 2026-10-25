"""项目相关路由：路径校验 + 最近项目列表 + 内置样例。"""

from pathlib import Path

from fastapi import APIRouter

from models import db
from models.schemas import ValidatePathRequest, ValidatePathResponse
from services.project_service import validate_path

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/validate", response_model=ValidatePathResponse)
def validate(req: ValidatePathRequest):
    return validate_path(req.path)


@router.get("")
def list_projects():
    return {"projects": db.list_projects()}


@router.get("/demo")
async def demo_project():
    """内置烂尾样例（pocket-ledger 口袋账本）：路径 + 真实统计（TODO 数、搁置天数），供首页场景卡片同步显示。"""
    fixture = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "pocket-ledger"
    if not fixture.is_dir():
        return {"path": str(fixture), "available": False, "todo_count": None, "last_commit_days": None}

    from tools.registry import execute_tool

    todo = await execute_tool(str(fixture), "search_project", {"query": "TODO|FIXME", "regex": True})
    git = await execute_tool(str(fixture), "analyze_git_history", {})
    todo_count = (todo.get("result") or {}).get("total_matches_shown") if todo.get("ok") else None
    last_commit = (git.get("result") or {}).get("last_commit") or {}
    return {
        "path": str(fixture),
        "available": True,
        "todo_count": todo_count,
        "last_commit_days": last_commit.get("days_ago"),
    }
