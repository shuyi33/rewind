import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createEntry } from '../services/ledger'

export default function CreateEntry() {
  const [amount, setAmount] = useState('')
  const [note, setNote] = useState('')
  const navigate = useNavigate()

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const n = Number(amount)
    if (!Number.isFinite(n) || n === 0) return
    const entry = createEntry(n, note.trim())
    navigate(`/charts/${entry.id}`)
  }

  return (
    <form className="create" onSubmit={submit}>
      <label>
        金额
        <input value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="decimal" />
      </label>
      <label>
        备注
        <input value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      {/* TODO: 月度预算设置入口（budget 字段数据层已支持，UI 未做） */}
      <button type="submit">保存</button>
    </form>
  )
}
