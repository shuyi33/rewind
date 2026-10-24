"""项目路径校验：确认路径存在、是目录，并附带 Git 状态等基础信息。"""

from pathlib import Path

from models.schemas import ValidatePathResponse


def validate_path(raw: str) -> ValidatePathResponse:
    path = (raw or "").strip().strip('"').strip("'")
    if not path:
        return ValidatePathResponse(valid=False, path=raw or "", error="路径不能为空")
    try:
        root = Path(path).expanduser().resolve()
    except (OSError, ValueError):
        return ValidatePathResponse(valid=False, path=path, error="路径无法解析")

    if not root.exists():
        return ValidatePathResponse(valid=False, path=str(root), error="路径不存在（本机）")
    if not root.is_dir():
        return ValidatePathResponse(valid=False, path=str(root), is_dir=False,
                                    error="目标不是文件夹")

    return ValidatePathResponse(
        valid=True,
        path=str(root),
        name=root.name,
        is_dir=True,
        has_git=(root / ".git").exists(),
    )
