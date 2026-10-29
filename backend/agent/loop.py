"""Agent Loop 核心。

真正的智能体循环（不是「输入 → LLM → 输出」）：
LLM 决定调用什么工具 → 执行 → 结果回填 → LLM 根据结果决定下一步
→ … → 证据充分后产出结构化诊断报告。

事件通过 on_event 回调实时上报（SSE 推给前端扫描页）。
"""

import json

from agent.heuristic import build_heuristic_report
from agent.llm import get_llm
from agent.prompts import system_prompt, user_brief
from agent.tool_summary import summarize_tool
from config import settings
from models.schemas import Evidence, Finding, ProjectMap, Suggestion
from pydantic import BaseModel, ValidationError
from tools.registry import execute_tool, PHASE_LABELS, phase_of, tool_specs

MAX_REPORT_RETRIES = 3


class ReportCore(BaseModel):
    """LLM 最终报告的校验模型（严格把关：不合法字段直接打回重试）。"""

    goal: str | None = None
    goal_source: str = "unknown"
    project_map: ProjectMap
    summary: str
    findings: list[Finding]
    suggestions: list[Suggestion] = []


class AgentError(Exception):
    pass


def extract_json_block(content: str) -> dict | None:
    """从模型输出中提取 JSON 对象（容忍 markdown 代码块包裹）。"""
    if not content:
        return None
    text = content.strip()
    fenced = "```json" in text or "```" in text
    if fenced:
        parts = text.split("```")
        for part in parts:
            p = part.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{") and p.endswith("}"):
                try:
                    return json.loads(p)
                except json.JSONDecodeError:
                    continue
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    # 兜底：首尾大括号之间
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e > s:
        try:
            return json.loads(text[s:e + 1])
        except json.JSONDecodeError:
            return None
    return None


def validate_report(data: dict) -> tuple[ReportCore | None, str | None]:
    """校验报告结构，返回 (模型, 失败原因)。"""
    try:
        core = ReportCore(**data)
    except ValidationError as e:
        first = e.errors()[0]
        loc = ".".join(str(x) for x in first["loc"])
        return None, f"字段 {loc}: {first['msg']}"
    if len(core.findings) == 0:
        return None, "findings 不能为空"
    return core, None


class AgentRunner:
    def __init__(self, project_root: str, goal: str | None, on_event, lang: str = "zh"):
        self.root = project_root
        self.goal = goal
        self.on_event = on_event
        self.lang = lang
        self.trace: list[dict] = []

    def emit(self, event: dict) -> None:
        self.on_event(event)

    async def run(self) -> dict:
        llm = get_llm(self.lang)
        specs = tool_specs()
        messages: list[dict] = [
            {"role": "system", "content": system_prompt(self.lang)},
            {"role": "user", "content": user_brief(self.root, self.goal, last_analyzed=False, lang=self.lang)},
        ]

        report_core: ReportCore | None = None
        parse_failures = 0
        step = 0

        while step < settings.MAX_AGENT_STEPS:
            step += 1
            try:
                resp = await llm.chat(messages, specs)
            except AgentError:
                raise
            except Exception as e:  # noqa: BLE001 — 网络/鉴权等错误统一转为失败事件
                raise AgentError(f"LLM 调用失败: {e}") from e

            # ---- 分支 A：请求工具 → 执行 → 回填 ----
            if resp.tool_calls:
                call_msgs = []
                for i, call in enumerate(resp.tool_calls):
                    call_id = f"call_{step}_{i}"
                    call_msgs.append((call_id, call))
                messages.append({
                    "role": "assistant",
                    "content": resp.content,
                    "tool_calls": [
                        {"id": cid, "type": "function",
                         "function": {"name": c["name"],
                                      "arguments": json.dumps(c["arguments"], ensure_ascii=False)}}
                        for cid, c in call_msgs
                    ],
                })

                for cid, call in call_msgs:
                    name, args = call["name"], call["arguments"]
                    phase = phase_of(name)
                    self.emit({"type": "phase", "phase": phase,
                               "label": PHASE_LABELS.get(phase, "正在分析")})
                    self.emit({"type": "tool_call", "step": step, "tool": name,
                               "args": args, "phase": phase})
                    outcome = await execute_tool(self.root, name, args, self.lang)
                    summary = summarize_tool(name, outcome, self.lang)
                    self.emit({"type": "tool_result", "step": step, "tool": name,
                               "ok": bool(outcome["ok"]), "summary": summary,
                               "duration_ms": outcome["duration_ms"]})
                    self.trace.append({
                        "step": step, "tool": name, "args": args,
                        "phase": phase, "ok": bool(outcome["ok"]), "summary": summary,
                    })
                    payload = outcome.get("result") or {"error": outcome.get("error")}
                    messages.append({
                        "role": "tool", "tool_call_id": cid, "name": name,
                        "content": json.dumps(payload, ensure_ascii=False, default=str)[:6000],
                    })
                continue

            # ---- 分支 B：无工具调用 → 尝试解析最终报告 ----
            data = extract_json_block(resp.content or "")
            if data is not None:
                core, err = validate_report(data)
                if core is not None:
                    report_core = core
                    break
            parse_failures += 1
            reason = err or "未能从输出中解析出 JSON"
            if parse_failures >= MAX_REPORT_RETRIES:
                raise AgentError(f"模型多次未能输出合法报告（{reason}）")
            messages.append({"role": "user", "content": (
                f"你上一次的输出无法作为报告使用：{reason}。"
                "请严格按照系统提示词中的 JSON 结构重新输出完整诊断报告，"
                "不要输出 JSON 以外的任何文字。")})

        if report_core is None:
            # 步数用尽：只要收集过证据就降级为启发式报告（明确标注）
            if self.trace:
                collected = [{"name": t["tool"], "arguments": t["args"], "result": {}}
                             for t in self.trace]
                # 从 messages 中恢复真实工具结果
                real = []
                for m in messages:
                    if m.get("role") == "tool":
                        try:
                            real.append({"name": m.get("name", ""), "arguments": {},
                                         "result": json.loads(m["content"])})
                        except (json.JSONDecodeError, TypeError):
                            pass
                data = build_heuristic_report(real or collected, self.root, self.lang)
                data["generated_by"] = "heuristic_fallback"
                report_core, _ = validate_report(data)
            if report_core is None:
                raise AgentError(f"Agent 在 {settings.MAX_AGENT_STEPS} 步内未产出报告")

        data = report_core.model_dump()
        # 用户显式提供的项目目标优先于任何推断（含 README 提取）
        if self.goal and data.get("goal_source") != "user":
            data["goal"] = self.goal
            data["goal_source"] = "user"

        return {
            "report": data,
            "trace": self.trace,
        }


async def run_diagnosis(project_root: str, goal: str | None, on_event, lang: str = "zh") -> dict:
    runner = AgentRunner(project_root, goal, on_event, lang)
    return await runner.run()
