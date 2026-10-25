import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { rewindApi } from '../api/client'
import type { ProjectInfo, ValidateResult } from '../types'

/**
 * 首页 = Sylva 苔藓世界 + 居中搜索横条（浏览器地址栏形态）。
 * 搜索横条浮在场景上层（pointer-events 只落在自身），回车或按钮发起回溯；
 * 场景内的「开始回溯」大按钮通过 rewind:focus 消息聚焦横条。
 */
export default function Home() {
  const navigate = useNavigate()
  const [path, setPath] = useState('')
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [hint, setHint] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    rewindApi.listProjects().then((r) => setProjects(r.projects)).catch(() => {})
    rewindApi
      .health()
      .then((h) => {
        if (!h.llm_configured) setHint('LLM 未配置：在 backend/.env 填入 LLM_API_KEY，或设 REWIND_MOCK_LLM=1')
        else if (h.mock) setHint('Mock 引擎运行中 — 流程完整，判断为演示级别')
      })
      .catch(() => {})

    const onMsg = (e: MessageEvent) => {
      const t = (e.data as { type?: string })?.type
      if (t === 'rewind:focus') {
        inputRef.current?.focus()
        inputRef.current?.select()
      } else if (t === 'rewind:demo') {
        // 场景里「诊断样例 · Story Tree」卡片 → 直接回溯内置样例
        rewindApi
          .demoProject()
          .then((d) => { if (d.available) void start(d.path) })
          .catch(() => setError('样例项目不可用'))
      }
    }
    window.addEventListener('message', onMsg)
    return () => window.removeEventListener('message', onMsg)
  }, [])

  async function start(raw?: string) {
    const target = (raw ?? path).trim()
    setError(null)
    if (!target) {
      setError('请输入项目文件夹的本地路径')
      inputRef.current?.focus()
      return
    }
    setChecking(true)
    let v: ValidateResult
    try {
      v = await rewindApi.validatePath(target)
    } catch (e) {
      setChecking(false)
      setError(e instanceof Error ? e.message : '路径校验失败')
      return
    }
    if (!v.valid) {
      setChecking(false)
      setError(v.error ?? '路径不可用')
      return
    }
    try {
      const { report_id } = await rewindApi.startAnalysis(v.path)
      sessionStorage.setItem('rewind:scan-path', v.path)
      navigate(`/scan/${report_id}`)
    } catch (e) {
      setChecking(false)
      setError(e instanceof Error ? e.message : '无法开始分析')
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
        const { report_id } = await rewindApi.startAnalysis(p.path)
        sessionStorage.setItem('rewind:scan-path', p.path)
        navigate(`/scan/${report_id}`)
      } catch (e) {
        setChecking(false)
        setError(e instanceof Error ? e.message : '无法开始分析')
      }
    }
  }

  return (
    <main className="sylva-home">
      <section className="sylva-hero" aria-label="Rewind · 回溯">
        <iframe
          src="/landing-pages/rewind-green-3d.html"
          title="Rewind · 回溯 — 把烂尾的项目重新看清楚"
          sandbox="allow-downloads allow-forms allow-modals allow-popups allow-same-origin allow-scripts"
          loading="eager"
        />
      </section>

      <div className="search-deck" aria-label="回溯入口">
        <div className="search-bar">
          <span className="search-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h6A2.5 2.5 0 0 1 15 6.5v6A2.5 2.5 0 0 1 12.5 15h-6A2.5 2.5 0 0 1 4 12.5z" />
              <path d="M15 9l4.6-2.7v10.4L15 14" />
            </svg>
          </span>
          <input
            ref={inputRef}
            className="search-input"
            placeholder="输入项目的本地路径，例如 D:\Projects\story-tree"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !checking && start()}
            spellCheck={false}
            autoComplete="off"
            aria-label="项目文件夹路径"
          />
          <button className="search-go" onClick={() => start()} disabled={checking}>
            {checking ? '正在检查…' : '回溯'}
          </button>
        </div>

        {projects.length > 0 && (
          <div className="search-recent" aria-label="最近回溯">
            {projects.slice(0, 3).map((p) => (
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
