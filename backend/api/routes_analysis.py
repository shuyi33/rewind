"""分析相关路由。

Phase 1 先建立路由骨架；Agent Loop 在 Phase 4 完成后填充。
SSE 事件流 + 后台任务编排见 services/analysis_service.py。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models import db
from models.schemas import StartAnalysisRequest, StartAnalysisResponse

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analysis", response_model=StartAnalysisResponse)
async def start_analysis(req: StartAnalysisRequest):
    from services.analysis_service import start_analysis

    return await start_analysis(req.path, req.goal)


@router.get("/analysis/{report_id}/events")
async def analysis_events(report_id: str):
    from services.analysis_service import stream_events

    return await stream_events(report_id)


@router.get("/reports/{report_id}")
def get_report(report_id: str):
    report = db.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"report": report}


class UpdateGoalRequest(BaseModel):
    goal: str


@router.patch("/reports/{report_id}/goal")
def update_goal(report_id: str, req: UpdateGoalRequest):
    goal = req.goal.strip()
    if not goal or len(goal) > 500:
        raise HTTPException(status_code=400, detail="目标描述不能为空（限 500 字内）")
    if not db.get_report(report_id):
        raise HTTPException(status_code=404, detail="报告不存在")
    db.update_report_goal(report_id, goal)
    return {"ok": True, "goal": goal, "goal_source": "user"}
