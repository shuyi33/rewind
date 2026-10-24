import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createStory } from '../services/story'

export default function CreateStory() {
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const navigate = useNavigate()

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    const story = createStory(title.trim(), summary.trim())
    navigate(`/editor/${story.id}`)
  }

  return (
    <form className="create" onSubmit={submit}>
      <label>
        标题
        <input value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <label>
        简介
        <textarea value={summary} onChange={(e) => setSummary(e.target.value)} />
      </label>
      {/* TODO: 封面选择入口（cover 字段数据层已支持，UI 未做） */}
      <button type="submit">创建</button>
    </form>
  )
}
