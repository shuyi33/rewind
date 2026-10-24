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


async def _run(cmd: list[str], cwd: str) -> dict:
    def run():
        resolved = _resolve_cmd(cmd)
        if resolved is None:
            return 127, "", f"命令不可用: {cmd[0]}"
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
            return 124, "", f"超时（>{settings.CHECK_TIMEOUT_SECONDS}s）被终止"

    code, out, err = await asyncio.to_thread(run)
    limit = settings.CHECK_OUTPUT_LIMIT
    output = (out + ("\n--stderr--\n" + err if err.strip() else "")).strip()
    if len(output) > limit:
        output = output[:limit] + f"\n…（截断，共 {len(output)} 字符）"
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


async def run_project_check(project_root: str, check: str = "build") -> dict:
    root = project_root_path(project_root)
    if root is None:
        return {"error": f"项目路径无效: {project_root}"}

    kind = (check or "").strip().lower()
    if kind not in CHECK_KINDS:
        return {"error": f"check 必须是 {', '.join(CHECK_KINDS)} 之一（不允许任意命令）"}

    # ---------- Python 项目 ----------
    if not (root / "package.json").exists() and (
        (root / "pyproject.toml").exists() or (root / "requirements.txt").exists()
    ):
        match kind:
            case "deps_check":
                result = await _run(["pip", "list"], str(root))
            case "test":
                if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
                    result = await _run(["pytest", "--collect-only", "-q"], str(root))
                else:
                    return {"check": kind, "ok": False, "skipped": True,
                            "details": "未找到 pytest 配置"}
            case "build" | "typecheck":
                result = await _run(["python", "-m", "compileall", "-q", "."], str(root))
            case "lint":
                return {"check": kind, "ok": False, "skipped": True,
                        "details": "Python lint（ruff/flake8）未纳入白名单"}
            case _:
                return {"error": f"未知检查类型: {kind}"}
        result.update({"check": kind, "project": "python"})
        return result

    # ---------- Node 项目 ----------
    scripts = _pkg(root, "scripts")
    if scripts is None:
        return {"check": kind, "ok": False, "skipped": True,
                "details": "不是 Node 项目（无 package.json），也不是 Python 项目，跳过运行检查"}

    deps = {**( _pkg(root, "dependencies") or {}), **(_pkg(root, "devDependencies") or {})}
    has_typescript = "typescript" in deps

    match kind:
        case "deps_check":
            if not (root / "node_modules").exists():
                return {"check": kind, "ok": False, "project": "node",
                        "details": "依赖未安装（node_modules 不存在）。"
                                   "构建/测试检查将无法运行，这本身是重要证据。"}
            return {"check": kind, "ok": True, "project": "node",
                    "details": "依赖已安装（node_modules 存在）"}
        case "build":
            if not scripts.get("build"):
                return {"check": kind, "ok": False, "skipped": True, "project": "node",
                        "details": "package.json 中没有 build 脚本"}
            cmd = ["npm", "run", "build"]
        case "test":
            if not scripts.get("test"):
                return {"check": kind, "ok": False, "skipped": True, "project": "node",
                        "details": "package.json 中没有 test 脚本"}
            cmd = ["npm", "run", "test"]
        case "lint":
            if not scripts.get("lint"):
                return {"check": kind, "ok": False, "skipped": True, "project": "node",
                        "details": "package.json 中没有 lint 脚本"}
            cmd = ["npm", "run", "lint"]
        case "typecheck":
            if scripts.get("typecheck"):
                cmd = ["npm", "run", "typecheck"]
            elif (root / "tsconfig.json").exists() and has_typescript:
                cmd = ["npx", "tsc", "--noEmit"]
            else:
                return {"check": kind, "ok": False, "skipped": True, "project": "node",
                        "details": "未找到 TypeScript 配置或 typecheck 脚本"}
        case _:
            return {"error": f"未知检查类型: {kind}"}

    # 白名单双保险
    if tuple(cmd[:2]) not in _ALLOWED_PREFIXES and tuple(cmd[:3]) not in _ALLOWED_PREFIXES:
        return {"error": f"命令 {cmd} 不在白名单内，拒绝执行"}

    result = await _run(cmd, str(root))
    result.update({"check": kind, "command": " ".join(cmd), "project": "node"})
    return result
