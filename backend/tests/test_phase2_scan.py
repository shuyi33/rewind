"""Phase 2 验证：项目扫描（结构 + 类型识别）在真实 fixture 上运行。"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.registry import execute_tool  # noqa: E402

FIXTURE = str(Path(__file__).parent / "fixtures" / "pocket-ledger")


async def main():
    print("=" * 60)
    print("Tool: detect_project_type")
    print("=" * 60)
    r = await execute_tool(FIXTURE, "detect_project_type", {})
    print(json.dumps(r["result"], ensure_ascii=False, indent=2))

    print()
    print("=" * 60)
    print("Tool: scan_project_structure")
    print("=" * 60)
    r = await execute_tool(FIXTURE, "scan_project_structure", {})
    res = r["result"]
    print("ok:", r["ok"], "| duration:", r["duration_ms"], "ms")
    print("total_files:", res["total_files"], "| total_dirs:", res["total_dirs"])
    print("key_files:", res["key_files"])
    print("key_dirs:", res["key_dirs"])
    print("top_level:", res["top_level"])
    print("--- tree ---")
    print(res["tree"])

    # 断言核心证据被扫描到
    assert res["key_files"].get("package.json") is True, "package.json 应被发现"
    assert res["key_files"].get("README.md") is True, "README.md 应被发现"
    assert res["key_files"].get(".git") is True, ".git 应被发现"
    assert "src/pages/" in res["tree"] or "src/" in res["tree"], "src 目录应在树中"
    assert "node_modules" not in res["tree"], "node_modules 不应出现"
    assert r["result"]["key_dirs"].get("tests") is True, "tests 目录应被发现"

    print()
    print("[PASS] Phase 2 扫描验证全部通过")


if __name__ == "__main__":
    asyncio.run(main())
