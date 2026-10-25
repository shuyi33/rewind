import { useEffect, useRef, useState } from 'react'
import type { LogEntry } from './ToolLog'

/**
 * 诊断树：左侧是项目文件夹节点，Agent 的每一次工具调用从它引出一条线，
 * 在右侧长成一张证据之树。
 *   calling → 流动虚线 + 呼吸卡片（正在取证）
 *   done    → 实线生长定格 + 苔绿状态点
 *   failed  → 橙红
 */

const TOOL_LABELS: Record<string, string> = {
  detect_project_type: '识别技术栈',
  scan_project_structure: '扫描项目结构',
  analyze_git_history: '检查 Git 历史',
  search_project: '搜索未完成证据',
  read_project_file: '读取项目文件',
  run_project_check: '运行项目检查',
}

export type DiagNode = {
  id: number
  step?: number
  tool?: string
  args?: Record<string, unknown>
  status: 'calling' | 'done' | 'failed' | 'note' | 'error'
  summary?: string
  ms?: number
  message?: string
}

/** 把 call/result 事件流聚合成节点（result 回填同 step 的 calling 节点） */
export function aggregateNodes(entries: LogEntry[]): DiagNode[] {
  const nodes: DiagNode[] = []
  for (const e of entries) {
    if (e.kind === 'call') {
      nodes.push({ id: nodes.length, step: e.step, tool: e.tool, args: e.args, status: 'calling' })
    } else if (e.kind === 'result') {
      for (let i = nodes.length - 1; i >= 0; i--) {
        if (nodes[i].step === e.step && nodes[i].status === 'calling') {
          nodes[i] = { ...nodes[i], status: e.ok ? 'done' : 'failed', summary: e.summary, ms: e.ms }
          break
        }
      }
    } else if (e.kind === 'note') {
      nodes.push({ id: nodes.length, status: 'note', message: e.message })
    } else if (e.kind === 'error') {
      nodes.push({ id: nodes.length, status: 'error', message: e.message })
    }
  }
  return nodes
}

const LEFT_W = 224
const NODE_X = 292
const ROW_H = 72
const GAP = 14
const TOP_PAD = 26

export function DiagnosisTree({ nodes, rootName, rootPath, finished }: {
  nodes: DiagNode[]
  rootName: string
  rootPath: string
  finished: boolean
}) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [w, setW] = useState(0)

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver((es) => setW(es[0].contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const height = TOP_PAD * 2 + Math.max(nodes.length, 1) * (ROW_H + GAP)
  const y1 = 96 // 文件夹卡中心

  return (
    <div className="diag-tree" ref={wrapRef} style={{ height }} aria-label="诊断证据树">
      {w > 0 && (
        <svg className="diag-lines" width={w} height={height} aria-hidden="true">
          {nodes.map((n, i) => {
            const y2 = TOP_PAD + i * (ROW_H + GAP) + ROW_H / 2
            const x1 = LEFT_W + 10
            const x2 = NODE_X - 6
            const dx = (x2 - x1) * 0.5
            const d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`
            const st = n.status === 'calling' ? 'calling' : n.status === 'failed' || n.status === 'error' ? 'failed' : 'done'
            return (
              <g key={n.id} className={`diag-line diag-line--${st}`} data-growing={st === 'done' ? '1' : undefined}>
                <path d={d} pathLength={1} />
                {st === 'done' && <circle cx={x2} cy={y2} r={2.6} />}
              </g>
            )
          })}
        </svg>
      )}

      <div className="diag-root" style={{ width: LEFT_W }}>
        <span className="diag-root-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 8V6.5A1.5 1.5 0 0 1 4.5 5h4l2 2.5h7A1.5 1.5 0 0 1 19 9v8a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 3 17z" />
          </svg>
        </span>
        <div className="diag-root-text">
          <strong>{rootName}</strong>
          <span className="diag-root-path">{rootPath}</span>
        </div>
        <span className={`diag-root-pulse${finished ? ' is-done' : ''}`} aria-hidden="true" />
      </div>

      <div className="diag-nodes" style={{ left: NODE_X }}>
        {nodes.map((n) => (
          <div key={n.id} className={`diag-node diag-node--${n.status}`} style={{ height: ROW_H }}>
            {n.tool && (
              <>
                <span className="diag-node-dot" aria-hidden="true" />
                <div className="diag-node-body">
                  <strong>{TOOL_LABELS[n.tool] ?? n.tool}</strong>
                  <span className="diag-node-sub">
                    {n.status === 'calling' ? '正在取证…' : (n.summary ?? '')}
                    {n.ms != null && n.status !== 'calling' ? ` · ${n.ms}ms` : ''}
                  </span>
                </div>
                {n.args && Object.keys(n.args).length > 0 && (
                  <code className="diag-node-args">{JSON.stringify(n.args).slice(0, 60)}</code>
                )}
              </>
            )}
            {!n.tool && n.message && (
              <div className="diag-node-body">
                <span className={`diag-node-sub${n.status === 'error' ? ' is-error' : ''}`}>{n.message}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
