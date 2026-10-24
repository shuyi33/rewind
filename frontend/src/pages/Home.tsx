import { useEffect, useState } from 'react'
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
    <main className="page">
      <section style={{ textAlign: 'center', paddingTop: 'var(--space-7)', paddingBottom: 'var(--space-7)' }}>
        <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, margin: 0, letterSpacing: '-0.5px' }}>
          重新捡起一个项目。
        </h1>
        <p className="muted" style={{ fontSize: 'var(--text-md)', marginTop: 'var(--space-3)' }}>
          让 Rewind 先替你弄清楚，它现在到底做到哪了。
        </p>

        <div style={{ maxWidth: 560, margin: 'var(--space-6) auto 0', textAlign: 'left' }}>
          <label htmlFor="project-path" className="subtle" style={{ display: 'block', marginBottom: 'var(--space-2)' }}>
            项目文件夹路径（Rewind 在本机运行，可直接读取该目录）
          </label>
          <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
            <input
              id="project-path"
              className="input"
              placeholder="例如 /Users/me/projects/story-tree"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && start()}
              spellCheck={false}
            />
            <button className="btn btn-primary btn-lg" onClick={start} disabled={checking}>
              {checking ? '正在检查…' : '开始回溯'}
            </button>
          </div>
          {error && (
            <p style={{ color: 'var(--danger)', fontSize: 'var(--text-sm)', margin: 'var(--space-3) 0 0' }}>{error}</p>
          )}
          {llmReady === false && (
            <div className="panel" style={{ marginTop: 'var(--space-4)', padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--fg-muted)' }}>
              尚未配置 LLM：请在 <code>backend/.env</code> 中设置 <code>LLM_API_KEY</code>
              （详见 <code>.env.example</code>）。未配置时无法执行智能诊断。
            </div>
          )}
          {mock && (
            <div className="panel" style={{ marginTop: 'var(--space-4)', padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--fg-muted)' }}>
              当前运行在 <b>Mock LLM 模式</b>（REWIND_MOCK_LLM=1）：Agent 流程完整可用，但判断质量为演示级别。
            </div>
          )}
        </div>
      </section>

      <section style={{ marginTop: 'var(--space-6)' }}>
        <h2 style={{ fontSize: 'var(--text-md)', fontWeight: 600, margin: '0 0 var(--space-3)' }}>最近的项目</h2>
        {projects.length === 0 ? (
          <p className="subtle" style={{ margin: 0 }}>还没有分析过任何项目。</p>
        ) : (
          <div className="panel">
            {projects.map((p) => (
              <button key={p.id} className="list-row" style={{ width: '100%', background: 'transparent', border: 'none', borderBottom: '1px solid var(--border-muted)', cursor: 'pointer', textAlign: 'left', font: 'inherit', color: 'inherit' }} onClick={() => openRecent(p)}>
                <span className="status-dot" style={{ background: p.last_report_status === 'completed' ? 'var(--success)' : p.last_report_status === 'failed' ? 'var(--danger)' : p.last_report_status === 'running' ? 'var(--warning)' : 'var(--neutral)' }} />
                <span style={{ fontWeight: 600 }}>{p.name}</span>
                <span className="mono-sm subtle" style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.path}</span>
                <span className="subtle" style={{ flexShrink: 0 }}>{p.last_analyzed_at ?? '未分析'}</span>
              </button>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}
