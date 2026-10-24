"""Tool 3: search_project

在项目文本文件中搜索（正则）：TODO/FIXME、组件引用、函数调用、关键词等。
纯 Python 实现，跨平台，不依赖系统 grep。
"""

import re
from pathlib import Path

from tools.safety import is_ignored_dir, looks_binary, MAX_FILE_BYTES, project_root_path, resolve_in_project

TOOL_NAME = "search_project"

MAX_TOTAL_MATCHES = 60
CONTEXT_CHARS = 90  # 匹配行上下文截断


def _iter_searchable_files(root: Path, glob_pattern: str | None):
    for p in root.rglob(glob_pattern or "*"):
        if not p.is_file():
            continue
        rel_parts = p.relative_to(root).parts
        if any(is_ignored_dir(seg) for seg in rel_parts[:-1]):
            continue
        if rel_parts[-1].startswith(".") and rel_parts[-1] not in (".env.example",):
            continue
        if p.stat().st_size > MAX_FILE_BYTES:
            continue
        if looks_binary(p):
            continue
        yield p


async def search_project(project_root: str, query: str = "",
                         file_glob: str | None = None,
                         regex: bool = False,
                         max_results: int = MAX_TOTAL_MATCHES) -> dict:
    root = project_root_path(project_root)
    if root is None:
        return {"error": f"项目路径无效: {project_root}"}
    if not query:
        return {"error": "缺少 query 参数"}

    max_results = max(1, min(int(max_results), MAX_TOTAL_MATCHES))

    if regex:
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error as e:
            return {"error": f"正则表达式无效: {e}"}
    else:
        pattern = re.compile(re.escape(query), re.IGNORECASE)

    # glob 校验：只允许简单通配，避免全量遍历陷阱
    if file_glob and (".." in file_glob or file_glob.startswith("/")):
        return {"error": "file_glob 只允许项目内相对通配符"}

    matches = []
    files_scanned = 0
    truncated = False
    try:
        for path in _iter_searchable_files(root, file_glob):
            files_scanned += 1
            rel = path.relative_to(root).as_posix()  # 统一正斜杠（Windows 下 str() 是反斜杠）
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                m = pattern.search(line)
                if not m:
                    continue
                snippet = line.strip()
                if len(snippet) > CONTEXT_CHARS * 2:
                    s = max(0, m.start() - CONTEXT_CHARS)
                    snippet = ("…" if s > 0 else "") + line[s:s + CONTEXT_CHARS * 2] + "…"
                matches.append({
                    "file": rel,
                    "line": lineno,
                    "match": m.group(0),
                    "snippet": snippet,
                })
                if len(matches) >= max_results:
                    truncated = True
                    break
            if truncated:
                break
    except PermissionError:
        return {"error": "没有权限遍历该项目"}

    files_with_matches = sorted({m["file"] for m in matches})
    return {
        "query": query,
        "regex": bool(regex),
        "file_glob": file_glob,
        "files_scanned": files_scanned,
        "total_matches_shown": len(matches),
        "files_with_matches": files_with_matches,
        "truncated": truncated,
        "matches": matches,
    }
