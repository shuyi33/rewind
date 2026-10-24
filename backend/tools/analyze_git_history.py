"""Tool 4: analyze_git_history

读取 Git 提交历史、最近改动、分支与工作区状态。
直接调用 git 命令行（无 GitPython 依赖）。
"""

import asyncio
import re
import subprocess
from datetime import date, datetime

from tools.safety import project_root_path

TOOL_NAME = "analyze_git_history"

GIT_TIMEOUT = 15  # 秒


async def _git(root: str, *args: str) -> tuple[int, str]:
    def run():
        try:
            proc = subprocess.run(
                ["git", "-C", root, *args],
                capture_output=True, text=True, timeout=GIT_TIMEOUT,
                env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": root,
                     "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C"},
            )
            return proc.returncode, (proc.stdout or proc.stderr).strip()
        except FileNotFoundError:
            return 127, "git 命令不可用"
        except subprocess.TimeoutExpired:
            return 124, "git 命令超时"

    return await asyncio.to_thread(run)


def _parse_log(raw: str):
    """格式: <iso_date>\x1f<author>\x1f<subject> 每行一条。"""
    commits = []
    for line in raw.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 3:
            commits.append({"date": parts[0], "author": parts[1], "message": parts[2]})
    return commits


def _days_ago(iso_date: str) -> int | None:
    m = re.match(r"(\d{4}-\d{2}-\d{2})", iso_date)
    if not m:
        return None
    try:
        d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None
    return (date.today() - d).days


def _human_days(days: int) -> str:
    if days <= 0:
        return "今天"
    if days < 30:
        return f"{days} 天前"
    if days < 365:
        return f"约 {days // 30} 个月前（{days} 天）"
    return f"约 {days // 365} 年前（{days} 天）"


async def analyze_git_history(project_root: str, max_commits: int = 30) -> dict:
    root = project_root_path(project_root)
    if root is None:
        return {"error": f"项目路径无效: {project_root}"}
    root = str(root)

    code, out = await _git(root, "rev-parse", "--is-inside-work-tree")
    if code != 0 or out.strip() != "true":
        return {
            "has_git": False,
            "note": "项目不是 Git 仓库（或 git 不可用），无法提供历史证据。",
        }

    branch_code, branch = await _git(root, "branch", "--show-current")
    status_code, status_raw = await _git(root, "status", "--porcelain")

    max_commits = max(1, min(int(max_commits), 200))
    log_code, log_raw = await _git(
        root, "log", f"-{max_commits}", "--date=short",
        "--pretty=format:%ad\x1f%an\x1f%s",
    )
    commits = _parse_log(log_raw) if log_code == 0 else []

    total_code, total_raw = await _git(root, "rev-list", "--count", "HEAD")
    total_commits = int(total_raw) if total_code == 0 and total_raw.isdigit() else None

    # 最近 5 次提交整体涉及的文件清单
    files_code, files_raw = await _git(root, "log", "-5", "--name-only", "--pretty=format:")
    last_changed_files = []
    if files_code == 0:
        for line in files_raw.splitlines():
            line = line.strip()
            if line and line not in last_changed_files:
                last_changed_files.append(line)
    last_changed_files = last_changed_files[:15]

    last_commit = dict(commits[0]) if commits else None
    first_commit = dict(commits[-1]) if commits else None
    for c in (last_commit, first_commit):
        if c:
            d = _days_ago(c["date"])
            c["days_ago"] = d
            c["relative"] = _human_days(d) if d is not None else None

    last_days = _days_ago(last_commit["date"]) if last_commit else None
    active_recently = (last_days is not None and last_days <= 30)

    uncommitted = status_raw.splitlines() if status_raw else []

    return {
        "has_git": True,
        "branch": branch if branch_code == 0 else "(detached)",
        "total_commits": total_commits,
        "commits_shown": len(commits),
        "first_commit": first_commit,
        "last_commit": last_commit,
        "active_recently": active_recently,
        "last_commit_note": (
            "最近 30 天内有提交" if active_recently else
            (f"最后一次提交于 {last_commit['relative']}" if last_commit else "无提交记录")
        ),
        "uncommitted_changes": len(uncommitted),
        "uncommitted_sample": uncommitted[:10],
        "last_changed_files": last_changed_files,
        "commit_log": [f"{c['date']}  {c['message']}  ({c['author']})" for c in commits[:30]],
    }
