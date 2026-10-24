import { useParams } from 'react-router-dom'
import { getStory } from '../services/story'

export default function Editor() {
  const { id } = useParams()
  const story = id ? getStory(id) : undefined

  if (!story) return <main className="editor">故事不存在</main>

  return (
    <main className="editor">
      <h1>{story.title}</h1>
      {/* FIXME: 节点画布未实现，目前只能预览标题 */}
      <section className="editor__canvas">
        {story.nodes.map((node) => (
          <article key={node.id} className="node">
            <p>{node.content}</p>
          </article>
        ))}
      </section>
    </main>
  )
}
