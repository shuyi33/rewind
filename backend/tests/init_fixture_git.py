"""初始化测试 fixture 的 Git 历史（幂等，可重复执行）。

pocket-ledger 是内置的"烂尾样例项目"：4 次提交、最后一次停在
"wip: 图表页骨架（烂尾于此）"，日期倒填到约 5 个月前（触发"已搁置"判定）。

Git 仓库无法嵌套提交，因此 .git 不进版本库，跑测试前先执行本脚本：
    python tests/init_fixture_git.py
"""

import os
import subprocess
import sys
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "pocket-ledger"

COMMITS = [
    ("2026-05-06T10:00:00+08:00", "init: 项目脚手架（Vite + React）",
     ["package.json", "vite.config.ts", ".gitignore", "src/main.tsx", "src/types/ledger.ts"]),
    ("2026-05-12T15:30:00+08:00", "feat: 账目数据层与 localStorage 存储",
     ["src/services/ledger.ts", "src/utils/storage.ts", "src/components/BudgetBadge.tsx"]),
    ("2026-05-18T21:10:00+08:00", "feat: 首页与记一笔页",
     ["README.md", "src/pages/Home.tsx", "src/pages/CreateEntry.tsx"]),
    ("2026-05-20T23:45:00+08:00", "wip: 图表页骨架（烂尾于此）",
     ["src/pages/Charts.tsx", "src/pages/Archive.tsx", "src/App.tsx", "tests/ledger.test.ts"]),
]


def main() -> int:
    if (FIXTURE / ".git").exists():
        print(f"[skip] {FIXTURE} 已有 .git，无需初始化")
        return 0

    # 必须先 init 独立仓库——否则 git add 会向上找到外层主仓库，污染其历史
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=FIXTURE, check=True)

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
