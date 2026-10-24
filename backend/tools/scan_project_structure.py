"""Tool 1: scan_project_structure

扫描项目目录与文件结构，产出紧凑的目录树 + 关键文件存在性清单。
输出将直接进入 LLM 上下文，因此严格限制体积。
"""

from pathlib import Path

from tools.safety import is_ignored_dir, project_root_path

TOOL_NAME = "scan_project_structure"

# 关键文件存在性清单（存在即报 True）
KEY_FILES = [
    "package.json", "README.md", "readme.md", "README.zh-CN.md", "tsconfig.json",
    "vite.config.ts", "vite.config.js", "next.config.js", "next.config.ts",
    "requirements.txt", "pyproject.toml", "setup.py", "Pipfile",
    "pubspec.yaml", "build.gradle", "build.gradle.kts", "settings.gradle",
    "go.mod", "Cargo.toml", "Gemfile", "composer.json", "pom.xml",
    "Dockerfile", "docker-compose.yml", ".env.example", ".gitignore",
    "Makefile", "jest.config.js", "vitest.config.ts", "pytest.ini",
]

KEY_DIRS = [
    "src", "app", "pages", "components", "routes", "lib", "api", "services",
    "models", "utils", "hooks", "styles", "assets", "public", "static",
    "tests", "test", "__tests__", "e2e", "android", "ios", "web", "server",
    "backend", "frontend", "scripts", "docs", ".github", ".vscode",
]


def build_tree(root: Path, max_depth: int, max_lines: int) -> tuple[str, bool]:
    """生成文本目录树。返回 (tree_text, truncated)。"""
    lines: list[str] = []

    def walk(dir_path: Path, prefix: str, depth: int) -> None:
        if len(lines) >= max_lines or depth > max_depth:
            return
        try:
            children = sorted(dir_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except (PermissionError, OSError):
            return
        shown = 0
        for child in children:
            if len(lines) >= max_lines:
                return
            if child.is_dir():
                if is_ignored_dir(child.name):
                    continue
                if child.name.startswith(".") and child.name not in (".github", ".vscode"):
                    # .git 等隐藏目录在 key_files 中单独报告
                    continue
                lines.append(f"{prefix}{child.name}/")
                shown += 1
                walk(child, prefix + "  ", depth + 1)
            else:
                lines.append(f"{prefix}{child.name}")
                shown += 1
        total = len(children)
        if shown < total and len(lines) < max_lines:
            lines.append(f"{prefix}… ({total - shown} more)")

    walk(root, "", 1)
    truncated = len(lines) >= max_lines
    return "\n".join(lines), truncated


async def scan_project_structure(
    project_root: str,
    subpath: str = "",
    max_depth: int = 4,
) -> dict:
    """扫描项目结构。

    参数:
        subpath: 只扫描某个子目录（相对路径，默认整个项目）
        max_depth: 目录树最大深度（默认 4）
    """
    root = project_root_path(project_root)
    scan_root = root / subpath if subpath else root
    scan_root = scan_root.resolve()
    if not scan_root.exists() or not scan_root.is_dir():
        return {"error": f"目录不存在: {subpath or '.'}"}
    try:
        scan_root.relative_to(root)
    except ValueError:
        return {"error": "路径越界"}

    # 统计（跳过忽略目录）
    total_files = 0
    total_dirs = 0
    for p in scan_root.rglob("*"):
        rel_parts = p.relative_to(scan_root).parts
        if any(is_ignored_dir(part) for part in rel_parts[:-1]):
            continue
        if p.is_dir():
            total_dirs += 1
        elif p.is_file():
            total_files += 1

    tree, truncated = build_tree(scan_root, max_depth=max_depth, max_lines=300)

    top_level = []
    try:
        for child in sorted(scan_root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            name = child.name + ("/" if child.is_dir() else "")
            top_level.append(name)
    except (PermissionError, OSError):
        pass

    key_files_present = {name: (root / name).exists() for name in KEY_FILES}
    key_files_present[".git"] = (root / ".git").exists()
    key_dirs_present = {name: (root / name).is_dir() for name in KEY_DIRS}

    return {
        "root": str(root),
        "scanned": subpath or ".",
        "total_files": total_files,
        "total_dirs": total_dirs,
        "tree": tree,
        "tree_truncated": truncated,
        "top_level": top_level[:60],
        "key_files": {k: v for k, v in key_files_present.items() if v},
        "key_dirs": {k: v for k, v in key_dirs_present.items() if v},
    }
