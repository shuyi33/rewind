import type { Story } from '../types/story'
import { loadStories, saveStories } from '../utils/storage'

export function createStory(title: string, summary: string, cover: string | null = null): Story {
  // TODO: 重名校验
  const story: Story = {
    id: crypto.randomUUID(),
    title,
    summary,
    cover,
    nodes: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  }
  const stories = loadStories()
  stories.push(story)
  saveStories(stories)
  return story
}

export function getStory(id: string): Story | undefined {
  return loadStories().find((s) => s.id === id)
}

export function updateStory(id: string, patch: Partial<Story>): Story | null {
  // TODO: 未实现
  return null
}

export function deleteStory(id: string): boolean {
  // TODO: 未实现
  return false
}
