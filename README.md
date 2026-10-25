# Rewind · 回溯

> Project Recovery Agent —— 把一个很久没碰的项目丢给它，它帮你重新理解这个项目现在到底是什么状态。

你电脑里是不是也有做了一半、几个月没碰的项目？再次打开时已经忘了当初想做什么、做到了哪里、为什么停下来、下一步从哪开始。

Rewind 不要求你重新解释整个项目。它主动检查项目现状，通过项目中的**实际证据**（代码、Git 历史、TODO、README、构建状态）重建项目状态，并告诉你：

1. 项目目前是什么状态
2. 已确认完成了什么
3. 已确认未完成什么
4. 哪些地方无法确定
5. 当前发现了哪些问题
6. 根据证据，下一步最值得做什么（最多 3 条）
7. 每个判断为什么成立（可展开查看证据原文）

**核心原则：不假装知道。** 证据不足的判断会明确标记为「无法判断」，所有重要判断都给出证据来源。

---

## 技术栈

- **前端**：React 18 + Vite + TypeScript（GitHub/Linear 风格的克制暗色 UI）
- **后端**：Python 3.10+ / FastAPI
- **数据库**：SQLite（标准库实现，无 ORM 依赖）
- **Agent**：OpenAI-compatible API（function calling 驱动的真实 Agent Loop）
- **实时进度**：SSE（Server-Sent Events）

## 目录结构

```
rewind/
├── README.md
├── .env.example          # 环境变量模板
├── backend/
│   ├── main.py           # FastAPI 入口
│   ├── config.py         # 环境变量配置
│   ├── agent/
│   │   ├── loop.py       # Agent Loop 核心（工具调度循环）
│   │   ├── llm.py        # LLM 客户端（真实 / Mock 双引擎）
│   │   ├── prompts.py    # 系统提示词（诊断契约）
│   │   ├── heuristic.py  # 证据驱动的启发式报告（Mock/降级用）
│   │   └── tool_summary.py
│   ├── tools/            # 6 个 Agent Tools
│   │   ├── scan_project_structure.py   # 目录树 + 关键文件
│   │   ├── read_project_file.py        # 读文件（防路径逃逸）
│   │   ├── search_project.py           # TODO/引用/关键词搜索
│   │   ├── analyze_git_history.py      # Git 历史与搁置时长
│   │   ├── detect_project_type.py      # 技术栈识别（附证据）
│   │   └── run_project_check.py        # 安全运行检查（白名单命令）
│   ├── models/           # SQLite 数据层 + 数据契约
│   ├── services/         # 分析编排（SSE 事件总线、落库）
│   ├── api/              # 路由
│   └── tests/            # 分阶段验证测试 + 烂尾样例项目 fixture
└── frontend/
    └── src/
        ├── pages/        # Home / Scan / Report
        ├── components/   # FindingRow / EvidenceList / SuggestionCard / …
        └── styles/       # 设计 token（GitHub dark）
```

## 本地运行

### 1. 后端

```bash
cd backend
pip install -r requirements.txt

# 配置 LLM（三选一）
cp ../.env.example .env   # 然后编辑 .env 填入 LLM_API_KEY 等
# 或导出环境变量：
#   export LLM_BASE_URL=https://api.openai.com/v1
#   export LLM_API_KEY=sk-...
#   export LLM_MODEL=gpt-4o
# 无 Key 时可先用 Mock 引擎体验完整链路：
#   export REWIND_MOCK_LLM=1

uvicorn main:app --port 8000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173（已配置 /api 代理到 8000）
```

### 3. 使用

打开 http://localhost:5173 → 输入一个本地项目文件夹路径（Rewind 在本机运行，后端直接读取该目录）→ 「开始回溯」。

> 由于 Agent 需要执行 Git 检查与构建检查，项目路径必须是后端所在机器上的真实路径。浏览器安全限制导致 Web 页面无法直接读取任意本地文件夹，因此采用路径输入方式。

## LLM 配置（OpenAI-compatible）

任何兼容 OpenAI Chat Completions 协议的服务都可以：

| 服务 | LLM_BASE_URL |
|---|---|
| OpenAI | `https://api.openai.com/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` |
| 本地 Ollama | `http://127.0.0.1:11434/v1` |

所有 Key 只通过环境变量注入，代码零硬编码。**未配置 Key 时**：`REWIND_MOCK_LLM=1` 可启用 Mock 引擎——它会真实执行全部 6 个工具、基于真实证据生成启发式报告（不是假数据），用于本地开发与链路验证。

## Agent 机制

真实的 Agent Loop，不是「输入 → LLM → 输出」：

```
系统提示词（诊断契约）+ 用户简报
        ↓
┌─→ LLM 决策：需要什么信息？
│       ↓
│   调用 Tool（6 个之一）
│       ↓
│   工具真实执行（读文件/查 Git/跑检查）
│       ↓
│   结果回填上下文 → 回到 LLM
│
└─ 证据充分 → 输出结构化诊断报告 JSON
        ↓
   pydantic 严格校验（不合格打回重试，最多 3 次）
        ↓
   落库 SQLite + SSE 推送报告
```

- 工具调用上限 `REWIND_MAX_AGENT_STEPS`（默认 30）防止失控
- 超限时若有证据，降级为启发式报告（诚实标注降级）
- 扫描页展示**真实阶段**（识别类型/分析结构/检查 Git/寻找未完成/运行检查/建立状态）与每一步工具调用日志，无假百分比

### 安全设计

- `read_project_file`：路径 resolve 后必须落在项目根内，越界拒绝
- `run_project_check`：LLM 只能选择检查类型（build/test/lint/typecheck/deps_check），命令由白名单映射生成，强制超时，输出截断
- 第一版**只诊断，不改任何代码**

## 测试

```bash
cd backend
python tests/init_fixture_git.py       # 首次先初始化烂尾样例的 Git 历史（幂等）
python tests/test_phase2_scan.py       # 项目扫描
python tests/test_phase3_tools.py      # 6 工具 + 安全边界
python tests/test_phase4_agent_loop.py # Agent Loop 端到端（Mock 模式）
```

`tests/fixtures/pocket-ledger/` 是一个内置的"烂尾样例项目"（README 目标 + cover 数据层完成但 UI 缺失 + 空实现 + 未引用组件 + 5 个月前的 Git 历史），用于全链路验证。

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 + LLM 配置状态 |
| POST | `/api/projects/validate` | 验证项目路径 |
| GET | `/api/projects` | 最近项目列表 |
| POST | `/api/analysis` | 开始分析 `{path, goal?}` |
| GET | `/api/analysis/{id}/events` | SSE 事件流（支持断线回放） |
| GET | `/api/reports/{id}` | 诊断报告 |
| PATCH | `/api/reports/{id}/goal` | 补充/修正项目目标 |

## 第一版边界（刻意不做）

自动修改代码 / 自动提交 Git / 自动部署 / 多 Agent / MCP / 云同步 / 账号系统 / 社交 / 权限 / 付费。第一版只解决一件事：**把烂尾项目丢给 Rewind，弄清它现在到底做到哪了。**
