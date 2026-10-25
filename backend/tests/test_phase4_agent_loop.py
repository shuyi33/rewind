"""Phase 4 验证：Agent Loop 完整链路（Mock LLM 模式，真实工具、真实证据）。

验证点：
1. 事件流顺序合法：phase → (tool_call → tool_result)* → report → done
2. Agent 自主完成多步工具调度（>=5 步，非单轮直出）
3. 报告通过 pydantic 校验，findings 覆盖多种状态
4. 证据真实：文件路径、行号、代码片段都来自 fixture 实际内容
"""

import asyncio
import json
import os
import sys
from pathlib import Path

os.environ["REWIND_MOCK_LLM"] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.loop import run_diagnosis  # noqa: E402

FIXTURE = str(Path(__file__).parent / "fixtures" / "pocket-ledger")


async def main():
    events = []

    def on_event(ev):
        events.append(ev)
        t = ev["type"]
        if t == "phase":
            print(f"[phase] {ev['phase']:10s} {ev['label']}")
        elif t == "tool_call":
            print(f"  → call #{ev['step']}: {ev['tool']}({json.dumps(ev['args'], ensure_ascii=False)})")
        elif t == "tool_result":
            print(f"  ← #{ev['step']} {ev['tool']}: {ev['summary']} ({ev['duration_ms']}ms)")

    outcome = await run_diagnosis(FIXTURE, goal=None, on_event=on_event)
    report = outcome["report"]
    trace = outcome["trace"]

    print("\n===== 事件流校验 =====")
    types = [e["type"] for e in events]
    assert "phase" in types, "缺少 phase 事件"
    tool_calls = [e for e in events if e["type"] == "tool_call"]
    tool_results = [e for e in events if e["type"] == "tool_result"]
    assert len(tool_calls) == len(tool_results) > 4, f"工具调用应成对且 >=5 步，实际 {len(tool_calls)}"
    # 每个 tool_call 后紧跟对应 tool_result
    seq = [e["type"] for e in events if e["type"] in ("tool_call", "tool_result")]
    for i in range(0, len(seq), 2):
        assert seq[i] == "tool_call" and seq[i + 1] == "tool_result", "call/result 必须交替"
    print(f"[OK] 事件序列合法（{len(tool_calls)} 次工具调用）")

    print("\n===== Agent 调度了哪些工具 =====")
    used = [c["tool"] for c in tool_calls]
    print(used)
    for expected in ("detect_project_type", "scan_project_structure", "analyze_git_history"):
        assert expected in used, f"Agent 应调用 {expected}"

    print("\n===== 报告结构 =====")
    print("generated_by:", report.get("generated_by"))
    print("goal:", report.get("goal"))
    print("goal_source:", report.get("goal_source"))
    print("summary:", report.get("summary"))
    print("project_map:", json.dumps(report["project_map"], ensure_ascii=False))
    print(f"findings: {len(report['findings'])} 条 / suggestions: {len(report['suggestions'])} 条")
    for f in report["findings"]:
        print(f"  [{f['status']:22s}] {f['title']}（证据 {len(f['evidence'])} 条）")
    for s in report["suggestions"]:
        print(f"  [建议] {s['title']} ← {s['depends_on']}")

    print("\n===== 报告真实性断言 =====")
    assert report["goal_source"] == "readme", "goal 应从 README 提取"
    assert report["goal"] and "记账" in report["goal"], "goal 内容应来自 README"

    statuses = {f["status"] for f in report["findings"]}
    assert "confirmed_incomplete" in statuses, "TODO 证据应产生 confirmed_incomplete"
    assert "unknown" in statuses, "应诚实包含 unknown 条目"

    todo_f = next(f for f in report["findings"] if f["status"] == "confirmed_incomplete")
    ev_files = [e["file"] for e in todo_f["evidence"]]
    assert any("CreateEntry.tsx" in p or "Charts.tsx" in p for p in ev_files), "TODO 证据应指向真实文件"

    # 证据真实性：fixture 里 TODO 的确在这些文件这些行
    charts = Path(FIXTURE, "src/pages/Charts.tsx").read_text().splitlines()
    ev = next(e for e in todo_f["evidence"] if "Charts.tsx" in e["file"])
    line_no = int(ev["lines"])
    assert "FIXME" in charts[line_no - 1] or "TODO" in charts[line_no - 1], "行号必须对应真实 TODO"

    assert len(report["suggestions"]) >= 1
    s1 = report["suggestions"][0]
    assert "依赖" in s1["title"] or "构建" in s1["title"], "最优先建议应指向恢复构建能力"

    assert trace and len(trace) == len(tool_calls)
    print("\n[PASS] Phase 4 Agent Loop 完整链路验证通过（mock 模式）")


if __name__ == "__main__":
    asyncio.run(main())
