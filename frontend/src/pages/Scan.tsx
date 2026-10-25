import { useEffect, useMemo, useRef, useState } from 'react'
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
              setTimeout(() => navigate(`/report/${reportId}`, { replace: true }), 1400)
            }
            break
        }
      },
      (err) => setError(err.message),
    )
    return cleanup
  }, [reportId, navigate])

  const nodes = useMemo(() => aggregateNodes(entries), [entries])
  const rootName = scanPath ? scanPath.split(/[\\/]/).filter(Boolean).pop() ?? '项目' : '项目'

  return (
    <main className="scan-page">
      <header className="scan-head">
        <div>
          <h1 className="scan-title">
            <span className="scan-title-dot" aria-hidden="true" />
            {finished ? '回溯完成' : '正在回溯'}
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
        <DiagnosisTree nodes={nodes} rootName={rootName} rootPath={scanPath ?? ''} finished={finished} />
      )}

      {finished && !error && <p className="scan-done">证据已收齐，正在打开诊断报告…</p>}

      <details className="scan-raw">
        <summary>原始事件日志</summary>
        <ToolLog entries={entries} />
      </details>
    </main>
  )
}
