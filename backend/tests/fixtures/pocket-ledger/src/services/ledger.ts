import type { LedgerEntry } from '../types/ledger'
import { loadEntries, saveEntries } from '../utils/storage'

export function createEntry(amount: number, note: string, budget: number | null = null): LedgerEntry {
  // TODO: 同日重复记账提醒
  const entry: LedgerEntry = {
    id: crypto.randomUUID(),
    amount,
    note,
    budget,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  }
  const entries = loadEntries()
  entries.push(entry)
  saveEntries(entries)
  return entry
}

export function getEntry(id: string): LedgerEntry | undefined {
  return loadEntries().find((e) => e.id === id)
}

export function updateEntry(id: string, patch: Partial<LedgerEntry>): LedgerEntry | null {
  // TODO: 未实现
  return null
}

export function deleteEntry(id: string): boolean {
  // TODO: 未实现
  return false
}
