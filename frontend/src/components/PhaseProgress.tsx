/** 扫描阶段进度（真实阶段，非假百分比）。 */

export const PHASE_ORDER = [
  { key: 'detect', label: '正在识别项目类型' },
  { key: 'structure', label: '正在分析文件结构' },
  { key: 'git', label: '正在检查 Git 历史' },
  { key: 'evidence', label: '正在寻找未完成内容' },
  { key: 'check', label: '正在运行项目检查' },
  { key: 'final', label: '正在建立项目状态' },
] as const

type PhaseState = 'pending' | 'active' | 'done'

export function PhaseProgress({ current }: { current: string | null }) {
  const idx = PHASE_ORDER.findIndex((p) => p.key === current)
  return (
    <div className="phase-list" role="list" aria-label="分析进度">
      {PHASE_ORDER.map((p, i) => {
        let state: PhaseState = 'pending'
        if (idx >= 0) {
          if (i < idx) state = 'done'
          else if (i === idx) state = 'active'
        } else if (current === 'finished') {
          state = 'done'
        }
        return (
          <div key={p.key} className={`phase-item ${state}`} role="listitem">
            <span className="phase-icon">
              {state === 'done' ? (
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
                  <path d="M3 8.5l3.5 3.5L13 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : state === 'active' ? (
                <span className="spinner" aria-label="进行中" />
              ) : (
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--border)' }} />
              )}
            </span>
            <span>{p.label}</span>
          </div>
        )
      })}
    </div>
  )
}
