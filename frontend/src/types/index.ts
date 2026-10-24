/** 与后端 models/schemas.py 一一对应的数据契约 */

export type FindingStatus =
  | 'confirmed_done'
  | 'confirmed_incomplete'
  | 'suspected_incomplete'
  | 'unknown'

export const STATUS_LABELS: Record<FindingStatus, string> = {
  confirmed_done: '已确认完成',
  confirmed_incomplete: '已确认未完成',
  suspected_incomplete: '疑似未完成',
  unknown: '无法判断',
}

export interface Evidence {
  file: string
  lines?: string | null
  snippet?: string | null
  note?: string
}

export interface Finding {
  id: string
  title: string
  status: FindingStatus
  detail?: string | null
  area?: string | null
  evidence: Evidence[]
  reasoning?: string | null
}

export interface Suggestion {
  title: string
  why_now: string
  evidence: Evidence[]
  related_files: string[]
  depends_on: string[]
  impact?: string
}

export interface ProjectMap {
  name?: string | null
  project_type?: string | null
  tech_stack: string[]
  entry_points: string[]
  modules: string[]
  pages: string[]
  notes?: string | null
}

export interface DiagnosisReport {
  goal?: string | null
  goal_source?: 'readme' | 'user' | 'inferred' | 'unknown'
  project_map: ProjectMap
  summary: string
  findings: Finding[]
  suggestions: Suggestion[]
  issues_found: string[]
}

export interface ReportRecord {
  id: string
  project_id: string
  status: 'running' | 'completed' | 'failed'
  goal?: string | null
  goal_source?: 'readme' | 'user' | 'unknown' | null
  summary?: string | null
  project_map?: ProjectMap | null
  findings?: Finding[] | null
  suggestions?: Suggestion[] | null
  tool_trace?: ToolCallTrace[] | null
  error?: string | null
  started_at: string
  finished_at?: string | null
}

export interface ToolCallTrace {
  step: number
  tool: string
  args: Record<string, unknown>
  phase: string
  ok: boolean
  summary: string
}

export interface ProjectInfo {
  id: string
  path: string
  name: string
  goal?: string | null
  created_at: string
  last_analyzed_at?: string | null
  last_report_id?: string | null
  last_report_status?: string | null
}

export interface ValidateResult {
  valid: boolean
  path: string
  name?: string | null
  is_dir: boolean
  has_git: boolean
  error?: string | null
}

/** SSE 事件（Agent 运行过程） */
export type AgentEvent =
  | { type: 'phase'; phase: string; label: string }
  | { type: 'tool_call'; step: number; tool: string; args: Record<string, unknown>; phase: string }
  | { type: 'tool_result'; step: number; tool: string; ok: boolean; summary: string; duration_ms: number }
  | { type: 'note'; message: string }
  | { type: 'report'; report: ReportRecord }
  | { type: 'error'; message: string }
  | { type: 'done'; status: 'completed' | 'failed' }
