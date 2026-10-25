import type { LedgerEntry } from '../types/ledger'

export function BudgetBadge({ entry }: { entry: LedgerEntry }) {
  if (entry.budget == null) return <span className="badge badge--empty" />
  return <span className="badge">{`¥${entry.budget}`}</span>
}
