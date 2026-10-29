import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { rewindApi } from '../api/client'
import type { Finding, FindingStatus, ReportRecord } from '../types'
import { FindingRow } from '../components/FindingRow'
import { SuggestionCard } from '../components/SuggestionCard'
import { useI18n } from '../i18n'

const STATUS_ORDER: FindingStatus[] = [
  'confirmed_incomplete',
  'suspected_incomplete',
  'confirmed_done',
  'unknown',
]

const STATUS_DOTS: Record<string, string> = {
  confirmed_done: 'var(--success)',
  confirmed_incomplete: 'var(--danger)',
  suspected_incomplete: 'var(--warning)',
  unknown: 'var(--neutral)',
}

const STATUS_I18N: Record<string, string> = {
  confirmed_done: 'report.stConfirmedDone',
  confirmed_incomplete: 'report.stConfirmedIncomplete',
  suspected_incomplete: 'report.stSuspected',
  unknown: 'report.stUnknown',
}

function fmtTime(iso: string | null | undefined, lang: string): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(lang === 'zh' ? 'zh-CN' : 'en-US', { hour12: false })
  } catch {
    return iso
  }
}

export default function Report() {
  const { t, lang } = useI18n()
  const { reportId } = useParams()
  const [report, setReport] = useState<ReportRecord | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [goalDraft, setGoalDraft] = useState('')
  const [savingGoal, setSavingGoal] = useState(false)

  useEffect(() => {
    if (!reportId) return
    rewindApi
      .getReport(reportId)
      .then((r) => setReport(r.report))
      .catch((e) => setError(e.message))
  }, [reportId])

  const grouped = useMemo(() => {
    const map = new Map<FindingStatus, Finding[]>()
    for (const s of STATUS_ORDER) map.set(s, [])
    for (const f of report?.findings ?? []) {
      if (map.has(f.status)) map.get(f.status)!.push(f)
    }
    return map
  }, [report])

  if (error) {
    return (
      <main className="page report-dark">
        <div className="banner banner-error">{t('report.loadFail')}{error}</div>
        <Link to="/">{t('report.backHome')}</Link>
      </main>
    )
  }
  if (!report) {
    return (
      <main className="page report-dark">
        <p className="muted">{t('report.loading')}</p>
      </main>
    )
  }

  const pm = report.project_map
  async function saveGoal() {
    if (!reportId || !goalDraft.trim()) return
    setSavingGoal(true)
    try {
      await rewindApi.updateGoal(reportId, goalDraft.trim())
      setReport((r) => (r ? { ...r, goal: goalDraft.trim(), goal_source: 'user' } : r))
      setGoalDraft('')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSavingGoal(false)
    }
  }

  return (
    <main className="page report-dark">
      {/* ---------- 头部 ---------- */}
      <header style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
          <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, margin: 0 }}>
            {pm?.name || '未命名项目'}
          </h1>
          {pm?.project_type ? <span className="label">{pm.project_type}</span> : null}
          <span className="subtle">{t('report.diagnosedAt')} {fmtTime(report.finished_at, lang)}</span>
        </div>

        <div style={{ marginTop: 'var(--space-3)' }}>
          <strong style={{ color: 'var(--fg-muted)', fontWeight: 600 }}>{t('report.goal')}</strong>
          {report.goal ? (
            <p style={{ margin: 'var(--space-1) 0 0' }}>
              {report.goal}
              {report.goal_source ? (
                <span className="subtle" style={{ marginLeft: 'var(--space-2)' }}>
                  （{t('report.goalFrom')}：{report.goal_source === 'readme' ? 'README' : report.goal_source === 'user' ? (lang === 'zh' ? '你' : 'you') : (lang === 'zh' ? '未知' : 'unknown')}）
                </span>
              ) : null}
            </p>
          ) : (
            <div className="goal-form">
              <input
                className="input"
                placeholder={t('report.goalPlaceholder')}
                value={goalDraft}
                maxLength={500}
                onChange={(e) => setGoalDraft(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && saveGoal()}
              />
              <button className="btn btn-primary" disabled={savingGoal || !goalDraft.trim()} onClick={saveGoal}>
                {savingGoal ? t('report.saving') : t('report.saveGoal')}
              </button>
            </div>
          )}
        </div>

        {pm ? (
          <div style={{ marginTop: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {pm.tech_stack?.length ? (
              <div className="dep-row">
                {pm.tech_stack.map((t) => (
                  <span key={t} className="label">{t}</span>
                ))}
              </div>
            ) : null}
            <div style={{ display: 'flex', gap: 'var(--space-6)', flexWrap: 'wrap', color: 'var(--fg-muted)', fontSize: 'var(--text-sm)' }}>
              {pm.modules?.length ? <div><span className="subtle">{t('report.modules')}</span>{pm.modules.join(' · ')}</div> : null}
              {pm.pages?.length ? <div><span className="subtle">{t('report.pages')}</span>{pm.pages.join(' · ')}</div> : null}
              {pm.entry_points?.length ? <div><span className="subtle">{t('report.entry')}</span>{pm.entry_points.join(' · ')}</div> : null}
            </div>
          </div>
        ) : null}
      </header>

      {/* ---------- 摘要 ---------- */}
      {report.summary ? (
        <section style={{ marginBottom: 'var(--space-6)' }}>
          <h2 style={{ fontSize: 'var(--text-md)', fontWeight: 600, marginBottom: 'var(--space-2)' }}>{t('report.summary')}</h2>
          <p style={{ margin: 0, color: 'var(--fg-muted)', lineHeight: 1.8 }}>{report.summary}</p>
        </section>
      ) : null}

      {/* ---------- 四分区状态 ---------- */}
      <section style={{ marginBottom: 'var(--space-6)' }}>
        <h2 style={{ fontSize: 'var(--text-md)', fontWeight: 600, marginBottom: 'var(--space-3)' }}>{t('report.status')}</h2>
        {STATUS_ORDER.map((status) => {
          const items = grouped.get(status) ?? []
          return (
            <div key={status} style={{ marginBottom: 'var(--space-4)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                <span className="status-dot" style={{ background: STATUS_DOTS[status] }} />
                <strong>{t(STATUS_I18N[status])}</strong>
                <span className="subtle">{items.length}</span>
              </div>
              {items.length === 0 ? (
                <p className="subtle" style={{ margin: 0 }}>{t('report.noItems')}</p>
              ) : (
                <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                  {items.map((f) => (
                    <FindingRow key={f.id} finding={f} />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </section>

      {/* ---------- 下一步建议 ---------- */}
      <section style={{ marginBottom: 'var(--space-6)' }}>
        <h2 style={{ fontSize: 'var(--text-md)', fontWeight: 600, marginBottom: 'var(--space-3)' }}>
          {t('report.next')}
        </h2>
        {report.suggestions?.length ? (
          <div className="suggestion-group">
            {report.suggestions.map((s, i) => (
              <SuggestionCard key={i} index={i} suggestion={s} />
            ))}
          </div>
        ) : (
          <p className="muted">{t('report.noSuggestions')}</p>
        )}
      </section>

      {/* ---------- 工具调用轨迹 ---------- */}
      {report.tool_trace?.length ? (
        <section style={{ marginBottom: 'var(--space-6)' }}>
          <details className="trace-fold">
            <summary>{t('report.trace', { n: report.tool_trace.length })}</summary>
            <table className="trace-table">
              <tbody>
                {report.tool_trace.map((t) => (
                  <tr key={t.step}>
                    <td>#{t.step} {t.tool}</td>
                    <td className={t.ok ? 'trace-summary-ok' : 'trace-summary-fail'}>{t.summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </section>
      ) : null}

      {/* ---------- 底部操作 ---------- */}
      <footer style={{ display: 'flex', gap: 'var(--space-3)', borderTop: '1px solid var(--border-muted)', paddingTop: 'var(--space-4)' }}>
        <Link to="/">{t('report.backHome')}</Link>
      </footer>
    </main>
  )
}
