"""初始化测试 fixture 的 Git 历史（幂等，可重复执行）。

story-tree 是内置的"烂尾样例项目"：4 次提交、最后一次停在
"wip: 编辑器骨架（烂尾于此）"，日期倒填到约 5 个月前（触发"已搁置"判定）。

Git 仓库无法嵌套提交，因此 .git 不进版本库，跑测试前先执行本脚本：
    python tests/init_fixture_git.py
"""

import os
import subprocess
import sys
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "story-tree"

COMMITS = [
    ("2026-05-06T10:00:00+08:00", "init: 项目脚手架（Vite + React）",
     ["package.json", "vite.config.ts", ".gitignore", "src/main.tsx", "src/types/story.ts"]),
    ("2026-05-12T15:30:00+08:00", "feat: 故事数据层与 localStorage 存储",
     ["src/services/story.ts", "src/utils/storage.ts", "src/components/CoverPreview.tsx"]),
    ("2026-05-18T21:10:00+08:00", "feat: 首页与故事创建页",
     ["README.md", "src/pages/Home.tsx", "src/pages/CreateStory.tsx"]),
    ("2026-05-20T23:45:00+08:00", "wip: 编辑器骨架（烂尾于此）",
     ["src/pages/Editor.tsx", "src/pages/MyWorks.tsx", "src/App.tsx", "tests/story.test.ts"]),
]


def main() -> int:
    if (FIXTURE / ".git").exists():
        print(f"[skip] {FIXTURE} 已有 .git，无需初始化")
        return 0

    env = dict(os.environ)
    for date, message, files in COMMITS:
        subprocess.run(["git", "add", *files], cwd=FIXTURE, check=True)
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
        subprocess.run(
            ["git", "-c", "user.name=dev", "-c", "user.email=dev@example.com",
             "commit", "-q", "-m", message],
            cwd=FIXTURE, env=env, check=True,
        )
        print(f"[ok] {date[:10]}  {message}")

    n = subprocess.run(["git", "rev-list", "--count", "HEAD"],
                       cwd=FIXTURE, capture_output=True, text=True, check=True).stdout.strip()
    print(f"[done] 共 {n} 次提交，fixture 就绪")
    return 0


if __name__ == "__main__":
    sys.exit(main())
