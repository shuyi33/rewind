import { useState } from 'react'
import type { Finding } from '../types'
import { EvidenceList } from './EvidenceList'
import { useI18n } from '../i18n'

const STATUS_DOT: Record<string, string> = {
  confirmed_done: 'var(--success)',
  confirmed_incomplete: 'var(--danger)',
  suspected_incomplete: 'var(--warning)',
  unknown: 'var(--neutral)',
}

/** 单条状态判断：点击展开详情、推理依据与证据。 */
export function FindingRow({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false)
  const { t } = useI18n()
  return (
    <div className={`finding-row${open ? ' open' : ''}`}>
      <button className="finding-head" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span className="status-dot" style={{ background: STATUS_DOT[finding.status] ?? 'var(--neutral)' }} />
        <span className="finding-title">{finding.title}</span>
        {finding.area ? <span className="finding-area">{finding.area}</span> : null}
        <svg className="chevron" width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
          <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open ? (
        <div className="finding-body">
          {finding.detail ? <p className="finding-detail">{finding.detail}</p> : null}
          {finding.evidence.length > 0 ? (
            <>
              <h4 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--text-sm)', color: 'var(--fg)', fontWeight: 600 }}>
                {t('report.evidence')}
              </h4>
              <EvidenceList evidence={finding.evidence} />
            </>
          ) : null}
          {finding.reasoning ? (
            <p className="finding-reason">
              <strong style={{ color: 'var(--fg-muted)' }}>{t('report.reasoning')}</strong>
              {finding.reasoning}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
