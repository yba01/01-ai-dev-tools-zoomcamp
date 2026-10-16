import type { Expense, Group, Settlement } from './types'

// All HTTP traffic lives here so the backend URL and wire format stay out of UI components.
// In development, use Vite's same-origin /api proxy so browsers opened through
// a forwarded workspace URL do not need direct access to the backend port.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

type WirePerson = { id: string; name: string }
type WireExpense = { id: string; description: string; amount: string | number; payer_id: string; date: string; participant_ids: string[] }
type WireSettlement = { id: string; payer_id: string; receiver_id: string; amount: string | number; date: string }
type WireGroup = { id: string; name: string; description: string; currency: string; created_at: string; participants: WirePerson[]; expenses: WireExpense[]; settlements: WireSettlement[] }
type WireBalances = { total_expenses: string | number; outstanding_amount: string | number; balances: { participant_id: string; name: string; total_paid: string | number; net_balance: string | number }[] }
type WireSuggestions = { transfers: { payer_id: string; receiver_id: string; amount: string | number }[] }

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers },
    })
  } catch {
    throw new Error(`Can’t reach the backend at ${API_BASE_URL}. Make sure it is running.`)
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json() as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map(item => typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item)).join(', ')
    } catch { /* Keep the HTTP status message when the body is not JSON. */ }
    throw new Error(detail)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

const fromGroup = (group: WireGroup): Group => ({
  id: group.id,
  name: group.name,
  description: group.description,
  currency: group.currency,
  createdAt: group.created_at.slice(0, 10),
  participants: group.participants,
  expenses: group.expenses.map(expense => ({
    id: expense.id,
    description: expense.description,
    amount: Number(expense.amount),
    payerId: expense.payer_id,
    date: expense.date,
    participantIds: expense.participant_ids,
  })),
  settlements: group.settlements.map(settlement => ({
    id: settlement.id,
    payerId: settlement.payer_id,
    receiverId: settlement.receiver_id,
    amount: Number(settlement.amount),
    date: settlement.date,
  })),
})

export const api = {
  async listGroups() {
    const groups = await request<WireGroup[]>('/groups')
    return groups.map(fromGroup)
  },
  async createGroup(input: Pick<Group, 'name' | 'description' | 'currency'>) {
    return fromGroup(await request<WireGroup>('/groups', { method: 'POST', body: JSON.stringify(input) }))
  },
  async updateGroup(groupId: string, input: Pick<Group, 'name' | 'description' | 'currency'>) {
    return fromGroup(await request<WireGroup>(`/groups/${groupId}`, { method: 'PATCH', body: JSON.stringify(input) }))
  },
  async deleteGroup(groupId: string) {
    await request<void>(`/groups/${groupId}`, { method: 'DELETE' })
  },
  async addParticipant(groupId: string, name: string) {
    return request<WirePerson>(`/groups/${groupId}/participants`, { method: 'POST', body: JSON.stringify({ name }) })
  },
  async removeParticipant(groupId: string, personId: string) {
    await request<void>(`/groups/${groupId}/participants/${personId}`, { method: 'DELETE' })
  },
  async saveExpense(groupId: string, input: Omit<Expense, 'id'>, expenseId?: string) {
    const payload = JSON.stringify({
      description: input.description,
      amount: input.amount.toFixed(2),
      payer_id: input.payerId,
      date: input.date,
      participant_ids: input.participantIds,
    })
    const path = expenseId ? `/expenses/${expenseId}` : `/groups/${groupId}/expenses`
    const method = expenseId ? 'PATCH' : 'POST'
    await request<WireExpense>(path, { method, body: payload })
  },
  async deleteExpense(_groupId: string, expenseId: string) {
    await request<void>(`/expenses/${expenseId}`, { method: 'DELETE' })
  },
  async getDashboard(groupId: string) {
    const [balanceData, suggestionData] = await Promise.all([
      request<WireBalances>(`/groups/${groupId}/balances`),
      request<WireSuggestions>(`/groups/${groupId}/settlement-suggestions`),
    ])
    return {
      total: Number(balanceData.total_expenses),
      outstanding: Number(balanceData.outstanding_amount),
      balances: balanceData.balances.map(balance => ({
        person: { id: balance.participant_id, name: balance.name },
        paid: Number(balance.total_paid),
        net: Number(balance.net_balance),
      })),
      transfers: suggestionData.transfers.map(transfer => ({
        from: transfer.payer_id,
        to: transfer.receiver_id,
        amount: Number(transfer.amount),
      })),
    }
  },
  async addSettlement(groupId: string, settlement: Omit<Settlement, 'id'>) {
    await request<WireSettlement>(`/groups/${groupId}/settlements`, {
      method: 'POST',
      body: JSON.stringify({
        payer_id: settlement.payerId,
        receiver_id: settlement.receiverId,
        amount: settlement.amount.toFixed(2),
        date: settlement.date,
      }),
    })
  },
}
