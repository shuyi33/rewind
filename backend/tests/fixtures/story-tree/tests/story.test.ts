import { describe, it, expect } from 'vitest'
import { createStory, getStory } from '../src/services/story'

// 数据层依赖 localStorage，Node 环境尚未 mock。
// TODO: 补充 localStorage polyfill 后启用以下用例

describe('story service', () => {
  it.skip('创建故事后可按 id 读取', () => {
    const s = createStory('测试故事', '简介')
    expect(getStory(s.id)?.title).toBe('测试故事')
  })
})
