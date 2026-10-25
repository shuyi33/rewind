"""启发式报告生成：仅基于工具真实返回的证据组装报告。

用途：
1. MockLLM 的最终报告（无 API Key 的本地模式）；
2. Agent Loop 超过步数上限时的降级回退（只要收集过证据就有产出）。

原则：不伪造结论——做不到的判断一律 unknown。
"""

import re
from pathlib import Path


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


def build_heuristic_report(collected: list[dict], project_root: str = "") -> dict:
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
        "project_type": detect.get("project_type", "unknown"),
        "tech_stack": (detect.get("frameworks") or [])[:8],
        "entry_points": entry_points,
        "modules": modules[:10],
        "pages": pages,
        "notes": f"共 {scan.get('total_files', '?')} 个文件 / {scan.get('total_dirs', '?')} 个目录",
    }

    # ---------- goal ----------
    goal, goal_source = _extract_goal_from_readme(readme)

    # ---------- findings ----------
    if todo_search and todo_search.get("matches"):
        evs = [
            {"file": m["file"], "lines": str(m["line"]),
             "snippet": (m.get("snippet") or "")[:120], "note": "显式 TODO/FIXME 标记"}
            for m in todo_search["matches"][:10]
        ]
        files = todo_search.get("files_with_matches") or []
        findings.append({
            "id": "f_todo",
            "title": f"存在 {todo_search['total_matches_shown']} 处显式 TODO/FIXME 标记（涉及 {len(files)} 个文件）",
            "status": "confirmed_incomplete",
            "detail": "这些是作者亲自留下的未完成标记，属于最直接的未完成证据。",
            "area": "全局",
            "evidence": evs,
            "reasoning": "TODO/FIXME 注释由 search_project 在源码中实际匹配到。",
        })

    if deps_check and deps_check.get("ok") is False and not deps_check.get("skipped"):
        findings.append({
            "id": "f_deps",
            "title": "依赖未安装，构建与测试均无法运行",
            "status": "confirmed_incomplete",
            "area": "工程化",
            "evidence": [{
                "file": "package.json", "lines": None, "snippet": None,
                "note": "声明了依赖但 node_modules 不存在（run_project_check: deps_check 失败）",
            }],
            "reasoning": "deps_check 检查实际执行并确认 node_modules 缺失。",
        })
        suggestions.append({
            "title": "安装依赖并运行一次构建",
            "why_now": "依赖缺失使所有后续验证（构建/测试）都无法进行，这是恢复项目可运行性的第一块基石。",
            "evidence": [{"file": "package.json", "note": "依赖已声明但未安装"}],
            "related_files": ["package.json"],
            "depends_on": ["无"],
            "impact": "恢复构建能力基线；若构建报错，会立刻暴露最真实的阻塞点。",
        })

    checklist = _readme_checklist(readme)
    if checklist:
        done, todo = checklist
        findings.append({
            "id": "f_readme_plan",
            "title": f"README 规划清单：{done} 项已勾选 / {todo} 项未勾选",
            "status": "suspected_incomplete",
            "detail": "清单勾选状态反映作者意图，但勾选项与实际实现是否一致尚未逐项核实。",
            "area": "规划",
            "evidence": [{
                "file": "README.md", "lines": None,
                "note": f"checklist 中 {todo} 个未勾选项（如预算、图表、归档、导出）",
            }],
            "reasoning": "来自 README 实际文本；完成度对应关系需要进一步代码核实。",
        })

    if git and git.get("has_git"):
        last = git.get("last_commit") or {}
        days = last.get("days_ago")
        if days is not None and days > 30:
            findings.append({
                "id": "f_stale",
                "title": f"项目已搁置：最后一次提交约 {days // 30} 个月前（{days} 天）",
                "status": "unknown",
                "detail": "这是搁置时间的事实陈述；具体停在哪一步请结合 TODO 与规划清单判断。",
                "area": "全局",
                "evidence": [{
                    "file": ".git", "lines": None,
                    "snippet": f"{last.get('message')}",
                    "note": f"最后提交：{last.get('date')}（git log 实际读取）",
                }],
                "reasoning": "git log 显示最后提交时间距今较远。",
            })

    # 诚实示范：启发式模式无法验证的内容
    findings.append({
        "id": "f_runtime_unknown",
        "title": "各页面/模块的运行时行为与相互可达性尚未验证",
        "status": "unknown",
        "detail": "静态扫描无法确认页面是否实际可访问、功能是否端到端可用。",
        "area": "全局",
        "evidence": [],
        "reasoning": "需要安装依赖后运行构建/开发服务器验证（当前启发式模式未执行）。",
    })

    if not any(s.get("title", "").startswith("处理") for s in suggestions) and todo_search and todo_search.get("matches"):
        suggestions.append({
            "title": "按文件处理 TODO/FIXME 清单",
            "why_now": "这些是作者明确标记的未完成点，成本最低、收益最确定。",
            "evidence": [{"file": m["file"], "lines": str(m["line"])}
                         for m in todo_search["matches"][:3]],
            "related_files": sorted({m["file"] for m in todo_search["matches"]})[:6],
            "depends_on": ["建议先完成依赖安装（若构建验证需要）"],
            "impact": "消除最明确的未完成点，快速恢复项目完成度。",
        })

    # ---------- summary ----------
    bits = []
    ptype = detect.get("project_type", "未知类型")
    bits.append(f"项目为 {ptype}（技术栈：{'、'.join(detect.get('frameworks', [])[:5]) or '未知'}）。")
    bits.append(f"共 {scan.get('total_files', '?')} 个文件；"
                f"{project_map and ''}主要模块：{'、'.join(modules[:5]) or '未识别'}。")
    if git and git.get("has_git") and git.get("last_commit"):
        bits.append(f"Git 显示最后提交于 {git['last_commit'].get('relative', '未知时间前')}（{git['last_commit'].get('message')}）。")
    n_todo = todo_search.get("total_matches_shown", 0) if todo_search else 0
    bits.append(f"发现 {n_todo} 处 TODO/FIXME；" +
                ("依赖未安装，无法构建验证。" if deps_check and deps_check.get("ok") is False else "依赖状态未见异常。"))
    if checklist:
        bits.append(f"README 规划 {checklist[0] + checklist[1]} 项，其中 {checklist[1]} 项未勾选。")
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
