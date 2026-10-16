export type Person = { id: string; name: string }
export type Expense = { id: string; description: string; amount: number; payerId: string; date: string; participantIds: string[] }
export type Settlement = { id: string; payerId: string; receiverId: string; amount: number; date: string }
export type Group = { id: string; name: string; description: string; currency: string; createdAt: string; participants: Person[]; expenses: Expense[]; settlements: Settlement[] }
