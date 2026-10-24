import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { loadStories } from '../utils/storage'
import type { Story } from '../types/story'

export default function Home() {
  const [stories, setStories] = useState<Story[]>([])

  useEffect(() => {
    setStories(loadStories())
  }, [])

  return (
    <main className="home">
      <h1>剧情树</h1>
      <p className="home__hint">制作分支剧情故事</p>
      <Link className="btn btn--primary" to="/create">新建故事</Link>

      <ul className="story-list">
        {stories.map((s) => (
          <li key={s.id} className="story-list__item">
            <Link to={`/editor/${s.id}`}>{s.title}</Link>
            <span className="story-list__summary">{s.summary}</span>
          </li>
        ))}
      </ul>
    </main>
  )
}
