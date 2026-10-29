import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { rewindApi } from '../api/client'
import { useI18n } from '../i18n'
import type { ProjectInfo, ValidateResult } from '../types'

/**
 * 首页 = Sylva 苔藓世界 + 居中搜索横条（浏览器地址栏形态）。
 * 搜索横条浮在场景上层（pointer-events 只落在自身），回车或按钮发起回溯；
 * 场景内的「开始回溯」大按钮通过 rewind:focus 消息聚焦横条。
 */
export default function Home() {
  const navigate = useNavigate()
  const { t, lang, setLang } = useI18n()
  const [path, setPath] = useState('')
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [hint, setHint] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const frameRef = useRef<HTMLIFrameElement>(null)
  const langRef = useRef(lang)
  langRef.current = lang

  useEffect(() => {
    rewindApi.listProjects().then((r) => setProjects(r.projects)).catch(() => {})
    rewindApi
      .health()
      .then((h) => {
        if (!h.llm_configured) setHint(t('home.hintNoLLM'))
        else if (h.mock) setHint(t('home.hintMock'))
      })
      .catch(() => {})

    // 内置样例的真实统计（TODO 数 / 搁置天数）同步进场景卡片
    rewindApi
      .demoProject()
      .then((d) => {
        if (!d.available) return
        frameRef.current?.contentWindow?.postMessage(
          { type: 'rewind:stats', days: d.last_commit_days, todo: d.todo_count },
          '*',
        )
      })
      .catch(() => {})

    const onMsg = (e: MessageEvent) => {
      const d = e.data as { type?: string; to?: string }
      if (d?.type === 'rewind:ready') {
        // 场景就绪握手：补发语言与统计，消除加载竞态
        frameRef.current?.contentWindow?.postMessage({ type: 'rewind:lang', lang: langRef.current }, '*')
        rewindApi
          .demoProject()
          .then((r) => {
            if (r.available)
              frameRef.current?.contentWindow?.postMessage(
                { type: 'rewind:stats', days: r.last_commit_days, todo: r.todo_count },
                '*',
              )
          })
          .catch(() => {})
        return
      }
      if (d?.type === 'rewind:focus') {
        inputRef.current?.focus()
        inputRef.current?.select()
      } else if (d?.type === 'rewind:demo') {
        // 场景里「诊断样例 · Pocket Ledger」卡片 → 直接回溯内置样例
        rewindApi
          .demoProject()
          .then((r) => { if (r.available) void start(r.path) })
          .catch(() => setError(t('home.errDemo')))
      } else if (d?.type === 'rewind:nav') {
        // 场景顶部 dock 横幅：诊断 / 证据 / 报告
        if (d.to === 'home') {
          navigate('/')
        } else if (d.to === 'scan') {
          const running = projects.find((p) => p.last_report_status === 'running' && p.last_report_id)
          const any = running ?? projects.find((p) => p.last_report_id)
          if (any?.last_report_id) navigate(`/scan/${any.last_report_id}`)
          else inputRef.current?.focus()
        } else if (d.to === 'report') {
          const done = projects.find((p) => p.last_report_status === 'completed' && p.last_report_id)
          if (done?.last_report_id) navigate(`/report/${done.last_report_id}`)
          else inputRef.current?.focus()
        }
      }
    }
    window.addEventListener('message', onMsg)
    return () => window.removeEventListener('message', onMsg)
  }, [projects])

  // 语言切换 → 通知场景换文案
  useEffect(() => {
    frameRef.current?.contentWindow?.postMessage({ type: 'rewind:lang', lang }, '*')
  }, [lang])

  async function start(raw?: string) {
    const target = (raw ?? path).trim()
    setError(null)
    if (!target) {
      setError(t('home.errEmptyPath'))
      inputRef.current?.focus()
      return
    }
    setChecking(true)
    let v: ValidateResult
    try {
      v = await rewindApi.validatePath(target)
    } catch (e) {
      setChecking(false)
      setError(e instanceof Error ? e.message : t('home.errValidate'))
      return
    }
    if (!v.valid) {
      setChecking(false)
      setError(v.error ?? t('home.errValidate'))
      return
    }
    try {
      const { report_id } = await rewindApi.startAnalysis(v.path, undefined, lang)
      sessionStorage.setItem('rewind:scan-path', v.path)
      sessionStorage.setItem('rewind:lang', lang)
      navigate(`/scan/${report_id}`)
    } catch (e) {
      setChecking(false)
      setError(e instanceof Error ? e.message : t('home.errStart'))
    }
  }

  async function openRecent(p: ProjectInfo) {
    setError(null)
    if (p.last_report_id && p.last_report_status === 'completed') {
      navigate(`/report/${p.last_report_id}`)
    } else if (p.last_report_id && p.last_report_status === 'running') {
      navigate(`/scan/${p.last_report_id}`)
    } else {
      setChecking(true)
      try {
        const { report_id } = await rewindApi.startAnalysis(p.path, undefined, lang)
        sessionStorage.setItem('rewind:scan-path', p.path)
        sessionStorage.setItem('rewind:lang', lang)
        navigate(`/scan/${report_id}`)
      } catch (e) {
        setChecking(false)
        setError(e instanceof Error ? e.message : t('home.errStart'))
      }
    }
  }

  return (
    <main className="sylva-home">
      <section className="sylva-hero" aria-label="Rewind">
        <iframe
          ref={frameRef}
          src="/landing-pages/rewind-green-3d.html"
          title="Rewind"
          sandbox="allow-downloads allow-forms allow-modals allow-popups allow-same-origin allow-scripts"
          loading="eager"
          onLoad={() => {
            frameRef.current?.contentWindow?.postMessage({ type: 'rewind:lang', lang }, '*')
            rewindApi
              .demoProject()
              .then((d) => {
                if (!d.available) return
                frameRef.current?.contentWindow?.postMessage(
                  { type: 'rewind:stats', days: d.last_commit_days, todo: d.todo_count },
                  '*',
                )
              })
              .catch(() => {})
          }}
        />
      </section>

      <div className="search-deck" aria-label="Rewind">
        <div className="search-bar">
          <button className="search-gear" onClick={() => navigate('/settings')} aria-label={t('home.settings')} title={t('home.settings')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="3.2" />
              <path d="M19.1 14.6a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.56-1.11 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34h.01a1.7 1.7 0 0 0 1.03-1.56V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1.03 1.56h.01a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.01a1.7 1.7 0 0 0 1.56 1.03H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.56 1.03z" />
            </svg>
          </button>
          <input
            ref={inputRef}
            className="search-input"
            placeholder={t('home.searchPlaceholder')}
            value={path}
            onChange={(e) => setPath(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !checking && start()}
            spellCheck={false}
            autoComplete="off"
            aria-label={t('home.searchAria')}
          />
          <button className="search-go" onClick={() => start()} disabled={checking}>
            {checking ? t('home.checking') : t('home.go')}
          </button>
        </div>

        <button className="lang-toggle" onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')} title={t('lang.switchTo')}>
          {t('lang.toggle')}
        </button>

        {projects.length > 0 && (
          <div className="search-recent" aria-label={t('home.recent')}>
            {projects.filter((p) => !p.path.includes('fixtures')).slice(0, 3).map((p) => (
              <button key={p.id} className="recent-chip" onClick={() => openRecent(p)}>
                <i
                  className="recent-dot"
                  data-status={p.last_report_status ?? 'none'}
                />
                {p.name}
              </button>
            ))}
          </div>
        )}
        {hint && <p className="search-hint">{hint}</p>}
      </div>

      {error && (
        <p className="sylva-toast" role="alert">
          {error}
        </p>
      )}
    </main>
  )
}
