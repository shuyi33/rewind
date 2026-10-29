/** 扫描阶段进度（真实阶段，非假百分比）。标签跟随界面语言。 */

import { useI18n } from '../i18n'

export const PHASE_ORDER = [
  { key: 'detect', i18n: 'phase.detect' },
  { key: 'structure', i18n: 'phase.structure' },
  { key: 'git', i18n: 'phase.git' },
  { key: 'evidence', i18n: 'phase.evidence' },
  { key: 'check', i18n: 'phase.check' },
  { key: 'final', i18n: 'phase.report' },
] as const

type PhaseState = 'pending' | 'active' | 'done'

export function PhaseProgress({ current }: { current: string | null }) {
  const { t } = useI18n()
  const idx = PHASE_ORDER.findIndex((p) => p.key === current)
  return (
    <div className="phase-list" role="list" aria-label={t('report.status')}>
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
                <span className="spinner" aria-label="..." />
              ) : (
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--border)' }} />
              )}
            </span>
            <span>{t(p.i18n)}</span>
          </div>
        )
      })}
    </div>
  )
}
