"""Tool 2: read_project_file

读取项目内指定文件，带行号、限制体积、阻止路径逃逸。
"""

from tools.safety import looks_binary, MAX_FILE_BYTES, project_root_path, resolve_in_project

TOOL_NAME = "read_project_file"

DEFAULT_MAX_LINES = 400


async def read_project_file(project_root: str, file_path: str = "",
                            start_line: int = 1, max_lines: int = DEFAULT_MAX_LINES) -> dict:
    root = project_root_path(project_root)
    if root is None:
        return {"error": f"项目路径无效: {project_root}"}
    if not file_path:
        return {"error": "缺少 file_path 参数（项目内相对路径）"}

    target = resolve_in_project(project_root, file_path)
    if target is None:
        return {"error": f"路径越界或无效: {file_path}（只允许项目内相对路径）"}
    if not target.exists():
        return {"error": f"文件不存在: {file_path}"}
    if target.is_dir():
        return {"error": f"{file_path} 是目录，不是文件"}

    if looks_binary(target):
        return {"error": f"{file_path} 是二进制文件，无法读取"}

    size = target.stat().st_size
    if size > MAX_FILE_BYTES:
        return {"error": f"文件过大（{size} 字节 > {MAX_FILE_BYTES} 上限），请用 search_project 定位片段"}

    rel = str(target.relative_to(root))
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"error": f"读取失败: {e}"}

    all_lines = text.splitlines()
    total = len(all_lines)
    start = max(1, int(start_line))
    end = min(total, start + int(max_lines) - 1)
    slice_lines = all_lines[start - 1:end]

    numbered = "\n".join(f"{i:>4}| {line}" for i, line in enumerate(slice_lines, start=start))

    truncated = end < total
    return {
        "file": rel,
        "total_lines": total,
        "shown_range": f"{start}-{end}",
        "truncated": truncated,
        "next_start_line": end + 1 if truncated else None,
        "content": numbered if numbered else "(空文件)",
    }
