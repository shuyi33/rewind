import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { loadEntries } from '../utils/storage'
import type { LedgerEntry } from '../types/ledger'

export default function Home() {
  const [entries, setEntries] = useState<LedgerEntry[]>([])

  useEffect(() => {
    setEntries(loadEntries())
  }, [])

  return (
    <main className="home">
      <h1>口袋账本</h1>
      <p className="home__hint">随手记一笔</p>
      <Link className="btn btn--primary" to="/create">记一笔</Link>

      <ul className="entry-list">
        {entries.map((e) => (
          <li key={e.id} className="entry-list__item">
            <Link to="/charts">{e.note}</Link>
            <span className="entry-list__amount">{e.amount}</span>
          </li>
        ))}
      </ul>
    </main>
  )
}
