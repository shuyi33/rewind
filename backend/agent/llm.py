"""LLM 客户端封装：OpenAI-compatible API + 本地 Mock 引擎。

两种引擎实现同一接口，Agent Loop 无感知切换：
- RealLLM：AsyncOpenAI（base_url / api_key / model 全部来自环境变量）
- MockLLM：脚本化工具调度 + 基于真实工具结果的启发式报告，
  用于无 API Key 的本地开发与测试（产出的是真证据，不是假数据）。
"""

import json

from openai import AsyncOpenAI

from config import settings


class LLMResponse:
    """统一的模型响应：文本内容 + 工具调用请求。"""

    def __init__(self, content: str | None = None,
                 tool_calls: list[dict] | None = None):
        self.content = content
        self.tool_calls = tool_calls or []  # [{name, arguments: dict}]


class RealLLM:
    """OpenAI-compatible 真实模型。"""

    def __init__(self):
        self._client = AsyncOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
        )
        self.model = settings.LLM_MODEL

    async def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools if tools else None,
            temperature=0.2,
        )
        choice = resp.choices[0]
        msg = choice.message
        calls = []
        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            calls.append({"name": tc.function.name, "arguments": args})
        return LLMResponse(content=msg.content, tool_calls=calls)


class MockLLM:
    """Mock 引擎：按状态机调度工具，最后基于真实结果生成报告。

    关键原则：Mock 不伪造任何结论——所有 finding 的证据均来自
    工具真实返回；无法判断的条目显式标记 unknown。
    """

    def __init__(self, lang: str = 'zh'):
        self.lang = lang
        self._plan_pos = 0
        self._collected: list[dict] = []  # [{name, arguments, result}]
        self._pending: dict | None = None  # 已发出、等待结果的调用

    def _next_call(self, project_hint: dict) -> dict | None:
        """根据已收集的信息决定下一个工具调用。"""
        plan = [
            {"name": "detect_project_type", "arguments": {}},
            {"name": "scan_project_structure", "arguments": {}},
            {"name": "analyze_git_history", "arguments": {}},
            {"name": "search_project", "arguments": {"query": "TODO|FIXME", "regex": True}},
            {"name": "read_project_file", "arguments": {"file_path": "README.md", "max_lines": 120}},
            {"name": "run_project_check", "arguments": {"check": "deps_check"}},
        ]
        while self._plan_pos < len(plan):
            step = plan[self._plan_pos]
            self._plan_pos += 1
            # 条件跳过
            if step["name"] == "read_project_file":
                scan = next((c["result"] for c in self._collected
                             if c["name"] == "scan_project_structure"), {})
                if "README.md" not in (scan.get("key_files") or {}):
                    continue
            return step
        return None

    async def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        # 从 messages 中收集工具结果（OpenAI role=tool 消息），与发出的调用参数配对
        if messages and messages[-1].get("role") == "tool":
            name = messages[-1].get("name", "")
            try:
                result = json.loads(messages[-1]["content"])
            except (json.JSONDecodeError, TypeError):
                result = {}
            pending = self._pending or {}
            self._collected.append({
                "name": name,
                "arguments": pending.get("arguments", {}) if pending.get("name") == name else {},
                "result": result,
            })
            self._pending = None

        next_call = self._next_call({})
        if next_call:
            self._pending = next_call
            return LLMResponse(tool_calls=[next_call])

        # 计划完成 → 生成最终报告（启发式，基于真实证据）
        from agent.heuristic import build_heuristic_report
        report = build_heuristic_report(self._collected, lang=self.lang)
        return LLMResponse(content="```json\n" + json.dumps(report, ensure_ascii=False) + "\n```")


def get_llm(lang: str = 'zh'):
    if settings.MOCK_LLM:
        return MockLLM(lang)
    if not settings.LLM_API_KEY:
        raise RuntimeError("未配置 LLM_API_KEY（或在环境变量 REWIND_MOCK_LLM=1 启用本地 Mock）")
    return RealLLM()
