"""Phase 3 验证：6 个 Tools 在真实 fixture 上逐一运行，含安全边界测试。"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.registry import execute_tool, TOOLS, tool_specs  # noqa: E402

FIXTURE = str(Path(__file__).parent / "fixtures" / "pocket-ledger")


def show(title, res, keys=None):
    print("=" * 60)
    print(title, "| ok:", res["ok"], "| ms:", res["duration_ms"])
    r = res.get("result") or {"error": res.get("error")}
    if keys:
        r = {k: r.get(k) for k in keys}
    s = json.dumps(r, ensure_ascii=False, indent=1, default=str)
    print(s[:1400])
    print()


async def main():
    # 0. 注册表完整性：6 个工具 + OpenAI schema
    assert len(TOOLS) == 6, f"应有 6 个工具，实际 {len(TOOLS)}"
    specs = tool_specs()
    assert len(specs) == 6
    for s in specs:
        assert s["type"] == "function" and s["function"]["name"] in TOOLS
    print("[OK] 工具注册表完整：6 个工具，schema 可用\n")

    # 1. read_project_file：正常读取
    res = await execute_tool(FIXTURE, "read_project_file",
                             {"file_path": "README.md"})
    show("read_project_file (README.md)", res, ["file", "total_lines", "shown_range"])
    assert res["ok"] and "口袋账本" in res["result"]["content"]

    # 2. read_project_file：安全边界 — 路径逃逸必须被拒绝
    res = await execute_tool(FIXTURE, "read_project_file",
                             {"file_path": "../config.py"})
    assert not res["ok"] and "越界" in (res["error"] or ""), "路径逃逸必须被拒绝"
    print("[OK] 路径逃逸被拒绝:", res["error"], "\n")

    res = await execute_tool(FIXTURE, "read_project_file",
                             {"file_path": "/etc/passwd"})
    assert not res["ok"], "绝对路径必须被拒绝"
    print("[OK] 绝对路径被拒绝\n")

    # 3. read_project_file：行范围
    res = await execute_tool(FIXTURE, "read_project_file",
                             {"file_path": "src/services/ledger.ts", "start_line": 20, "max_lines": 10})
    show("read_project_file (ledger.ts L20-29)", res, ["file", "total_lines", "shown_range", "next_start_line"])
    assert res["ok"] and res["result"]["truncated"] is True

    # 4. search_project：TODO 搜索
    res = await execute_tool(FIXTURE, "search_project", {"query": "TODO"})
    show("search_project (TODO)", res, ["total_matches_shown", "files_with_matches"])
    files = res["result"]["files_with_matches"]
    assert "src/services/ledger.ts" in files
    assert "src/pages/Archive.tsx" in files
    assert "tests/ledger.test.ts" in files

    # 5. search_project：未引用组件检测（BudgetBadge 只在定义处出现）
    res = await execute_tool(FIXTURE, "search_project", {"query": "BudgetBadge"})
    show("search_project (BudgetBadge 引用)", res, ["total_matches_shown", "matches"])
    assert res["result"]["total_matches_shown"] == 1, "BudgetBadge 应只出现 1 次（仅定义，无引用）"

    # 6. search_project：budget 字段证据
    res = await execute_tool(FIXTURE, "search_project", {"query": "budget"})
    files = res["result"]["files_with_matches"]
    print("[budget 出现的文件]", files, "\n")
    assert "src/types/ledger.ts" in files and "src/services/ledger.ts" in files
    assert "src/pages/CreateEntry.tsx" in files  # 注释里提到
    assert "src/components/BudgetBadge.tsx" in files

    # 7. analyze_git_history
    res = await execute_tool(FIXTURE, "analyze_git_history", {})
    show("analyze_git_history", res,
         ["branch", "total_commits", "last_commit", "last_commit_note", "active_recently", "last_changed_files"])
    assert res["ok"]
    assert res["result"]["total_commits"] == 4
    assert res["result"]["active_recently"] is False
    assert res["result"]["last_commit"]["message"] == "wip: 图表页骨架（烂尾于此）"

    # 8. run_project_check：deps_check（node_modules 不存在 → 重要证据）
    res = await execute_tool(FIXTURE, "run_project_check", {"check": "deps_check"})
    show("run_project_check (deps_check)", res)
    assert res["ok"] is True, "工具本身应执行成功"
    assert res["result"]["ok"] is False, "检查应发现依赖未安装"
    assert "依赖未安装" in res["result"]["details"]

    # 9. run_project_check：test（无 test 脚本 → skip 说明）
    res = await execute_tool(FIXTURE, "run_project_check", {"check": "test"})
    show("run_project_check (test)", res)
    assert res["result"].get("skipped") is True and "没有 test 脚本" in res["result"]["details"]

    # 10. run_project_check：安全 — 任意命令注入必须被拒绝
    res = await execute_tool(FIXTURE, "run_project_check",
                             {"check": "build; rm -rf /"})
    assert not res["ok"], "非白名单 check 必须被拒绝"
    print("[OK] 非白名单 check 被拒绝:", res["error"], "\n")

    print("[PASS] Phase 3 全部 6 个工具验证通过（含安全边界）")


if __name__ == "__main__":
    asyncio.run(main())
