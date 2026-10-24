"""工具层共享的安全与过滤规则。"""

from pathlib import Path

# 扫描时跳过的目录（依赖产物 / 构建输出 / IDE 缓存）
IGNORED_DIRS = {
    "node_modules", ".git", "dist", "build", "out", ".next", ".nuxt", ".output",
    ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", "coverage", ".idea", ".vscode", ".dart_tool",
    ".gradle", "target", "vendor", "Pods", ".expo", ".turbo", ".cache",
    ".terraform", ".yarn", "bower_components", "site-packages",
}

# 二进制/非文本文件扩展名（读取与搜索时跳过）
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svgz", ".bmp",
    ".pdf", ".zip", ".gz", ".tar", ".rar", ".7z", ".bz2", ".xz",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".class", ".jar", ".war",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".avi", ".mov", ".flv", ".wmv", ".wav", ".aiff",
    ".sqlite", ".db", ".pyc", ".pyo", ".o", ".a", ".wasm", ".map",
    ".psd", ".ai", ".sketch", ".fig", ".dmg", ".iso", ".apk", ".ipa",
}

MAX_FILE_BYTES = 200_000  # 单文件读取上限 200KB


def project_root_path(project_root: str) -> Path:
    return Path(project_root).expanduser().resolve()


def resolve_in_project(project_root: str, rel_path: str) -> Path | None:
    """把相对路径安全解析到项目内；越界（路径逃逸）返回 None。"""
    root = project_root_path(project_root)
    target = (root / rel_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def is_ignored_dir(name: str) -> bool:
    return name in IGNORED_DIRS


def looks_binary(path: Path, peek_bytes: int = 1024) -> bool:
    if path.suffix.lower() in BINARY_EXTS:
        return True
    try:
        with open(path, "rb") as f:
            chunk = f.read(peek_bytes)
    except OSError:
        return True
    return b"\x00" in chunk


def iter_project_files(project_root: str, root_rel: str = ""):
    """非递归列出 root_rel 下的一层内容（排序：目录在前）。"""
    base = resolve_in_project(project_root, root_rel) if root_rel else project_root_path(project_root)
    if base is None or not base.is_dir():
        return []
    entries = []
    try:
        for child in base.iterdir():
            entries.append(child)
    except (PermissionError, OSError):
        return []
    dirs = sorted((c for c in entries if c.is_dir() and not is_ignored_dir(c.name)), key=lambda p: p.name.lower())
    files = sorted((c for c in entries if c.is_file()), key=lambda p: p.name.lower())
    return dirs + files
