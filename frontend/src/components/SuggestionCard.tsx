import { useState } from 'react'
import type { Suggestion } from '../types'
import { EvidenceList } from './EvidenceList'
import { useI18n } from '../i18n'

/** 恢复建议条目：可展开「为什么 / 证据 / 涉及文件 / 前置依赖 / 影响」。 */
export function SuggestionCard({ index, suggestion }: { index: number; suggestion: Suggestion }) {
  const [open, setOpen] = useState(index === 0)
  const { t } = useI18n()
  return (
    <div className="suggestion-item">
      <button className="suggestion-head" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span className="suggestion-idx">{String(index + 1).padStart(2, '0')}</span>
        <span style={{ flex: 1, fontWeight: 600 }}>{suggestion.title}</span>
        <svg className="chevron" width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
          <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open ? (
        <div className="suggestion-body">
          <h4>{t('report.whyNow')}</h4>
          <p style={{ margin: 0 }}>{suggestion.why_now}</p>

          {suggestion.evidence?.length > 0 ? (
            <>
              <h4>{t('report.evidence')}</h4>
              <EvidenceList evidence={suggestion.evidence} />
            </>
          ) : null}

          {suggestion.related_files?.length > 0 ? (
            <>
              <h4>{t('report.relatedFiles')}</h4>
              <div className="dep-row">
                {suggestion.related_files.map((f) => (
                  <span key={f} className="dep-chip mono-sm">{f}</span>
                ))}
              </div>
            </>
          ) : null}

          <h4>{t('report.dependsOn')}</h4>
          {suggestion.depends_on?.length ? (
            <div className="dep-row">
              {suggestion.depends_on.map((d, i) => (
                <span key={i} className="dep-chip">{d}</span>
              ))}
            </div>
          ) : (
            <p style={{ margin: 0 }}>—</p>
          )}

          {suggestion.impact ? (
            <>
              <h4>{t('report.impact')}</h4>
              <p style={{ margin: 0 }}>{suggestion.impact}</p>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
