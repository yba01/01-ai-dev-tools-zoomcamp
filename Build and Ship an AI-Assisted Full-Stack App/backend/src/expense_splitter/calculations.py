from collections import defaultdict
from decimal import Decimal

from .models import BalanceLine, GroupRecord, Transfer

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def expense_shares(group: GroupRecord) -> dict[str, Decimal]:
    """Allocate each expense in cents, giving remainder cents in participant order."""
    shares: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for expense in group.expenses:
        amount_cents = int(expense.amount * 100)
        base, remainder = divmod(amount_cents, len(expense.participant_ids))
        for index, participant_id in enumerate(expense.participant_ids):
            cents = base + (1 if index < remainder else 0)
            shares[participant_id] += Decimal(cents) / 100
    return shares


def balances_for(group: GroupRecord) -> list[BalanceLine]:
    shares = expense_shares(group)
    paid: dict[str, Decimal] = defaultdict(lambda: ZERO)
    settlement_effect: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for expense in group.expenses:
        paid[expense.payer_id] += expense.amount
    for settlement in group.settlements:
        # A completed transfer reduces the creditor's claim and the debtor's debt.
        settlement_effect[settlement.receiver_id] -= settlement.amount
        settlement_effect[settlement.payer_id] += settlement.amount
    return [
        BalanceLine(
            participant_id=person.id,
            name=person.name,
            total_paid=paid[person.id].quantize(CENT),
            total_share=shares[person.id].quantize(CENT),
            net_balance=(paid[person.id] - shares[person.id] + settlement_effect[person.id]).quantize(CENT),
        )
        for person in group.participants
    ]


def suggestions_for(balances: list[BalanceLine]) -> list[Transfer]:
    debtors = [[line.participant_id, -line.net_balance] for line in balances if line.net_balance < ZERO]
    creditors = [[line.participant_id, line.net_balance] for line in balances if line.net_balance > ZERO]
    transfers: list[Transfer] = []
    debtor_index = creditor_index = 0
    while debtor_index < len(debtors) and creditor_index < len(creditors):
        payer_id, debt = debtors[debtor_index]
        receiver_id, credit = creditors[creditor_index]
        amount = min(debt, credit).quantize(CENT)
        if amount > ZERO:
            transfers.append(Transfer(payer_id=payer_id, receiver_id=receiver_id, amount=amount))
        debtors[debtor_index][1] -= amount
        creditors[creditor_index][1] -= amount
        if debtors[debtor_index][1] == ZERO:
            debtor_index += 1
        if creditors[creditor_index][1] == ZERO:
            creditor_index += 1
    return transfers
