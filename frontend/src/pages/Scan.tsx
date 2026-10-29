import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { subscribeEvents } from '../api/client'
import type { AgentEvent } from '../types'
import { PhaseProgress } from '../components/PhaseProgress'
import { ToolLog, type LogEntry } from '../components/ToolLog'
import { useI18n } from '../i18n'

/** 扫描页：订阅 SSE 事件流，展示真实阶段与 Agent 的每一步工具调用（简洁过渡页）。 */
export default function Scan() {
  const { reportId } = useParams()
  const navigate = useNavigate()
  const { t } = useI18n()
  const [phase, setPhase] = useState<string | null>(null)
  const [finished, setFinished] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [entries, setEntries] = useState<LogEntry[]>([])
  const scanPath = typeof window !== 'undefined' ? sessionStorage.getItem('rewind:scan-path') : null

  useEffect(() => {
    if (!reportId) return
    let timer = 0
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
            break
          case 'done':
            setFinished(true)
            if (ev.status === 'completed') {
              timer = window.setTimeout(() => navigate(`/report/${reportId}`, { replace: true }), 1200)
            }
            break
        }
      },
      (err) => setError(err.message),
    )
    return () => {
      window.clearTimeout(timer)
      cleanup()
    }
  }, [reportId, navigate])

  return (
    <main className="scan-page">
      <header className="scan-head">
        <div>
          <h1 className="scan-title">
            {finished ? t('scan.finished') : t('scan.running')}
          </h1>
          {scanPath && <p className="scan-path">{scanPath}</p>}
        </div>
        <PhaseProgress current={finished ? 'finished' : phase} />
      </header>

      {error ? (
        <div className="scan-error" role="alert">
          {t('scan.failed')}{error}
          <div className="scan-error-back">
            <Link to="/">{t('scan.backHome')}</Link>
          </div>
        </div>
      ) : (
        <ToolLog entries={entries} />
      )}

      {finished && !error && <p className="scan-done">{t('scan.done')}</p>}
    </main>
  )
}
