import type { Story } from '../types/story'

export function CoverPreview({ story }: { story: Story }) {
  if (!story.cover) return <div className="cover cover--empty" />
  return <img className="cover" src={story.cover} alt={story.title} />
}
