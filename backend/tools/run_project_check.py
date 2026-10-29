"""Tool 6: run_project_check

安全地运行项目的基础检查（build / test / lint / typecheck / deps_check）。

安全设计（不允许执行任意命令）：
1. LLM 只能从固定 check 类型中选择（build/test/lint/typecheck/deps_check），
   不接受任何自由形式的命令字符串。
2. 具体命令由"项目类型 + package.json scripts"映射生成，全部来自白名单。
3. 强制超时、输出截断、工作目录锁定在项目内。
"""

import asyncio
import os
import shutil
import subprocess

from config import settings
from tools.safety import project_root_path

TOOL_NAME = "run_project_check"

CHECK_KINDS = ("build", "test", "lint", "typecheck", "deps_check")

# 命令前缀白名单（双保险：即使映射逻辑被改坏，也不会执行任意命令）
_ALLOWED_PREFIXES = (
    ("npm", "run"),
    ("npx", "tsc"),
    ("python", "-m"),
    ("pytest",),
    ("pip", "list"),
)


def _resolve_cmd(cmd: list[str]) -> list[str] | None:
    """解析命令完整路径。Windows 上 npm 实际是 npm.cmd，不带 shell 时必须显式解析。"""
    exe = shutil.which(cmd[0])
    return [exe, *cmd[1:]] if exe else None


async def _run(cmd: list[str], cwd: str, M) -> dict:
    def run():
        resolved = _resolve_cmd(cmd)
        if resolved is None:
            return 127, "", M["cmd_missing"].format(c=cmd[0])
        # 沿用系统 PATH（npm 可能装在任意目录），其余变量保持最小集
        env = {k: os.environ.get(k, "") for k in ("PATH", "SystemRoot", "SystemDrive", "TEMP", "TMP")}
        env.update({"HOME": cwd, "LANG": "C.UTF-8", "NO_COLOR": "1"})
        try:
            proc = subprocess.run(
                resolved, cwd=cwd, capture_output=True,
                encoding="utf-8", errors="replace",
                timeout=settings.CHECK_TIMEOUT_SECONDS,
                env=env,
            )
            return proc.returncode, proc.stdout or "", proc.stderr or ""
        except FileNotFoundError:
            return 127, "", f"命令不可用: {cmd[0]}"
        except subprocess.TimeoutExpired:
            return 124, "", M["timeout"].format(n=settings.CHECK_TIMEOUT_SECONDS)


    limit = settings.CHECK_OUTPUT_LIMIT
    output = (out + ("\n--stderr--\n" + err if err.strip() else "")).strip()
    if len(output) > limit:
        output = output[:limit] + M["truncated"].format(n=len(output))
    return {
        "ok": code == 0,
        "exit_code": code,
        "output": output if output else "(无输出)",
    }


def _pkg(root, key):
    import json
    try:
        with open(root / "package.json", encoding="utf-8") as f:
            pkg = json.load(f)
        return pkg.get(key) or {}
    except (OSError, json.JSONDecodeError):
        return None


_DETAILS = {
    "zh": {
        "invalid_root": "项目路径无效: {p}",
        "bad_kind": "check 必须是 {kinds} 之一（不允许任意命令）",
        "not_node": "不是 Node 项目（无 package.json），也不是 Python 项目，跳过运行检查",
        "no_script": "package.json 中没有 {k} 脚本",
        "no_ts": "未找到 TypeScript 配置或 typecheck 脚本",
        "no_pytest": "未找到 pytest 配置",
        "no_py_lint": "Python lint（ruff/flake8）未纳入白名单",
        "deps_missing": "依赖未安装（node_modules 不存在）。构建/测试检查将无法运行，这本身是重要证据。",
        "deps_ok": "依赖已安装（node_modules 存在）",
        "unknown_kind": "未知检查类型: {k}",
        "not_whitelist": "命令 {c} 不在白名单内，拒绝执行",
        "cmd_missing": "命令不可用: {c}",
        "timeout": "超时（>{n}s）被终止",
        "no_output": "(无输出)",
        "truncated": "\n…（截断，共 {n} 字符）",
    },
    "en": {
        "invalid_root": "invalid project path: {p}",
        "bad_kind": "check must be one of {kinds} (arbitrary commands are not allowed)",
        "not_node": "Not a Node project (no package.json) nor a Python project — check skipped",
        "no_script": "no {k} script in package.json",
        "no_ts": "no TypeScript config or typecheck script found",
        "no_pytest": "no pytest config found",
        "no_py_lint": "Python lint (ruff/flake8) is not whitelisted",
        "deps_missing": "Dependencies not installed (node_modules missing). Build/test checks cannot run — that itself is evidence.",
        "deps_ok": "Dependencies installed (node_modules present)",
        "unknown_kind": "unknown check kind: {k}",
        "not_whitelist": "command {c} is not whitelisted — refused",
        "cmd_missing": "command not available: {c}",
        "timeout": "timed out (>{n}s), terminated",
        "no_output": "(no output)",
        "truncated": "\n… (truncated, {n} chars total)",
    },
}


async def run_project_check(project_root: str, check: str = "build", lang: str = "zh") -> dict:
    M = _DETAILS.get(lang, _DETAILS["zh"])
    root = project_root_path(project_root)
    if root is None:
        return {"error": M["invalid_root"].format(p=project_root)}

    kind = (check or "").strip().lower()
    if kind not in CHECK_KINDS:
        return {"error": M["bad_kind"].format(kinds=", ".join(CHECK_KINDS))}

    # ---------- Python 项目 ----------
    if not (root / "package.json").exists() and (
        (root / "pyproject.toml").exists() or (root / "requirements.txt").exists()
    ):
        match kind:
            case "deps_check":
                result = await _run(["pip", "list"], str(root), M)
            case "test":
                if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
                    result = await _run(["pytest", "--collect-only", "-q"], str(root), M)
                else:
                    return {"check": kind, "ok": False, "skipped": True,
                            "details": M["no_pytest"]}
            case "build" | "typecheck":
                result = await _run(["python", "-m", "compileall", "-q", "."], str(root), M)
            case "lint":
                return {"check": kind, "ok": False, "skipped": True,
                        "details": M["no_py_lint"]}
            case _:
                return {"error": M["unknown_kind"].format(k=kind)}
        result.update({"check": kind, "project": "python"})
        return result

    # ---------- Node 项目 ----------
    scripts = _pkg(root, "scripts")
    if scripts is None:
        return {"check": kind, "ok": False, "skipped": True,
                "details": M["not_node"]}

    deps = {**( _pkg(root, "dependencies") or {}), **(_pkg(root, "devDependencies") or {})}
    has_typescript = "typescript" in deps

    match kind:
        case "deps_check":
            if not (root / "node_modules").exists():
                return {"check": kind, "ok": False, "project": "node",
                        "details": M["deps_missing"]}
            return {"check": kind, "ok": True, "project": "node",
                    "details": M["deps_ok"]}
        case "build":
            if not scripts.get("build"):
                return {"check": kind, "ok": False, "skipped": True, "project": "node",
                        "details": M["no_script"].format(k="build")}
            cmd = ["npm", "run", "build"]
        case "test":
            if not scripts.get("test"):
                return {"check": kind, "ok": False, "skipped": True, "project": "node",
                        "details": M["no_script"].format(k="test")}
            cmd = ["npm", "run", "test"]
        case "lint":
            if not scripts.get("lint"):
                return {"check": kind, "ok": False, "skipped": True, "project": "node",
                        "details": M["no_script"].format(k="lint")}
            cmd = ["npm", "run", "lint"]
        case "typecheck":
            if scripts.get("typecheck"):
                cmd = ["npm", "run", "typecheck"]
            elif (root / "tsconfig.json").exists() and has_typescript:
                cmd = ["npx", "tsc", "--noEmit"]
            else:
                return {"check": kind, "ok": False, "skipped": True, "project": "node",
                        "details": M["no_ts"]}
        case _:
            return {"error": f"未知检查类型: {kind}"}

    # 白名单双保险
    if tuple(cmd[:2]) not in _ALLOWED_PREFIXES and tuple(cmd[:3]) not in _ALLOWED_PREFIXES:
        return {"error": M["not_whitelist"].format(c=cmd)}

    result = await _run(cmd, str(root), M)
    result.update({"check": kind, "command": " ".join(cmd), "project": "node"})
    return result
