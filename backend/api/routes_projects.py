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
def demo_project():
    """内置烂尾样例（pocket-ledger 口袋账本）的绝对路径，供首页「诊断样例」卡片直连扫描。"""
    fixture = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "pocket-ledger"
    return {"path": str(fixture), "available": fixture.is_dir()}
