"""pydantic 数据契约（与前端 src/types/index.ts 一一对应）。"""

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- 报告结构

class Evidence(BaseModel):
    file: str
    lines: str | None = None
    snippet: str | None = None
    note: str | None = None


FindingStatus = Literal[
    "confirmed_done", "confirmed_incomplete", "suspected_incomplete", "unknown"
]


class Finding(BaseModel):
    id: str
    title: str
    status: FindingStatus
    detail: str | None = None
    area: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    reasoning: str | None = None


class ProjectMap(BaseModel):
    name: str | None = None
    project_type: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    pages: list[str] = Field(default_factory=list)
    notes: str | None = None


class Suggestion(BaseModel):
    title: str
    why_now: str
    evidence: list[Evidence] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    impact: str | None = None


# ---------------------------------------------------------------- API 请求/响应

class StartAnalysisRequest(BaseModel):
    path: str
    goal: str | None = None
    lang: str = "zh"


class StartAnalysisResponse(BaseModel):
    report_id: str
    project_id: str


class ValidatePathRequest(BaseModel):
    path: str


class ValidatePathResponse(BaseModel):
    valid: bool
    path: str
    name: str | None = None
    is_dir: bool = False
    has_git: bool = False
    error: str | None = None
