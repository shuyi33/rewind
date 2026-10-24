import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { subscribeEvents } from '../api/client'
import type { AgentEvent } from '../types'
import { PhaseProgress } from '../components/PhaseProgress'
import { ToolLog, type LogEntry } from '../components/ToolLog'

/** 扫描页：订阅 SSE 事件流，展示真实阶段与 Agent 的每一步工具调用。 */
export default function Scan() {
  const { reportId } = useParams()
  const navigate = useNavigate()
  const [phase, setPhase] = useState<string | null>(null)
  const [finished, setFinished] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [entries, setEntries] = useState<LogEntry[]>([])
  const scanPath = typeof window !== 'undefined' ? sessionStorage.getItem('rewind:scan-path') : null
  const navigated = useRef(false)

  useEffect(() => {
    if (!reportId || navigated.current) return
    const cleanup = subscribeEvents(
      reportId,
      (ev: AgentEvent) => {
        switch (ev.type) {
          case 'phase':
            setPhase(ev.phase)
            break
          case 'tool_call':
            setEntries((xs) => [...xs, { kind: 'call', step: ev.step, tool: ev.tool, args: ev.args }])
            break
          case 'tool_result':
            setEntries((xs) => [...xs, { kind: 'result', step: ev.step, ok: ev.ok, summary: ev.summary, ms: ev.duration_ms }])
            break
          case 'note':
            setEntries((xs) => [...xs, { kind: 'note', message: ev.message }])
            break
          case 'error':
            setError(ev.message)
            setEntries((xs) => [...xs, { kind: 'error', message: ev.message }])
            break
          case 'report':
            // 完整报告已落库，等 done 事件统一跳转
            break
          case 'done':
            setFinished(true)
            if (ev.status === 'completed' && !navigated.current) {
              navigated.current = true
              setTimeout(() => navigate(`/report/${reportId}`, { replace: true }), 500)
            }
            break
        }
      },
      (err) => setError(err.message),
    )
    return cleanup
  }, [reportId, navigate])

  return (
    <main className="page">
      <div style={{ marginBottom: 'var(--space-5)' }}>
        <h1 style={{ fontSize: 'var(--text-lg)', fontWeight: 600, margin: 0 }}>
          {finished ? '回溯完成' : '正在回溯…'}
        </h1>
        {scanPath ? <p className="mono-sm subtle" style={{ margin: 'var(--space-1) 0 0' }}>{scanPath}</p> : null}
      </div>

      <div className="scan-layout">
        <PhaseProgress current={finished ? 'finished' : phase} />
        <div>
          {error ? (
            <div className="banner banner-error" role="alert">
              分析失败：{error}
              <div style={{ marginTop: 'var(--space-2)' }}>
                <Link to="/">← 返回首页重新开始</Link>
              </div>
            </div>
          ) : (
            <ToolLog entries={entries} />
          )}
          {finished && !error ? (
            <p className="muted" style={{ marginTop: 'var(--space-3)' }}>正在打开诊断报告…</p>
          ) : null}
        </div>
      </div>
    </main>
  )
}
