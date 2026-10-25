import type { LedgerEntry } from '../types/ledger'

const KEY = 'pocket-ledger:entries'

export function loadEntries(): LedgerEntry[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '[]')
  } catch {
    return []
  }
}

export function saveEntries(entries: LedgerEntry[]): void {
  localStorage.setItem(KEY, JSON.stringify(entries))
}
