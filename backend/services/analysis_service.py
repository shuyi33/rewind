"""分析编排服务：启动 Agent、广播事件（SSE）、落库报告。

事件模型（与前端 AgentEvent 类型一一对应）：
  phase      —— 进入新阶段（真实进度，非假百分比）
  tool_call  —— Agent 决定调用某工具
  tool_result—— 工具返回（含一行摘要）
  report     —— 最终完整报告
  error/done —— 终止事件
"""

import asyncio
import json
import threading

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from agent.loop import AgentError, run_diagnosis
from models import db
from services.project_service import validate_path


class _Hub:
    """单次分析的事件总线：事件历史（重连回放）+ 多订阅者广播。"""

    def __init__(self):
        self.events: list[dict] = []
        self.subs: set[asyncio.Queue] = set()
        self.finished = False
        self.lock = threading.Lock()  # 临界区极短且无 await，线程锁即可

    def publish(self, ev: dict) -> None:
        with self.lock:
            self.events.append(ev)
            if ev.get("type") == "done":
                self.finished = True
            for q in list(self.subs):
                q.put_nowait(ev)

    def subscribe(self) -> tuple[list[dict], asyncio.Queue]:
        q: asyncio.Queue = asyncio.Queue()
        with self.lock:
            snapshot = list(self.events)
            if not self.finished:
                self.subs.add(q)
        return snapshot, q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self.lock:
            self.subs.discard(q)


_registry: dict[str, _Hub] = {}


def _sse(ev: dict) -> str:
    return f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"


async def start_analysis(path: str, goal: str | None, lang: str = "zh"):
    """校验路径 → 建档 → 启动后台 Agent 任务。"""
    result = validate_path(path)
    if not result.valid:
        raise HTTPException(status_code=400, detail=result.error or "路径无效")

    # 无 LLM（既没 key 也没 mock）→ 直接拒绝并给出指引
    from config import llm_configured
    if not llm_configured():
        raise HTTPException(
            status_code=503,
            detail="LLM 未配置：请在 backend/.env 中设置 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL，"
                   "或设置 REWIND_MOCK_LLM=1 启用本地 Mock 引擎。",
        )

    goal = (goal or "").strip() or None
    project = db.upsert_project(result.path, result.name, goal)
    report = db.create_report(project["id"], goal)
    report_id = report["id"]

    hub = _Hub()
    _registry[report_id] = hub

    asyncio.create_task(_run_agent_task(report_id, project["id"], result.path, goal, lang))
    return {"report_id": report_id, "project_id": project["id"]}


async def _run_agent_task(report_id: str, project_id: str, root: str, goal: str | None, lang: str = "zh"):
    hub = _registry[report_id]
    try:
        outcome = await run_diagnosis(root, goal, hub.publish, lang)
        db.complete_report(
            report_id=report_id,
            summary=outcome["report"]["summary"],
            project_map=outcome["report"]["project_map"],
            findings=outcome["report"]["findings"],
            suggestions=outcome["report"]["suggestions"],
            tool_trace=outcome["trace"],
            goal_source=outcome["report"].get("goal_source"),
        )
        db.set_report_goal_and_status(report_id,
                                      outcome["report"].get("goal") or goal,
                                      "completed")
        db.touch_project_analyzed(project_id)
        record = db.get_report(report_id)
        hub.publish({"type": "report", "report": record})
        hub.publish({"type": "done", "status": "completed"})
    except AgentError as e:
        db.fail_report(report_id, str(e))
        db.touch_project_analyzed(project_id)
        hub.publish({"type": "error", "message": str(e)})
        hub.publish({"type": "done", "status": "failed"})
    except Exception as e:  # noqa: BLE001
        db.fail_report(report_id, f"内部错误: {e}")
        hub.publish({"type": "error", "message": f"内部错误: {e}"})
        hub.publish({"type": "done", "status": "failed"})


async def stream_events(report_id: str) -> StreamingResponse:
    """SSE 流：先回放历史事件（支持刷新/重连），再实时推送。"""
    hub = _registry.get(report_id)

    if hub is None:
        # 进程内没有该分析：要么已完成落库，要么不存在/已中断
        record = db.get_report(report_id)
        if record is None:
            raise HTTPException(status_code=404, detail="分析任务不存在")
        if record["status"] == "completed":

            async def replay():
                yield _sse({"type": "phase", "phase": "done", "label": "分析已完成（历史记录回放）"})
                yield _sse({"type": "report", "report": record})
                yield _sse({"type": "done", "status": "completed"})

            return StreamingResponse(replay(), media_type="text/event-stream")
        # 僵尸 running（进程重启）或 failed
        if record["status"] == "running":
            db.fail_report(report_id, "分析被中断（服务重启），请重新发起分析")

        async def failed():
            yield _sse({"type": "error", "message": record.get("error") or "分析未完成，请重新发起"})
            yield _sse({"type": "done", "status": "failed"})

        return StreamingResponse(failed(), media_type="text/event-stream")

    snapshot, queue = hub.subscribe()

    async def generator():
        try:
            for ev in snapshot:
                yield _sse(ev)
            if hub.finished:
                return  # 回放模式：历史已含终止事件，直接结束响应
            while True:
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=15.0)
                except TimeoutError:
                    yield ": ping\n\n"  # 心跳，防止代理超时断开
                    continue
                yield _sse(ev)
                if ev.get("type") == "done":
                    break
        finally:
            hub.unsubscribe(queue)

    return StreamingResponse(generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
