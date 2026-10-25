import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { rewindApi } from '../api/client'
import type { ProjectInfo, ValidateResult } from '../types'

/**
 * 首页 = Sylva 苔藓世界（iframe 场景）。
 * 路径输入、开始回溯、最近项目都长在场景卡片里（postMessage 双向通信）：
 *   ← rewind:submit {path}  场景内点击「开始回溯」
 *   ← rewind:open   {path}  场景内点击最近项目
 *   → rewind:ctx    {projects, hint}  宿主把最近项目 / LLM 状态注入场景
 */
export default function Home() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const projectsRef = useRef<ProjectInfo[]>([])
  const frameRef = useRef<HTMLIFrameElement>(null)
  const sentRef = useRef(false)

  const refresh = () => rewindApi.listProjects().then((r) => {
    setProjects(r.projects)
    projectsRef.current = r.projects
  }).catch(() => {})

  const pushCtx = () => {
    const frame = frameRef.current?.contentWindow
    if (!frame) return
    rewindApi.health().then((h) => {
      frame.postMessage(
        {
          type: 'rewind:ctx',
          projects: projectsRef.current.map((p) => ({
            name: p.name,
            path: p.path,
            status: p.last_report_status ?? 'none',
          })),
          hint: !h.llm_configured
            ? 'LLM 未配置：在 backend/.env 填入 LLM_API_KEY，或设 REWIND_MOCK_LLM=1'
            : h.mock
              ? 'Mock 引擎运行中：流程完整，判断质量为演示级别'
              : null,
        },
        '*',
      )
    }).catch(() => {})
  }

  useEffect(() => {
    refresh()

    const onMsg = async (e: MessageEvent) => {
      const d = e.data as { type?: string; path?: string }
      if (d?.type === 'rewind:ready') {
        sentRef.current = true
        pushCtx()
        return
      }
      if (d?.type === 'rewind:submit' && d.path) {
        setError(null)
        let v: ValidateResult
        try {
          v = await rewindApi.validatePath(d.path)
        } catch (err) {
          setError(err instanceof Error ? err.message : '路径校验失败')
          return
        }
        if (!v.valid) {
          setError(v.error ?? '路径不可用')
          return
        }
        try {
          const { report_id } = await rewindApi.startAnalysis(v.path)
          sessionStorage.setItem('rewind:scan-path', v.path)
          navigate(`/scan/${report_id}`)
        } catch (err) {
          setError(err instanceof Error ? err.message : '无法开始分析')
        }
        return
      }
      if (d?.type === 'rewind:open' && d.path) {
        const p = projectsRef.current.find((x) => x.path === d.path)
        if (!p) return
        if (p.last_report_id && p.last_report_status === 'completed') {
          navigate(`/report/${p.last_report_id}`)
        } else if (p.last_report_id && p.last_report_status === 'running') {
          navigate(`/scan/${p.last_report_id}`)
        } else {
          try {
            const { report_id } = await rewindApi.startAnalysis(p.path)
            sessionStorage.setItem('rewind:scan-path', p.path)
            navigate(`/scan/${report_id}`)
          } catch (err) {
            setError(err instanceof Error ? err.message : '无法开始分析')
          }
        }
      }
    }
    window.addEventListener('message', onMsg)
    return () => window.removeEventListener('message', onMsg)
  }, [])

  useEffect(() => {
    // projects 异步到达时，若场景已就绪则补发一次
    if (projects.length && sentRef.current) pushCtx()
  }, [projects])

  return (
    <main className="sylva-home">
      <section className="sylva-hero" aria-label="Rewind · 回溯">
        <iframe
          ref={frameRef}
          src="/landing-pages/rewind-green-3d.html"
          title="Rewind · 回溯 — 把烂尾的项目重新看清楚"
          sandbox="allow-downloads allow-forms allow-modals allow-popups allow-same-origin allow-scripts"
          loading="eager"
          onLoad={pushCtx}
        />
      </section>
      {error && (
        <p className="sylva-toast" role="alert">
          {error}
        </p>
      )}
    </main>
  )
}
