import type { Evidence } from '../types'

/**
 * 证据列表 — Rewind 的产品特色。
 * 每条证据：文件路径 + 行号 + 该证据说明了什么 + 关键代码片段。
 * 用户可以据此核验 Agent 的每个判断。
 */
export function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (!evidence || evidence.length === 0) {
    return <p className="evidence-empty">该判断暂无直接证据（Agent 未提供）。</p>
  }
  return (
    <div className="evidence-list">
      {evidence.map((ev, i) => (
        <div key={i} className="evidence-item">
          <div className="evidence-file">
            <span>{ev.file}</span>
            {ev.lines ? <span className="evidence-lines">:{ev.lines}</span> : null}
            {ev.note ? <span className="evidence-note">{ev.note}</span> : null}
          </div>
          {ev.snippet ? <pre className="evidence-snippet">{ev.snippet}</pre> : null}
        </div>
      ))}
    </div>
  )
}
