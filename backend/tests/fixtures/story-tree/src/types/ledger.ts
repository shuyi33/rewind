export interface LedgerEntry {
  id: string
  amount: number
  note: string
  /** 当月预算（元），可为空 */
  budget: number | null
  createdAt: number
  updatedAt: number
}
