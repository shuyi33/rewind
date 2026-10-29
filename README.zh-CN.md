# Rewind · 回溯

把一个很久没碰的项目文件夹丢给它，它告诉你这个项目现在到底是什么状态。

你电脑里是不是也有做了一半、几个月没碰的项目？再次打开时已经忘了当初想做什么、做到了哪里、为什么停下来。Rewind 不要求你重新解释整个项目——它自己去查：读代码、翻 Git 历史、搜 TODO、跑构建检查，然后用证据回答四个问题：做到了哪里，停在了哪里，为什么停，下一步最值得做什么。

它有一条硬原则：不假装知道。每个判断都附证据来源（文件、行号、git 提交），证据不足的结论会明确标注「无法判断」。

[English](README.md)

![首页](docs/screenshots/home.png)

## 快速开始

环境只需要 Python 3.10+（前端已构建好，改前端才需要 Node）。

```bash
git clone https://github.com/shuyi33/rewind.git
cd rewind/backend
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```

打开 http://127.0.0.1:8000 就能看到主界面。点搜索条左侧的齿轮进入设置页，选一个服务商（OpenRouter / DeepSeek / 智谱 GLM / OpenAI / 本地 Ollama）填入 API Key，保存即生效。没有 Key 也能玩：打开 Mock 引擎开关，全部流程照跑，工具真实执行，只是报告由启发式生成，方便先体验链路。

Rewind 在你本机运行，分析的是本机路径下的项目，代码不经过任何中间服务器（发给所选 LLM 服务商的内容除外）。Key 只保存在本地 `backend/.env`，不进 git。

## 它是怎么工作的

和「把整个项目塞给大模型」不同，Rewind 是一个真正的工具调度循环：

模型先决定需要什么信息，调用一个工具，工具在你硬盘上真实执行，结果回填给模型，再决定下一步——直到证据充分，输出一份通过 pydantic 严格校验的结构化诊断报告（不合格会被打回重试）。整个过程通过 SSE 实时推给前端，你能看到 Agent 每一步在查什么。

六个工具：

- `scan_project_structure` — 目录树与关键文件
- `detect_project_type` — 技术栈识别（附判定证据）
- `analyze_git_history` — 提交记录与搁置时长
- `search_project` — TODO / FIXME / 引用搜索
- `read_project_file` — 读文件（防路径逃逸）
- `run_project_check` — 构建 / 测试 / 依赖检查（命令白名单）

安全是设计出来的，不是后补的：文件访问 resolve 后必须落在项目根内；模型只能从固定检查类型中选择，具体命令由白名单映射生成，强制超时、输出截断。诊断全程不改动项目的任何文件。

步数用尽还没产出报告时，只要收集过证据，会降级为启发式报告并明确标注来源，而不是失败或编造。数据库是本地 SQLite，历史报告可回看、可补充项目目标。

![Agent 扫描过程](docs/screenshots/scan.png)

![诊断报告](docs/screenshots/report.png)

## 测试

```bash
cd backend
python tests/init_fixture_git.py       # 初始化内置样例的 Git 历史（幂等）
python tests/test_phase2_scan.py       # 项目扫描
python tests/test_phase3_tools.py      # 六个工具 + 安全边界
python tests/test_phase4_agent_loop.py # Agent Loop 端到端
```

`tests/fixtures/pocket-ledger/` 是一个内置的「烂尾样例项目」（一个规划了六个功能、只做完两个、搁置了五个月的记账应用），用于全链路验证。

## 界面

主视觉基于 Meng To 的 [ThreeUI](https://threeui.com)（Sylva 场景，MIT 许可）构建，Living Green 设计语言贯穿首页、扫描与报告页。

## License

MIT
