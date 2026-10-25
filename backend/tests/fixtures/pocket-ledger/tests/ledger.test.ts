import { describe, it, expect } from 'vitest'
import { createEntry, getEntry } from '../src/services/ledger'

// 数据层依赖 localStorage，Node 环境尚未 mock。
// TODO: 补充 localStorage polyfill 后启用以下用例

describe('ledger service', () => {
  it.skip('记账后可按 id 读取', () => {
    const e = createEntry(25, '午餐')
    expect(getEntry(e.id)?.amount).toBe(25)
  })
})
