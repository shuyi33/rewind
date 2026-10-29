"""工具注册表：Agent Loop 的工具调度中枢。

每个工具提供：
- name / description / parameters：OpenAI function calling 的 JSON Schema
- handler: 异步执行函数（统一签名 (project_root, **args) -> dict）
- phase: 工具对应的前端扫描阶段（真实进度，非假百分比）
"""

import inspect
import time
import traceback

from tools.analyze_git_history import analyze_git_history
from tools.detect_project_type import detect_project_type, TOOL_NAME as T_DETECT
from tools.read_project_file import read_project_file
from tools.run_project_check import run_project_check
from tools.scan_project_structure import scan_project_structure, TOOL_NAME as T_SCAN
from tools.search_project import search_project


def _phase_map():
    return {
        "detect_project_type": "detect",
        "scan_project_structure": "structure",
        "analyze_git_history": "git",
        "search_project": "evidence",
        "read_project_file": "evidence",
        "run_project_check": "check",
    }


PHASE_LABELS = {
    "detect": "正在识别项目类型",
    "structure": "正在分析文件结构",
    "git": "正在检查 Git 历史",
    "evidence": "正在寻找未完成内容",
    "check": "正在运行项目检查",
    "report": "正在建立项目状态",
}


TOOLS: dict[str, dict] = {
    T_SCAN: {
        "description": (
            "扫描项目目录与文件结构，返回目录树、关键文件存在性"
            "（package.json/README/tests 等定位）。通常是分析的第一步。"
            "可选 subpath 深入某个子目录。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "subpath": {
                    "type": "string",
                    "description": "要扫描的子目录（相对路径，默认整个项目根）",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "目录树最大深度，默认 4",
                    "minimum": 1,
                    "maximum": 8,
                },
            },
        },
        "handler": scan_project_structure,
    },
    T_DETECT: {
        "description": (
            "判断项目技术栈与类型（React/Vue/Python/Flutter/Android 等），"
            "返回判定证据与 package.json scripts。在 scan 之后调用可帮助解读结构。"
        ),
        "parameters": {"type": "object", "properties": {}},
        "handler": detect_project_type,
    },
    "read_project_file": {
        "description": (
            "读取项目内一个文本文件的指定行范围（带行号）。"
            "用于查看 README、配置、源码具体实现等。"
            "file_path 必须是项目内相对路径，路径越界会被拒绝。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "项目内相对路径，如 src/pages/Home.tsx"},
                "start_line": {"type": "integer", "description": "起始行（默认 1）"},
                "max_lines": {"type": "integer", "description": "最多返回行数（默认 400）"},
            },
            "required": ["file_path"],
        },
        "handler": read_project_file,
    },
    "search_project": {
        "description": (
            "在项目文本文件中搜索关键词或正则：TODO/FIXME 注释、"
            "组件或函数的引用、特定标识符等。可选 file_glob 限定文件类型（如 *.tsx）。"
            "纯字面量搜索默认关闭正则语法（regex=false），需要正则时显式传 regex=true。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索内容，如 'TODO' 或 'CoverPreview'"},
                "file_glob": {"type": "string", "description": "限定文件名模式，如 *.tsx / *.py，默认全部"},
                "regex": {"type": "boolean", "description": "是否把 query 当作正则（默认 false）"},
                "max_results": {"type": "integer", "description": "最多返回匹配数（默认 50）"},
            },
            "required": ["query"],
        },
        "handler": search_project,
    },
    "analyze_git_history": {
        "description": (
            "读取 Git 历史：提交记录、最近改动文件、分支、未提交变更、"
            "最后提交时间与距今间隔。无 Git 仓库时会明确说明。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "max_commits": {"type": "integer", "description": "返回最近 N 条提交（默认 30）"},
            },
        },
        "handler": analyze_git_history,
    },
    "run_project_check": {
        "description": (
            "安全运行项目基础检查（不允许任意命令）。check 只能是: "
            "build / test / lint / typecheck / deps_check。"
            "自动跳过不适用的检查并说明原因（如无 test 脚本）。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "check": {"type": "string", "enum": ["build", "test", "lint", "typecheck", "deps_check"]},
            },
            "required": ["check"],
        },
        "handler": run_project_check,
    },
}


def tool_specs() -> list[dict]:
    """输出 OpenAI function calling 的 tools 列表。"""
    specs = []
    for name, meta in TOOLS.items():
        specs.append({
            "type": "function",
            "function": {
                "name": name,
                "description": meta["description"],
                "parameters": meta["parameters"],
            },
        })
    return specs


def phase_of(tool_name: str) -> str:
    return _phase_map().get(tool_name, "evidence")


async def execute_tool(project_root: str, tool_name: str, args: dict, lang: str = "zh") -> dict:
    """统一执行入口。返回 {ok, result | error, duration_ms, phase}。"""
    meta = TOOLS.get(tool_name)
    if not meta:
        return {"ok": False, "error": f"未知工具: {tool_name}", "duration_ms": 0,
                "phase": "evidence"}
    start = time.monotonic()
    try:
        cleaned = {k: v for k, v in (args or {}).items() if v is not None}
        handler = meta["handler"]
        if "lang" in inspect.signature(handler).parameters:
            cleaned.setdefault("lang", lang)
        result = await handler(project_root, **cleaned)
        duration = int((time.monotonic() - start) * 1000)
        return {"ok": "error" not in result, "result": result,
                "error": result.get("error"), "duration_ms": duration,
                "phase": phase_of(tool_name)}
    except TypeError as e:
        # 参数不匹配（LLM 传错参数）
        return {"ok": False, "error": f"参数错误: {e}", "duration_ms": 0,
                "phase": phase_of(tool_name)}
    except Exception as e:  # noqa: BLE001 — 工具层兜底，不允许击穿 Agent Loop
        traceback.print_exc()
        return {"ok": False, "error": f"工具执行异常: {e}",
                "duration_ms": int((time.monotonic() - start) * 1000),
                "phase": phase_of(tool_name)}
