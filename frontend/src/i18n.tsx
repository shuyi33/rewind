import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type Lang = 'zh' | 'en'

type Dict = Record<string, string>

const zh: Dict = {
  // 首页
  'home.heroTitle': '把烂尾的项目，重新看清楚。',
  'home.heroSub': '它替你重新读懂一个很久没碰的项目——代码、Git 历史、TODO、构建状态，一切用证据说话，不假装知道。',
  'home.searchPlaceholder': '输入项目的本地路径，例如 D:\\Projects\\pocket-ledger',
  'home.searchAria': '项目文件夹路径',
  'home.go': '回溯',
  'home.checking': '正在检查…',
  'home.recent': '最近回溯',
  'home.settings': '设置（LLM 配置）',
  'home.errEmptyPath': '请输入项目文件夹的本地路径',
  'home.errValidate': '路径校验失败',
  'home.errStart': '无法开始分析',
  'home.errDemo': '样例项目不可用',
  'home.hintNoLLM': 'LLM 未配置：点左侧齿轮进入设置页配置',
  'home.hintMock': 'Mock 引擎运行中 — 流程完整，判断为演示级别',
  'home.langToggle': 'EN',
  // 扫描页
  'scan.running': '正在回溯',
  'scan.finished': '回溯完成',
  'scan.done': '证据已收齐，正在打开诊断报告…',
  'scan.failed': '分析失败：',
  'scan.backHome': '← 返回重新开始',
  // 工具摘要（后端 summary 为占位时的回退由后端处理；这里是阶段标签）
  'phase.detect': '正在识别项目类型',
  'phase.structure': '正在分析文件结构',
  'phase.git': '正在检查 Git 历史',
  'phase.evidence': '正在寻找未完成内容',
  'phase.check': '正在运行项目检查',
  'phase.report': '正在建立项目状态',
  'phase.done': '分析已完成',
  // 报告页
  'report.diagnosedAt': '诊断于',
  'report.goal': '项目目标',
  'report.goalFrom': '来源',
  'report.goalPlaceholder': '这个项目当初想做什么？（一句话）',
  'report.saveGoal': '保存目标',
  'report.saving': '保存中…',
  'report.modules': '模块：',
  'report.pages': '页面：',
  'report.entry': '入口：',
  'report.summary': '现状摘要',
  'report.status': '项目状态',
  'report.stConfirmedIncomplete': '已确认未完成',
  'report.stSuspected': '疑似未完成',
  'report.stConfirmedDone': '已确认完成',
  'report.stUnknown': '无法判断',
  'report.noItems': '（无条目）',
  'report.next': '现在最值得做什么?',
  'report.whyNow': '为什么建议现在做',
  'report.reasoning': '推理：',
  'report.noSuggestions': '暂无建议（证据不足时 Rewind 不会硬凑）。',
  'report.trace': '查看 Agent 的工具调用轨迹（{n} 步）',
  'report.loadFail': '加载报告失败：',
  'report.evidence': '证据',
  'report.relatedFiles': '相关文件',
  'report.dependsOn': '前置条件',
  'report.impact': '预期影响',
  'report.updateGoal': '补充目标',
  'report.backHome': '← 返回首页',
  'report.loading': '正在加载报告…',
  'report.notFound': '报告不存在',
  // 设置页
  'settings.title': '设置',
  'settings.back': '← 返回首页',
  'settings.badgeMock': 'Mock 引擎',
  'settings.badgeLive': '真实 LLM 已配置',
  'settings.badgeNone': '未配置',
  'settings.mockSub': '流程完整，判断为演示级别',
  'settings.liveSub': '密钥',
  'settings.noneSub': '填入 API Key 后即可智能诊断',
  'settings.provider': '服务商预置',
  'settings.baseUrl': 'API 地址（OpenAI-compatible）',
  'settings.apiKey': 'API Key',
  'settings.keyKeep': '— 留空保持不变',
  'settings.keyPlaceholder': 'sk-… 粘贴后自动测试连接',
  'settings.keyChars': '已输入 {n} 字符',
  'settings.keyFormatOk': '· 格式正确',
  'settings.model': '模型',
  'settings.mockToggle': 'Mock 引擎（无需 Key，本地演示全流程）',
  'settings.test': '测试连接',
  'settings.testing': '测试中…',
  'settings.save': '保存并生效',
  'settings.saving': '保存中…',
  'settings.saved': '已保存并即时生效',
  'settings.note': '配置写入 backend/.env，保存后立即生效（无需重启）。Key 只保存在你本机。',
  'settings.language': '界面语言',
  'settings.loadFail': '无法加载设置',
  'settings.saveFail': '保存失败',
  'settings.testFail': '测试请求失败',
  'settings.keyInvalid': 'Key 无效或未授权（401）',
  'settings.keyDiag': '（后端收到 {n} 字符，前缀{p}）',
  'settings.prefixOk': '正确',
  'settings.prefixBad': '异常',
  'settings.keyComplete': 'Key 已完整送达后端，但被服务商拒绝 —— 请检查：① 账户邮箱是否已验证；② Key 状态是否为 Active（未吊销）；③ 账户是否有可用额度',
  'settings.keyIncomplete': 'Key 未完整到达后端 —— 请点输入框右侧「眼睛」核对明文后再测一次',
  'settings.keyCheckProvider': '—— 请检查 Key 是否属于该服务商',
  'settings.keyPaste': '粘贴时混入了符号，请清空后重新只复制 Key 本身（仅含字母、数字、连字符）',
  'settings.noKey': '没有可用的 API Key',
  'settings.noUrl': '没有 API 地址',
  'settings.noModel': '没有模型名',
  'settings.testOk': '连接成功：{model} 可用（返回 {n} 条候选）',
  'settings.testFailGeneric': '连接失败',
  // 语言切换按钮
  'lang.toggle': 'EN',
  'lang.switchTo': 'Switch to English',
}

const en: Dict = {
  'home.heroTitle': 'See your abandoned projects, clearly.',
  'home.heroSub': "It re-reads a project you haven't touched in months — code, git history, TODOs, build status — every conclusion backed by evidence. It never pretends to know.",
  'home.searchPlaceholder': 'Local project path, e.g. D:\\Projects\\pocket-ledger',
  'home.searchAria': 'Project folder path',
  'home.go': 'Rewind',
  'home.checking': 'Checking…',
  'home.recent': 'Recent',
  'home.settings': 'Settings (LLM)',
  'home.errEmptyPath': 'Enter a local project folder path',
  'home.errValidate': 'Path validation failed',
  'home.errStart': 'Failed to start analysis',
  'home.errDemo': 'Sample project unavailable',
  'home.hintNoLLM': 'LLM not configured — click the gear to open Settings',
  'home.hintMock': 'Mock engine running — full pipeline, demo-level judgments',
  'home.langToggle': '中',
  // Scan
  'scan.running': 'Rewinding',
  'scan.finished': 'Rewind complete',
  'scan.done': 'Evidence collected — opening the diagnosis report…',
  'scan.failed': 'Analysis failed: ',
  'scan.backHome': '← Start over',
  'phase.detect': 'Detecting project type',
  'phase.structure': 'Analyzing file structure',
  'phase.git': 'Checking git history',
  'phase.evidence': 'Hunting for unfinished work',
  'phase.check': 'Running project checks',
  'phase.report': 'Building project state',
  'phase.done': 'Analysis complete',
  // Report
  'report.diagnosedAt': 'Diagnosed',
  'report.goal': 'Project goal',
  'report.goalFrom': 'source',
  'report.goalPlaceholder': 'What was this project trying to be? (one line)',
  'report.saveGoal': 'Save goal',
  'report.saving': 'Saving…',
  'report.modules': 'Modules: ',
  'report.pages': 'Pages: ',
  'report.entry': 'Entry: ',
  'report.summary': 'Summary',
  'report.status': 'Project state',
  'report.stConfirmedIncomplete': 'Confirmed incomplete',
  'report.stSuspected': 'Suspected incomplete',
  'report.stConfirmedDone': 'Confirmed done',
  'report.stUnknown': 'Unknown',
  'report.noItems': '(nothing)',
  'report.next': "What's most worth doing now?",
  'report.whyNow': 'Why now',
  'report.reasoning': 'Reasoning: ',
  'report.noSuggestions': 'No suggestions yet (Rewind will not invent them without evidence).',
  'report.trace': 'View the agent tool trace ({n} steps)',
  'report.loadFail': 'Failed to load report: ',
  'report.evidence': 'Evidence',
  'report.relatedFiles': 'Related files',
  'report.dependsOn': 'Depends on',
  'report.impact': 'Expected impact',
  'report.updateGoal': 'Add goal',
  'report.backHome': '← Home',
  'report.loading': 'Loading report…',
  'report.notFound': 'Report not found',
  // Settings
  'settings.title': 'Settings',
  'settings.back': '← Home',
  'settings.badgeMock': 'Mock engine',
  'settings.badgeLive': 'LLM configured',
  'settings.badgeNone': 'Not configured',
  'settings.mockSub': 'Full pipeline, demo-level judgments',
  'settings.liveSub': 'key',
  'settings.noneSub': 'Paste an API key to enable smart diagnosis',
  'settings.provider': 'Provider presets',
  'settings.baseUrl': 'API base URL (OpenAI-compatible)',
  'settings.apiKey': 'API key',
  'settings.keyKeep': '— leave blank to keep',
  'settings.keyPlaceholder': 'sk-… auto-tests on paste',
  'settings.keyChars': '{n} characters',
  'settings.keyFormatOk': '· format ok',
  'settings.model': 'Model',
  'settings.mockToggle': 'Mock engine (no key needed, full local pipeline)',
  'settings.test': 'Test connection',
  'settings.testing': 'Testing…',
  'settings.save': 'Save & apply',
  'settings.saving': 'Saving…',
  'settings.saved': 'Saved and applied',
  'settings.note': 'Written to backend/.env, effective immediately (no restart). Your key stays on this machine.',
  'settings.language': 'Language',
  'settings.loadFail': 'Failed to load settings',
  'settings.saveFail': 'Save failed',
  'settings.testFail': 'Test request failed',
  'settings.keyInvalid': 'Key invalid or unauthorized (401)',
  'settings.keyDiag': '(received {n} chars, prefix {p})',
  'settings.prefixOk': 'ok',
  'settings.prefixBad': 'bad',
  'settings.keyComplete': 'Key reached the backend intact but was rejected — check: 1) email verified; 2) key still Active (not revoked); 3) account has credit',
  'settings.keyIncomplete': "Key didn't arrive intact — click the eye icon to check the plaintext and retry",
  'settings.keyCheckProvider': ' — check the key belongs to this provider',
  'settings.keyPaste': 'Pasted text contains stray characters. Clear and re-copy the key only (letters, digits, hyphens).',
  'settings.noKey': 'No API key available',
  'settings.noUrl': 'No API base URL',
  'settings.noModel': 'No model name',
  'settings.testOk': 'Connected: {model} works ({n} choices)',
  'settings.testFailGeneric': 'Connection failed',
  'lang.toggle': '中',
  'lang.switchTo': '切换到中文',
}

const DICTS: Record<Lang, Dict> = { zh, en }

type I18nCtx = {
  lang: Lang
  setLang: (l: Lang) => void
  t: (key: string, params?: Record<string, string | number>) => string
}

const Ctx = createContext<I18nCtx | null>(null)

const STORAGE_KEY = 'rewind:lang'

function detect(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'en' || saved === 'zh') return saved
  } catch { /* ignore */ }
  return navigator.language?.toLowerCase().startsWith('zh') ? 'zh' : 'en'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(detect)

  useEffect(() => {
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en'
  }, [lang])

  const setLang = (l: Lang) => {
    setLangState(l)
    try { localStorage.setItem(STORAGE_KEY, l) } catch { /* ignore */ }
  }

  const t = (key: string, params?: Record<string, string | number>) => {
    let s = DICTS[lang][key] ?? DICTS.zh[key] ?? key
    if (params) {
      for (const [k, v] of Object.entries(params)) s = s.replace(`{${k}}`, String(v))
    }
    return s
  }

  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>
}

export function useI18n(): I18nCtx {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}
