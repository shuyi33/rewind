"""工具结果的一行摘要（用于 SSE 实时展示与 trace 存档）。"""

_ZH = {
    "confidence": "置信度 {v}",
    "files_dirs": "{f} 个文件 / {d} 个目录",
    "tree_truncated": "（树已截断）",
    "commits": "{n} 次提交 · {note}",
    "uncommitted": " · {n} 处未提交",
    "no_git": "没有 Git 仓库",
    "matches": "{n} 处匹配（{m} 个文件）",
    "truncated": "（截断）",
    "lines": "{f} 第 {r} 行",
    "skip": "跳过：{d}",
    "pass_fail": "{pf}：{d}",
    "pass": "通过",
    "fail": "失败",
    "done": "完成",
    "fail_generic": "失败",
}

_EN = {
    "confidence": "confidence {v}",
    "files_dirs": "{f} files / {d} dirs",
    "tree_truncated": " (tree truncated)",
    "commits": "{n} commits · {note}",
    "uncommitted": " · {n} uncommitted",
    "no_git": "no git repository",
    "matches": "{n} matches ({m} files)",
    "truncated": " (truncated)",
    "lines": "{f} lines {r}",
    "skip": "skipped: {d}",
    "pass_fail": "{pf}: {d}",
    "pass": "pass",
    "fail": "fail",
    "done": "done",
    "fail_generic": "failed",
}


def summarize_tool(tool: str, outcome: dict, lang: str = "zh") -> str:
    M = _EN if lang == "en" else _ZH
    r = outcome.get("result") or {}
    if not outcome.get("ok"):
        err = r.get("error") or outcome.get("error") or M["fail_generic"]
        return "\u2717 " + err

    if tool == "detect_project_type":
        c = M["confidence"].format(v=r.get("confidence", "?"))
        return f"{r.get('project_type', '?')}（{c}）" if lang == "zh" else f"{r.get('project_type', '?')} ({c})"
    if tool == "scan_project_structure":
        base = M["files_dirs"].format(f=r.get("total_files", "?"), d=r.get("total_dirs", "?"))
        return base + (M["tree_truncated"] if r.get("tree_truncated") else "")
    if tool == "analyze_git_history":
        if r.get("has_git"):
            base = M["commits"].format(n=r.get("total_commits", "?"), note=r.get("last_commit_note", ""))
            if r.get("uncommitted_changes"):
                base += M["uncommitted"].format(n=r["uncommitted_changes"])
            return base
        return M["no_git"]
    if tool == "search_project":
        n = r.get("total_matches_shown", 0)
        files = r.get("files_with_matches") or []
        return M["matches"].format(n=n, m=len(files)) + (M["truncated"] if r.get("truncated") else "")
    if tool == "read_project_file":
        return M["lines"].format(f=r.get("file", "?"), r=r.get("shown_range", "?"))
    if tool == "run_project_check":
        pf = M["pass"] if r.get("ok") else M["fail"]
        if r.get("skipped"):
            return M["skip"].format(d=r.get("details", ""))
        if r.get("details") and not r.get("command"):
            return M["pass_fail"].format(pf=pf, d=r["details"])
        return M["pass_fail"].format(pf=pf, d=r.get("command", "")).rstrip("\uff1a:")
    return M["done"]
