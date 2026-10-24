"""工具结果的一行摘要（用于 SSE 实时展示与 trace 存档）。"""


def summarize_tool(tool: str, outcome: dict) -> str:
    r = outcome.get("result") or {}
    if not outcome.get("ok"):
        err = r.get("error") or outcome.get("error") or "失败"
        return f"✗ {err}"

    if tool == "detect_project_type":
        return f"{r.get('project_type', '?')}（置信度 {r.get('confidence', '?')}）"
    if tool == "scan_project_structure":
        return (f"{r.get('total_files', '?')} 个文件 / {r.get('total_dirs', '?')} 个目录"
                + ("（树已截断）" if r.get("tree_truncated") else ""))
    if tool == "analyze_git_history":
        if r.get("has_git"):
            return (f"{r.get('total_commits', '?')} 次提交 · {r.get('last_commit_note', '')}"
                    + (f" · {r.get('uncommitted_changes')} 处未提交" if r.get("uncommitted_changes") else ""))
        return "没有 Git 仓库"
    if tool == "search_project":
        n = r.get("total_matches_shown", 0)
        files = r.get("files_with_matches") or []
        return f"{n} 处匹配（{len(files)} 个文件）" + ("（截断）" if r.get("truncated") else "")
    if tool == "read_project_file":
        return f"{r.get('file', '?')} 第 {r.get('shown_range', '?')} 行"
    if tool == "run_project_check":
        if r.get("skipped"):
            return f"跳过：{r.get('details', '')}"
        # 非命令型结果（如 deps_check 的直接结论）优先展示 details
        if r.get("details") and not r.get("command"):
            return f"{'通过' if r.get('ok') else '失败'}：{r['details']}"
        return f"{'通过' if r.get('ok') else '失败'}：{r.get('command', '')}".rstrip("：")
    return "完成"
