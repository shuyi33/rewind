import type { Story } from '../types/story'

const KEY = 'story-tree:stories'

export function loadStories(): Story[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '[]')
  } catch {
    return []
  }
}

export function saveStories(stories: Story[]): void {
  localStorage.setItem(KEY, JSON.stringify(stories))
}
