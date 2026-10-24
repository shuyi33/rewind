export interface Story {
  id: string
  title: string
  summary: string
  /** 封面图（dataURL 或路径），可为空 */
  cover: string | null
  nodes: StoryNode[]
  createdAt: number
  updatedAt: number
}

export interface StoryNode {
  id: string
  content: string
  choices: { text: string; nextId: string | null }[]
}
