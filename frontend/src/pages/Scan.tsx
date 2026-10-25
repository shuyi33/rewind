import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { subscribeEvents } from '../api/client'
import type { AgentEvent } from '../types'
import { PhaseProgress } from '../components/PhaseProgress'
import { ToolLog, type LogEntry } from '../components/ToolLog'
import { DiagnosisTree, aggregateNodes } from '../components/DiagnosisTree'

/** 扫描页：订阅 SSE，把 Agent 的每一步取证长成一棵「证据之树」。 */
export default function Scan() {
  const { reportId } = useParams()
  const navigate = useNavigate()
  const [phase, setPhase] = useState<string | null>(null)
  const [finished, setFinished] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [entries, setEntries] = useState<LogEntry[]>([])
  const scanPath = typeof window !== 'undefined' ? sessionStorage.getItem('rewind:scan-path') : null

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
            // 完整报告已落库，等 done 事件标记完成
            break
          case 'done':
            setFinished(true)
            break
        }
      },
      (err) => setError(err.message),
    )
    return cleanup
  }, [reportId])

  const nodes = useMemo(() => aggregateNodes(entries), [entries])

  // 节奏放行：即使分析瞬间完成（Mock/SSE 回放），树也按 0.5s/条生长，保证过程可见
  const [visibleCount, setVisibleCount] = useState(0)
  useEffect(() => {
    if (visibleCount >= nodes.length) return
    const t = window.setTimeout(() => setVisibleCount((c) => c + 1), visibleCount === 0 ? 150 : 500)
    return () => window.clearTimeout(t)
  }, [visibleCount, nodes.length])

  const allShown = visibleCount >= nodes.length
  const rootName = scanPath ? scanPath.split(/[\\/]/).filter(Boolean).pop() ?? '项目' : '项目'

  return (
    <main className="scan-page">
      <header className="scan-head">
        <div>
          <h1 className="scan-title">
            <span className="scan-title-dot" aria-hidden="true" />
            {finished && allShown ? '回溯完成' : '正在回溯'}
          </h1>
          {scanPath && <p className="scan-path">{scanPath}</p>}
        </div>
        <PhaseProgress current={finished ? 'finished' : phase} />
      </header>

      {error ? (
        <div className="scan-error" role="alert">
          分析失败：{error}
          <div className="scan-error-back">
            <Link to="/">← 返回重新开始</Link>
          </div>
        </div>
      ) : (
        <DiagnosisTree
          nodes={nodes.slice(0, visibleCount)}
          rootName={rootName}
          rootPath={scanPath ?? ''}
          finished={finished && allShown}
        />
      )}

      {finished && !error && allShown && (
        <div className="scan-next">
          <button className="scan-next-btn" onClick={() => navigate(`/report/${reportId}`, { replace: true })}>
            查看诊断报告 →
          </button>
          <Link to="/" className="scan-next-home">返回首页</Link>
        </div>
      )}
      {(!finished || !allShown) && !error && nodes.length > 0 && (
        <p className="scan-done">证据正在生长…</p>
      )}

      <details className="scan-raw">
        <summary>原始事件日志</summary>
        <ToolLog entries={entries} />
      </details>
    </main>
  )
}
