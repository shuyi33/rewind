"""Tool 5: detect_project_type

基于项目内的实际文件证据判断技术栈，绝不凭空猜测。
返回判定结果 + 置信度 + 支撑证据（哪些文件/字段）。
"""

import json

from tools.safety import project_root_path

TOOL_NAME = "detect_project_type"


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _count_exts(root, top_n=8):
    exts = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        parts = p.relative_to(root).parts
        if any(seg in ("node_modules", ".git", "dist", "build", ".venv", "venv",
                       "__pycache__", ".dart_tool", ".gradle", "target") for seg in parts):
            continue
        ext = p.suffix.lower() or "(no ext)"
        exts[ext] = exts.get(ext, 0) + 1
    return dict(sorted(exts.items(), key=lambda kv: -kv[1])[:top_n])


def _node_project(root, pkg):
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    evidence = []
    frameworks = []
    language = "JavaScript"

    def has(name: str) -> bool:
        return name in deps

    if has("react"):
        frameworks.append(f"React {deps['react'].lstrip('^~')}")
        evidence.append("package.json dependencies.react")
    if has("vue"):
        frameworks.append(f"Vue {deps['vue'].lstrip('^~')}")
        evidence.append("package.json dependencies.vue")
    if has("svelte"):
        frameworks.append("Svelte")
        evidence.append("package.json dependencies.svelte")
    if has("next"):
        frameworks.append("Next.js")
        evidence.append("package.json dependencies.next")
    if has("vite") or (root / "vite.config.ts").exists() or (root / "vite.config.js").exists():
        if "Vite" not in frameworks:
            frameworks.append("Vite")
        evidence.append("vite 依赖或 vite.config.* 存在")
    if has("express"):
        frameworks.append("Express (Node 服务端)")
        evidence.append("package.json dependencies.express")
    if has("fastapi") is False and has("nest"):
        frameworks.append("NestJS")
        evidence.append("package.json dependencies.@nestjs/core")

    if has("typescript") or (root / "tsconfig.json").exists() or any(
        root.glob("src/**/*.ts*")
    ):
        language = "TypeScript"
        evidence.append("tsconfig.json 或 TypeScript 依赖存在")

    # React 判定补充：存在 .tsx 文件
    tsx_count = sum(1 for _ in root.rglob("src/**/*.tsx")) if (root / "src").exists() else 0
    if tsx_count and "react" not in str(frameworks).lower():
        frameworks.append("疑似 React（发现 .tsx 组件文件）")
        evidence.append(f"src/ 下存在 {tsx_count} 个 .tsx 文件")

    pm = "npm"
    if (root / "pnpm-lock.yaml").exists():
        pm = "pnpm"
    elif (root / "yarn.lock").exists():
        pm = "yarn"
    elif (root / "bun.lockb").exists() or (root / "bun.lock").exists():
        pm = "bun"

    scripts = {k: v for k, v in (pkg.get("scripts") or {}).items() if k in
               ("dev", "build", "test", "lint", "start", "typecheck", "preview")}

    if not frameworks:
        # 只有 package.json，无框架特征
        if any(root.glob("server.js")) or any(root.glob("index.js")):
            return {
                "project_type": "Node.js",
                "confidence": "medium",
                "language": language,
                "frameworks": [],
                "package_manager": pm,
                "scripts": scripts,
                "evidence": evidence or ["package.json 存在，无框架特征依赖"],
            }
        return {
            "project_type": "Node 项目（未识别框架）",
            "confidence": "low",
            "language": language,
            "frameworks": [],
            "package_manager": pm,
            "scripts": scripts,
            "evidence": ["仅 package.json 存在"],
        }

    return {
        "project_type": " + ".join(frameworks[:2]),
        "confidence": "high" if evidence else "medium",
        "language": language,
        "frameworks": frameworks,
        "package_manager": pm,
        "scripts": scripts,
        "evidence": evidence,
    }


def _python_project(root):
    evidence = []
    frameworks = []
    deps_text = ""

    req = root / "requirements.txt"
    pyproject = root / "pyproject.toml"
    if req.exists():
        deps_text = req.read_text(encoding="utf-8", errors="ignore")
        evidence.append("requirements.txt 存在")
    elif pyproject.exists():
        deps_text = pyproject.read_text(encoding="utf-8", errors="ignore")
        evidence.append("pyproject.toml 存在")

    low = deps_text.lower()
    if "fastapi" in low:
        frameworks.append("FastAPI")
        evidence.append("依赖中包含 fastapi")
    elif "flask" in low:
        frameworks.append("Flask")
        evidence.append("依赖中包含 flask")
    elif "django" in low:
        frameworks.append("Django")
        evidence.append("依赖中包含 django")
    if "tkinter" in low or "PyQt" in deps_text:
        frameworks.append("桌面 GUI")
    if "pytest" in low:
        evidence.append("依赖中包含 pytest（测试框架）")

    return {
        "project_type": "Python" + (f"（{frameworks[0]}）" if frameworks else ""),
        "confidence": "high" if frameworks else "medium",
        "language": "Python",
        "frameworks": frameworks,
        "evidence": evidence,
    }


async def detect_project_type(project_root: str) -> dict:
    """判断项目类型与技术栈（基于文件证据）。"""
    root = project_root_path(project_root)

    pkg_path = root / "package.json"
    if pkg_path.exists():
        pkg = _read_json(pkg_path)
        if isinstance(pkg, dict):
            result = _node_project(root, pkg)
            result["file_ext_counts"] = _count_exts(root)
            return result

    for marker, getter in (
        ("requirements.txt", lambda: _python_project(root)),
        ("pyproject.toml", lambda: _python_project(root)),
        ("setup.py", lambda: _python_project(root)),
    ):
        if (root / marker).exists():
            result = getter()
            result["file_ext_counts"] = _count_exts(root)
            return result

    if (root / "pubspec.yaml").exists():
        pub = (root / "pubspec.yaml").read_text(encoding="utf-8", errors="ignore")
        return {
            "project_type": "Flutter",
            "confidence": "high",
            "language": "Dart",
            "frameworks": ["Flutter"],
            "evidence": ["pubspec.yaml 存在" + ("（含 flutter 依赖）" if "flutter:" in pub else "")],
            "file_ext_counts": _count_exts(root),
        }

    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        has_manifest = (root / "app/src/main/AndroidManifest.xml").exists()
        return {
            "project_type": "Android",
            "confidence": "high" if has_manifest else "medium",
            "language": "Kotlin/Java",
            "frameworks": ["Gradle"],
            "evidence": ["build.gradle 存在" + ("；AndroidManifest.xml 存在" if has_manifest else "")],
            "file_ext_counts": _count_exts(root),
        }

    for marker, ptype in (("go.mod", "Go"), ("Cargo.toml", "Rust"),
                          ("Gemfile", "Ruby"), ("composer.json", "PHP"), ("pom.xml", "Java")):
        if (root / marker).exists():
            return {
                "project_type": ptype,
                "confidence": "high",
                "language": ptype,
                "frameworks": [],
                "evidence": [f"{marker} 存在"],
                "file_ext_counts": _count_exts(root),
            }

    # 无构建配置：可能是普通 HTML 站点
    html_files = list(root.glob("*.html")) + list(root.glob("*.htm"))
    if html_files and not (root / "package.json").exists():
        return {
            "project_type": "静态 HTML/CSS/JS 站点",
            "confidence": "medium",
            "language": "HTML/JavaScript",
            "frameworks": [],
            "evidence": [f"根目录存在 HTML 文件: {', '.join(p.name for p in html_files[:3])}"],
            "file_ext_counts": _count_exts(root),
        }

    return {
        "project_type": "unknown",
        "confidence": "low",
        "language": "unknown",
        "frameworks": [],
        "evidence": ["未发现常见项目标记文件（package.json / requirements.txt / pubspec.yaml 等）"],
        "file_ext_counts": _count_exts(root),
        "note": "项目类型无法确认，但结构扫描与其他工具仍可继续分析。",
    }
