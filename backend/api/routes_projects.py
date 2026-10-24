"""项目相关路由：路径校验 + 最近项目列表。"""

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
