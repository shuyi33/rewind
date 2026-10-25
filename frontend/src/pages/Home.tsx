import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { rewindApi } from '../api/client'
import type { ProjectInfo, ValidateResult } from '../types'

export default function Home() {
  const navigate = useNavigate()
  const [path, setPath] = useState('')
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [llmReady, setLlmReady] = useState<boolean | null>(null)
  const [mock, setMock] = useState(false)
  const toolRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const refresh = () => rewindApi.listProjects().then((r) => setProjects(r.projects)).catch(() => {})

  useEffect(() => {
    rewindApi
      .health()
      .then((h) => {
        setLlmReady(h.llm_configured)
        setMock(h.mock)
      })
      .catch(() => setLlmReady(false))
    refresh()
  }, [])

  // hero（iframe 内 Sylva 世界）的「开始回溯 / 回溯」按钮 → 平滑滚动到工具区
  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      if ((e.data as { type?: string })?.type === 'rewind:enter') {
        toolRef.current?.scrollIntoView({ behavior: 'smooth' })
        window.setTimeout(() => inputRef.current?.focus(), 650)
      }
    }
    window.addEventListener('message', onMsg)
    return () => window.removeEventListener('message', onMsg)
  }, [])

  async function start() {
    setError(null)
    if (!path.trim()) {
      setError('请输入项目文件夹的本地路径')
      return
    }
    setChecking(true)
    let v: ValidateResult
    try {
      v = await rewindApi.validatePath(path)
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
    if (p.last_report_id && p.last_report_status === 'completed') {
      navigate(`/report/${p.last_report_id}`)
    } else if (p.last_report_id && p.last_report_status === 'running') {
      navigate(`/scan/${p.last_report_id}`)
    } else {
      // 无可用报告或已失败 → 重新分析
      try {
        const { report_id } = await rewindApi.startAnalysis(p.path)
        sessionStorage.setItem('rewind:scan-path', p.path)
        navigate(`/scan/${report_id}`)
      } catch (e) {
        setError(e instanceof Error ? e.message : '无法开始分析')
      }
    }
  }

  return (
    <main className="sylva-home">
      <section className="sylva-hero" aria-label="Rewind · 回溯 主视觉">
        <iframe
          src="/landing-pages/rewind-green-3d.html"
          title="Rewind · 回溯 — 把烂尾的项目重新看清楚"
          sandbox="allow-downloads allow-forms allow-modals allow-popups allow-same-origin allow-scripts"
          loading="eager"
        />
      </section>

      <div className="tool-sec" ref={toolRef}>
        <section className="tool-panel">
          <p className="tool-kicker">EVIDENCE-BASED RECOVERY</p>
          <h2 className="tool-h">回溯一个项目</h2>
          <p className="tool-sub">
            输入本机项目文件夹路径，Rewind 会用真实证据——代码、Git 历史、TODO、构建状态——重建它的现状。
          </p>

          <label htmlFor="project-path" className="tool-label">
            项目文件夹路径（Rewind 在本机运行，可直接读取该目录）
          </label>
          <div className="tool-launch">
            <input
              ref={inputRef}
              id="project-path"
              className="tool-input"
              placeholder="例如 D:\Projects\story-tree"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && start()}
              spellCheck={false}
            />
            <button className="tool-btn" onClick={start} disabled={checking}>
              {checking ? '正在检查…' : '开始回溯'}
            </button>
          </div>
          {error && (
            <p className="tool-error" role="alert">
              {error}
            </p>
          )}
          {llmReady === false && (
            <div className="tool-note">
              尚未配置 LLM：请在 <code>backend/.env</code> 中设置 <code>LLM_API_KEY</code>
              （详见 <code>.env.example</code>）。未配置时无法执行智能诊断。
            </div>
          )}
          {mock && (
            <div className="tool-note">
              当前运行在 <b>Mock LLM 模式</b>（REWIND_MOCK_LLM=1）：Agent 流程完整可用，但判断质量为演示级别。
            </div>
          )}
        </section>

        <section className="tool-panel">
          <h2 className="tool-h tool-h--sm">最近的项目</h2>
          {projects.length === 0 ? (
            <p className="tool-empty">还没有分析过任何项目。</p>
          ) : (
            <div className="tool-list">
              {projects.map((p) => (
                <button key={p.id} className="tool-row" onClick={() => openRecent(p)}>
                  <span
                    className="tool-dot"
                    data-status={
                      p.last_report_status === 'completed'
                        ? 'done'
                        : p.last_report_status === 'failed'
                          ? 'failed'
                          : p.last_report_status === 'running'
                            ? 'running'
                            : 'none'
                    }
                  />
                  <span className="tool-name">{p.name}</span>
                  <span className="tool-path">{p.path}</span>
                  <span className="tool-time">{p.last_analyzed_at ?? '未分析'}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <footer className="tool-foot">
          Rewind · 回溯 — Project Recovery Agent · 苔藓世界场景由{' '}
          <a href="https://threeui.com" target="_blank" rel="noreferrer">
            ThreeUI
          </a>
          （Sylva，MIT）驱动
        </footer>
      </div>
    </main>
  )
}
