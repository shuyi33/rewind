import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { rewindApi } from '../api/client'

type SettingsState = {
  base_url: string
  model: string
  mock: boolean
  has_key: boolean
  api_key_masked: string
}

const PRESETS = [
  { name: 'OpenRouter', url: 'https://openrouter.ai/api/v1', model: 'deepseek/deepseek-chat' },
  { name: 'DeepSeek', url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  { name: '智谱 GLM', url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4.5' },
  { name: 'OpenAI', url: 'https://api.openai.com/v1', model: 'gpt-4o' },
  { name: 'Ollama 本地', url: 'http://127.0.0.1:11434/v1', model: 'qwen2.5:14b' },
]

/** 设置页：LLM 配置（写入 backend/.env，保存后热加载，无需重启服务）。 */
export default function Settings() {
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [mock, setMock] = useState(false)
  const [state, setState] = useState<SettingsState | null>(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; detail: string } | null>(null)
  const [showKey, setShowKey] = useState(false)

  useEffect(() => {
    rewindApi
      .getSettings()
      .then((s) => {
        setState(s)
        setBaseUrl(s.base_url)
        setModel(s.model)
        setMock(s.mock)
      })
      .catch(() => setErr('无法加载设置'))
  }, [])

  async function testConnection() {
    setTesting(true)
    setTestResult(null)
    try {
      const r = await rewindApi.testLLM({ base_url: baseUrl, api_key: apiKey || undefined, model })
      setTestResult(r)
    } catch (e) {
      setTestResult({ ok: false, detail: e instanceof Error ? e.message : '测试请求失败' })
    } finally {
      setTesting(false)
    }
  }

  async function save() {
    setSaving(true)
    setMsg(null)
    setErr(null)
    try {
      const s = await rewindApi.saveSettings({
        base_url: baseUrl,
        model,
        api_key: apiKey || undefined,
        mock,
      })
      setState(s)
      setMock(s.mock)
      setApiKey('')
      setMsg('已保存并即时生效')
    } catch (e) {
      setErr(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="settings-page">
      <header className="settings-head">
        <h1>设置</h1>
        <Link to="/" className="settings-back">← 返回首页</Link>
      </header>

      <section className="settings-card">
        <div className="settings-status">
          <span className={`settings-badge${state ? (state.mock ? ' is-mock' : state.has_key ? ' is-live' : ' is-none') : ''}`}>
            {state ? (state.mock ? 'Mock 引擎' : state.has_key ? '真实 LLM 已配置' : '未配置') : '…'}
          </span>
          <span className="settings-sub">
            {state?.mock
              ? '流程完整，判断为演示级别'
              : state?.has_key
                ? `密钥 ${state.api_key_masked} · ${state.model}`
                : '填入 API Key 后即可智能诊断'}
          </span>
        </div>

        <label className="settings-field">
          <span className="settings-label">服务预置</span>
          <div className="settings-presets">
            {PRESETS.map((p) => (
              <button
                key={p.name}
                type="button"
                className={`settings-preset${baseUrl === p.url ? ' is-active' : ''}`}
                onClick={() => { setBaseUrl(p.url); setModel(p.model) }}
              >
                {p.name}
              </button>
            ))}
          </div>
        </label>

        <label className="settings-field">
          <span className="settings-label">API 地址（OpenAI-compatible）</span>
          <input className="settings-input" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} spellCheck={false} />
        </label>

        <label className="settings-field">
          <span className="settings-label">
            API Key
            {apiKey.length > 0 && <span className="settings-keylen">已输入 {apiKey.length} 字符{apiKey.startsWith('sk-or-v1-') ? ' · 格式正确' : ''}</span>}
          </span>
          <div className="settings-key-row">
            <input
              className="settings-input"
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              onBlur={() => { if (apiKey.trim().length > 10) void testConnection() }}
              placeholder={state?.has_key ? `${state.api_key_masked} — 留空保持不变` : 'sk-… 粘贴后自动测试连接'}
              spellCheck={false}
              autoComplete="off"
            />
            <button
              type="button"
              className="settings-eye"
              onClick={() => setShowKey((v) => !v)}
              aria-label={showKey ? '隐藏 Key' : '显示 Key'}
              title={showKey ? '隐藏' : '显示明文'}
            >
              {showKey ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c7 0 10 8 10 8a13.2 13.2 0 0 1-1.67 2.68" />
                  <path d="M6.61 6.61A13.5 13.5 0 0 0 2 12s3 8 10 8a9.7 9.7 0 0 0 5.39-1.61" />
                  <path d="M2 2l20 20" />
                  <path d="M14.12 14.12A3 3 0 1 1 9.88 9.88" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M2 12s3-8 10-8 10 8 10 8-3 8-10 8-10-8-10-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              )}
            </button>
          </div>
        </label>

        <label className="settings-field">
          <span className="settings-label">模型</span>
          <input className="settings-input" value={model} onChange={(e) => setModel(e.target.value)} spellCheck={false} />
        </label>

        <label className="settings-switch-row">
          <input
            type="checkbox"
            className="settings-switch"
            checked={mock}
            onChange={(e) => setMock(e.target.checked)}
          />
          <span>Mock 引擎（无需 Key，本地演示全流程）</span>
        </label>

        <div className="settings-actions">
          <button className="settings-test" onClick={testConnection} disabled={testing}>
            {testing ? '测试中…' : '测试连接'}
          </button>
          <button className="settings-save" onClick={save} disabled={saving}>
            {saving ? '保存中…' : '保存并生效'}
          </button>
        </div>
        {testResult && (
          <p className={testResult.ok ? 'settings-msg' : 'settings-err'} role="status">
            {testResult.ok ? '✓ ' : '✕ '}{testResult.detail}
          </p>
        )}
        {msg && <p className="settings-msg">{msg}</p>}
        {err && <p className="settings-err" role="alert">{err}</p>}

        <p className="settings-note">
          配置写入 <code>backend/.env</code>，保存后立即生效（无需重启）。Key 只保存在你本机。
        </p>
      </section>
    </main>
  )
}
