"""启发式报告生成：仅基于工具真实返回的证据组装报告。

用途：
1. MockLLM 的最终报告（无 API Key 的本地模式）；
2. Agent Loop 超过步数上限时的降级回退（只要收集过证据就有产出）。

原则：不伪造结论——做不到的判断一律 unknown。
"""

import re
from pathlib import Path

_T = {
    "zh": {
        "todo_title": "存在 {n} 处显式 TODO/FIXME 标记（涉及 {m} 个文件）",
        "todo_detail": "这些是作者亲自留下的未完成标记，属于最直接的未完成证据。",
        "todo_note": "显式 TODO/FIXME 标记",
        "todo_reason": "TODO/FIXME 注释由 search_project 在源码中实际匹配到。",
        "deps_title": "依赖未安装，构建与测试均无法运行",
        "deps_note": "声明了依赖但 node_modules 不存在（run_project_check: deps_check 失败）",
        "deps_reason": "deps_check 检查实际执行并确认 node_modules 缺失。",
        "deps_sug": "安装依赖并运行一次构建",
        "deps_why": "依赖缺失使所有后续验证（构建/测试）都无法进行，这是恢复项目可运行性的第一块基石。",
        "plan_title": "README 规划清单：{d} 项已勾选 / {t} 项未勾选",
        "plan_detail": "清单勾选状态反映作者意图，但勾选项与实际实现是否一致尚未逐项核实。",
        "plan_note": "checklist 中 {t} 个未勾选项",
        "plan_reason": "来自 README 实际文本；完成度对应关系需要进一步代码核实。",
        "stale_title": "项目已搁置：最后一次提交约 {mo} 个月前（{d} 天）",
        "stale_detail": "这是搁置时间的事实陈述；具体停在哪一步请结合 TODO 与规划清单判断。",
        "stale_note": "最后提交：{date}（git log 实际读取）",
        "stale_reason": "git log 显示最后提交时间距今较远。",
        "runtime_title": "各页面/模块的运行时行为与相互可达性尚未验证",
        "runtime_detail": "静态扫描无法确认页面是否实际可访问、功能是否端到端可用。",
        "runtime_reason": "需要安装依赖后运行构建/开发服务器验证（当前启发式模式未执行）。",
        "todo_sug": "按文件处理 TODO/FIXME 清单",
        "todo_sug_why": "这些是作者明确标记的未完成点，成本最低、收益最确定。",
        "todo_sug_dep": "建议先完成依赖安装（若构建验证需要）",
        "todo_sug_impact": "消除最明确的未完成点，快速恢复项目完成度。",
        "area_all": "全局",
        "area_eng": "工程化",
        "area_plan": "规划",
        "summary_type": "项目为 {t}（技术栈：{s}）。",
        "summary_files": "共 {n} 个文件；主要模块：{m}。",
        "summary_git": "Git 显示最后提交于 {w}（{msg}）。",
        "summary_todo": "发现 {n} 处 TODO/FIXME；{dep}",
        "summary_deps_bad": "依赖未安装，无法构建验证。",
        "summary_deps_ok": "依赖状态未见异常。",
        "summary_plan": "README 规划 {a} 项，其中 {b} 项未勾选。",
        "notes": "共 {f} 个文件 / {d} 个目录",
        "unknown_type": "未知类型",
        "unknown_stack": "未知",
        "no_modules": "未识别",
        "unknown_time": "未知时间前",
        "depends_none": "无",
    },
    "en": {
        "todo_title": "{n} explicit TODO/FIXME markers found (across {m} files)",
        "todo_detail": "These are unfinished-work markers left by the author — the most direct evidence of incompleteness.",
        "todo_note": "explicit TODO/FIXME marker",
        "todo_reason": "The TODO/FIXME comments were actually matched in source by search_project.",
        "deps_title": "Dependencies not installed — build and tests cannot run",
        "deps_note": "Dependencies declared but node_modules missing (run_project_check: deps_check failed)",
        "deps_reason": "deps_check actually ran and confirmed node_modules is missing.",
        "deps_sug": "Install dependencies and run one build",
        "deps_why": "Missing dependencies block every downstream verification (build/tests). Restoring the build is the first cornerstone of reviving the project.",
        "plan_title": "README checklist: {d} done / {t} unchecked",
        "plan_detail": "Checkboxes reflect author intent, but whether checked items match the actual implementation is not yet verified item by item.",
        "plan_note": "{t} unchecked items in the checklist",
        "plan_reason": "From the README text; the completion mapping needs further code verification.",
        "stale_title": "Project abandoned: last commit about {mo} months ago ({d} days)",
        "stale_detail": "A factual statement of abandonment time; where exactly it stopped needs the TODO list and plan checklist to judge.",
        "stale_note": "Last commit: {date} (read from git log)",
        "stale_reason": "git log shows the last commit is far in the past.",
        "runtime_title": "Runtime behavior and reachability of pages/modules not yet verified",
        "runtime_detail": "Static scanning cannot confirm pages are actually reachable or features work end to end.",
        "runtime_reason": "Requires installing dependencies and running a build/dev server (not executed in heuristic mode).",
        "todo_sug": "Work through the TODO/FIXME list file by file",
        "todo_sug_why": "These are points the author explicitly marked unfinished — lowest cost, most certain payoff.",
        "todo_sug_dep": "Consider installing dependencies first (if build verification is needed)",
        "todo_sug_impact": "Clears the most explicit unfinished points and quickly restores completeness.",
        "area_all": "Global",
        "area_eng": "Tooling",
        "area_plan": "Planning",
        "summary_type": "Project is {t} (stack: {s}).",
        "summary_files": "{n} files; key modules: {m}.",
        "summary_git": "Git shows the last commit {w} ({msg}).",
        "summary_todo": "{n} TODO/FIXME markers found; {dep}",
        "summary_deps_bad": "dependencies not installed, build verification impossible.",
        "summary_deps_ok": "dependency status looks fine.",
        "summary_plan": "README plans {a} items, {b} unchecked.",
        "notes": "{f} files / {d} directories",
        "unknown_type": "unknown",
        "unknown_stack": "unknown",
        "no_modules": "unidentified",
        "unknown_time": "unknown time ago",
        "depends_none": "none",
    },
}


def _find(collected: list[dict], name: str, arg_pred=None) -> dict | None:
    for c in collected:
        if c["name"] == name and (arg_pred is None or arg_pred(c.get("arguments", {}))):
            return c.get("result") or {}
    return None


def _parse_tree_modules(tree: str) -> list[str]:
    """从缩进树中提取 src/ 的直接子目录。"""
    mods = []
    in_src = False
    for line in tree.splitlines():
        if not line.strip():
            continue
        if re.match(r"^src/\s*$", line):
            in_src = True
            continue
        if in_src:
            m = re.match(r"^ {2}([^ /]+)/", line)
            if m:
                mods.append(f"src/{m.group(1)}")
            elif not line.startswith(" "):
                in_src = False
    return mods


def _parse_tree_pages(tree: str) -> list[str]:
    """提取 pages/ views/ 或（Next.js 风格）app/ 目录下的文件名作为页面。"""
    pages = []
    watching = None  # 命中目录行的缩进
    for line in tree.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        name = line.strip()
        if watching is None:
            if name.rstrip("/").split("/")[-1] in ("pages", "views", "app"):
                watching = indent
            continue
        if indent > watching:
            if name.endswith("/"):
                continue  # 子目录跳过（页面文件仍在其中时由后续行处理）
            pages.append(re.sub(r"\.(tsx|jsx|vue|py|html|js|ts)$", "", name))
        else:
            watching = None
    return pages[:12]


def _extract_goal_from_readme(readme: dict) -> tuple[str | None, str]:
    if not readme or "content" not in readme:
        return None, "unknown"
    text = readme.get("content", "")
    # 去掉行号前缀
    lines = [re.sub(r"^\s*\d+\|\s?", "", ln) for ln in text.splitlines()]
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith("```") or s.startswith("-") or s.startswith("!"):
            continue
        if len(s) >= 8:
            return s[:160], "readme"
    return None, "unknown"


def _readme_checklist(readme: dict) -> tuple[int, int] | None:
    if not readme or "content" not in readme:
        return None
    text = readme.get("content", "")
    done = len(re.findall(r"\[[xX]\]", text))
    todo = len(re.findall(r"\[ \]", text))
    return (done, todo) if (done + todo) > 0 else None


def build_heuristic_report(collected: list[dict], project_root: str = "", lang: str = "zh") -> dict:
    M = _T.get(lang, _T["zh"])
    detect = _find(collected, "detect_project_type") or {}
    scan = _find(collected, "scan_project_structure") or {}
    git = _find(collected, "analyze_git_history") or {}
    todo_search = _find(collected, "search_project",
                        lambda a: "TODO" in str(a.get("query", "")))
    readme = _find(collected, "read_project_file",
                   lambda a: str(a.get("file_path", "")).lower().startswith("readme"))
    deps_check = _find(collected, "run_project_check",
                       lambda a: a.get("check") == "deps_check")

    findings: list[dict] = []
    suggestions: list[dict] = []

    # ---------- project map ----------
    tree = scan.get("tree", "")
    modules = _parse_tree_modules(tree) or [d for d in scan.get("key_dirs", [])][:6]
    pages = _parse_tree_pages(tree)
    root_name = Path(project_root).name if project_root else (scan.get("root", "/").rstrip("/").split("/")[-1])
    # 入口文件直接从树文本匹配（strip 后的裸文件名）
    tree_files = {ln.strip() for ln in tree.splitlines() if ln.strip() and not ln.strip().endswith("/")}
    entry_points = [f for f in ("index.html", "main.tsx", "main.jsx",
                                "App.tsx", "app.py", "main.py", "__init__.py")
                    if f in tree_files]
    project_map = {
        "name": root_name,
        "project_type": detect.get("project_type", M["unknown_type"]),
        "tech_stack": (detect.get("frameworks") or [])[:8],
        "entry_points": entry_points,
        "modules": modules[:10],
        "pages": pages,
        "notes": M["notes"].format(f=scan.get("total_files", "?"), d=scan.get("total_dirs", "?")),
    }

    # ---------- goal ----------
    goal, goal_source = _extract_goal_from_readme(readme)

    # ---------- findings ----------
    if todo_search and todo_search.get("matches"):
        evs = [
            {"file": m["file"], "lines": str(m["line"]),
             "snippet": (m.get("snippet") or "")[:120], "note": M["todo_note"]}
            for m in todo_search["matches"][:10]
        ]
        files = todo_search.get("files_with_matches") or []
        findings.append({
            "id": "f_todo",
            "title": M["todo_title"].format(n=todo_search["total_matches_shown"], m=len(files)),
            "status": "confirmed_incomplete",
            "detail": M["todo_detail"],
            "area": M["area_all"],
            "evidence": evs,
            "reasoning": M["todo_reason"],
        })

    if deps_check and deps_check.get("ok") is False and not deps_check.get("skipped"):
        findings.append({
            "id": "f_deps",
            "title": M["deps_title"],
            "status": "confirmed_incomplete",
            "area": M["area_eng"],
            "evidence": [{
                "file": "package.json", "lines": None, "snippet": None,
                "note": M["deps_note"],
            }],
            "reasoning": M["deps_reason"],
        })
        suggestions.append({
            "title": M["deps_sug"],
            "why_now": M["deps_why"],
            "evidence": [{"file": "package.json", "note": M["deps_note"]}],
            "related_files": ["package.json"],
            "depends_on": [M["depends_none"]],
            "impact": M["deps_why"],
        })

    checklist = _readme_checklist(readme)
    if checklist:
        done, todo = checklist
        findings.append({
            "id": "f_readme_plan",
            "title": M["plan_title"].format(d=done, t=todo),
            "status": "suspected_incomplete",
            "detail": M["plan_detail"],
            "area": M["area_plan"],
            "evidence": [{
                "file": "README.md", "lines": None,
                "note": M["plan_note"].format(t=todo),
            }],
            "reasoning": M["plan_reason"],
        })

    if git and git.get("has_git"):
        last = git.get("last_commit") or {}
        days = last.get("days_ago")
        if days is not None and days > 30:
            findings.append({
                "id": "f_stale",
                "title": M["stale_title"].format(mo=days // 30, d=days),
                "status": "unknown",
                "detail": M["stale_detail"],
                "area": M["area_all"],
                "evidence": [{
                    "file": ".git", "lines": None,
                    "snippet": f"{last.get('message')}",
                    "note": M["stale_note"].format(date=last.get("date")),
                }],
                "reasoning": M["stale_reason"],
            })

    # 诚实示范：启发式模式无法验证的内容
    findings.append({
        "id": "f_runtime_unknown",
        "title": M["runtime_title"],
        "status": "unknown",
        "detail": M["runtime_detail"],
        "area": M["area_all"],
        "evidence": [],
        "reasoning": M["runtime_reason"],
    })

    if not any(s.get("title", "").startswith(M["todo_sug"][:4]) for s in suggestions) and todo_search and todo_search.get("matches"):
        suggestions.append({
            "title": M["todo_sug"],
            "why_now": M["todo_sug_why"],
            "evidence": [{"file": m["file"], "lines": str(m["line"])}
                         for m in todo_search["matches"][:3]],
            "related_files": sorted({m["file"] for m in todo_search["matches"]})[:6],
            "depends_on": [M["todo_sug_dep"]],
            "impact": M["todo_sug_impact"],
        })

    # ---------- summary ----------
    ptype = detect.get("project_type", M["unknown_type"])
    frameworks = detect.get("frameworks", [])[:5]
    stack = "、".join(frameworks) if lang == "zh" else ", ".join(frameworks)
    bits = [M["summary_type"].format(t=ptype, s=stack or M["unknown_stack"])]
    mod_str = ("、".join(modules[:5]) if lang == "zh" else ", ".join(modules[:5])) or M["no_modules"]
    bits.append(M["summary_files"].format(n=scan.get("total_files", "?"), m=mod_str))
    if git and git.get("has_git") and git.get("last_commit"):
        bits.append(M["summary_git"].format(
            w=git["last_commit"].get("relative", M["unknown_time"]),
            msg=git["last_commit"].get("message"),
        ))
    n_todo = todo_search.get("total_matches_shown", 0) if todo_search else 0
    dep_bit = M["summary_deps_bad"] if deps_check and deps_check.get("ok") is False else M["summary_deps_ok"]
    bits.append(M["summary_todo"].format(n=n_todo, dep=dep_bit))
    if checklist:
        bits.append(M["summary_plan"].format(a=checklist[0] + checklist[1], b=checklist[1]))
    summary = "".join(bits)

    return {
        "goal": goal,
        "goal_source": goal_source,
        "project_map": project_map,
        "summary": summary,
        "findings": findings,
        "suggestions": suggestions[:3],
        "generated_by": "heuristic",
    }
