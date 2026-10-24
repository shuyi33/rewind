/** Agent 工具调用实时日志（扫描页）。 */

export type LogEntry =
  | { kind: 'call'; step: number; tool: string; args: Record<string, unknown> }
  | { kind: 'result'; step: number; ok: boolean; summary: string; ms: number }
  | { kind: 'note'; message: string }
  | { kind: 'error'; message: string }

export function ToolLog({ entries }: { entries: LogEntry[] }) {
  if (entries.length === 0) {
    return <p className="muted">等待 Agent 的第一个动作…</p>
  }
  return (
    <div className="tool-log" role="log" aria-live="polite">
      {entries.map((e, i) => {
        if (e.kind === 'call') {
          const args = Object.entries(e.args)
            .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
            .join(' ')
          return (
            <div key={i} className="log-line">
              <span className="log-n">{e.step}</span>
              <span className="log-call">
                → {e.tool}
                {args ? <span className="log-args"> ({args.slice(0, 120)})</span> : null}
              </span>
            </div>
          )
        }
        if (e.kind === 'result') {
          return (
            <div key={i} className="log-line">
              <span className="log-n" />
              <span className={`log-result${e.ok ? ' ok' : ' fail'}`}>
                ← {e.summary} <span className="log-ms">·{e.ms}ms</span>
              </span>
            </div>
          )
        }
        if (e.kind === 'note') {
          return (
            <div key={i} className="log-line">
              <span className="log-n" />
              <span className="log-note">· {e.message}</span>
            </div>
          )
        }
        return (
          <div key={i} className="log-line">
            <span className="log-n" />
            <span className="log-error">✗ {e.message}</span>
          </div>
        )
      })}
    </div>
  )
}
