/** 后端 API 客户端（同源，经 Vite 代理转发到 FastAPI） */

import type { AgentEvent, ProjectInfo, ReportRecord, ValidateResult } from '../types'

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* ignore */ }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const rewindApi = {
  health: () => api<{ ok: boolean; llm_configured: boolean; mock: boolean }>('/api/health'),

  validatePath: (path: string) =>
    api<ValidateResult>('/api/projects/validate', {
      method: 'POST',
      body: JSON.stringify({ path }),
    }),

  listProjects: () => api<{ projects: ProjectInfo[] }>('/api/projects'),

  demoProject: () =>
    api<{ path: string; available: boolean; todo_count: number | null; last_commit_days: number | null }>(
      '/api/projects/demo',
    ),

  testLLM: (body: { base_url?: string; api_key?: string; model?: string }) =>
    api<{ ok: boolean; detail: string }>('/api/settings/test', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getSettings: () =>
    api<{ base_url: string; model: string; mock: boolean; has_key: boolean; api_key_masked: string }>(
      '/api/settings',
    ),

  saveSettings: (body: { base_url?: string; model?: string; api_key?: string; mock?: boolean }) =>
    api<{ base_url: string; model: string; mock: boolean; has_key: boolean; api_key_masked: string }>(
      '/api/settings',
      { method: 'POST', body: JSON.stringify(body) },
    ),

  startAnalysis: (path: string, goal?: string, lang?: string) =>
    api<{ report_id: string; project_id: string }>('/api/analysis', {
      method: 'POST',
      body: JSON.stringify({ path, goal, lang }),
    }),

  getReport: (reportId: string) => api<{ report: ReportRecord }>(`/api/reports/${reportId}`),

  updateGoal: (reportId: string, goal: string) =>
    api<{ ok: boolean; goal: string; goal_source: string }>(`/api/reports/${reportId}/goal`, {
      method: 'PATCH',
      body: JSON.stringify({ goal }),
    }),
}

/** 订阅一次分析的事件流（SSE）。返回清理函数。 */
export function subscribeEvents(
  reportId: string,
  onEvent: (ev: AgentEvent) => void,
  onError?: (err: Error) => void,
): () => void {
  const es = new EventSource(`/api/analysis/${reportId}/events`)
  es.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data) as AgentEvent)
    } catch (e) {
      console.error('bad sse payload', e)
    }
  }
  es.onerror = () => {
    // EventSource 会自动重连；仅在连接已关闭且无法恢复时通知
    if (es.readyState === EventSource.CLOSED) {
      onError?.(new Error('事件流连接已断开'))
    }
  }
  return () => es.close()
}
