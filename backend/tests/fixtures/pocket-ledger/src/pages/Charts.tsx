import { useParams } from 'react-router-dom'
import { getEntry } from '../services/ledger'

export default function Charts() {
  const { id } = useParams()
  const entry = id ? getEntry(id) : undefined

  if (!entry) return <main className="charts">账目不存在</main>

  return (
    <main className="charts">
      <h1>{entry.note}</h1>
      {/* FIXME: 分类统计图表未实现，目前只能看金额 */}
      <section className="charts__panel">
        <p>{`¥${entry.amount}`}</p>
      </section>
    </main>
  )
}
