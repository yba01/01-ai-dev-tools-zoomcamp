"""SQLAlchemy repository that maps relational rows to the API's domain records."""

from datetime import timezone
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .database import (
    ExpenseRow,
    ExpenseShareRow,
    GroupRow,
    ParticipantRow,
    SettlementRow,
    build_engine,
    initialize_schema,
)
from .models import ExpenseRead, GroupRecord, ParticipantRead, SettlementRead


class Store(Protocol):
    def list_groups(self) -> list[GroupRecord]: ...
    def get_group(self, group_id: str) -> GroupRecord | None: ...
    def put_group(self, group: GroupRecord) -> GroupRecord: ...
    def delete_group(self, group_id: str) -> bool: ...
    def get_expense(self, expense_id: str) -> tuple[GroupRecord, ExpenseRead] | None: ...
    def get_settlement(self, settlement_id: str) -> tuple[GroupRecord, SettlementRead] | None: ...


class SQLAlchemyStore:
    """Database adapter; configure it with any SQLAlchemy-supported URL."""

    def __init__(self, database_url: str, *, create_schema: bool = True) -> None:
        self.engine = build_engine(database_url)
        self.sessions: sessionmaker[Session] = sessionmaker(self.engine, expire_on_commit=False)
        if create_schema:
            initialize_schema(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()

    def list_groups(self) -> list[GroupRecord]:
        with self.sessions() as session:
            rows = session.scalars(select(GroupRow).order_by(GroupRow.created_at.desc(), GroupRow.id)).all()
            return [self._to_record(session, row) for row in rows]

    def get_group(self, group_id: str) -> GroupRecord | None:
        with self.sessions() as session:
            row = session.get(GroupRow, group_id)
            return self._to_record(session, row) if row else None

    def put_group(self, group: GroupRecord) -> GroupRecord:
        with self.sessions.begin() as session:
            row = session.get(GroupRow, group.id)
            if row is None:
                row = GroupRow(id=group.id, created_at=group.created_at)
                session.add(row)
            row.name = group.name
            row.description = group.description
            row.currency = group.currency
            row.created_at = group.created_at
            session.flush()

            expense_ids = {item.id for item in group.expenses}
            for existing in session.scalars(select(ExpenseRow).where(ExpenseRow.group_id == group.id)).all():
                if existing.id not in expense_ids:
                    session.delete(existing)
            settlement_ids = {item.id for item in group.settlements}
            for existing in session.scalars(select(SettlementRow).where(SettlementRow.group_id == group.id)).all():
                if existing.id not in settlement_ids:
                    session.delete(existing)
            session.flush()

            participant_ids = {person.id for person in group.participants}
            for existing in session.scalars(select(ParticipantRow).where(ParticipantRow.group_id == group.id)).all():
                if existing.id not in participant_ids:
                    session.delete(existing)
            session.flush()

            for position, person in enumerate(group.participants):
                participant = session.get(ParticipantRow, person.id)
                if participant is None:
                    participant = ParticipantRow(id=person.id, group_id=group.id)
                    session.add(participant)
                participant.group_id = group.id
                participant.name = person.name
                participant.normalized_name = person.name.casefold()
                participant.position = position
            session.flush()

            for position, expense in enumerate(group.expenses):
                stored = session.get(ExpenseRow, expense.id)
                if stored is None:
                    stored = ExpenseRow(id=expense.id, group_id=group.id)
                    session.add(stored)
                stored.group_id = group.id
                stored.payer_id = expense.payer_id
                stored.description = expense.description
                stored.amount = expense.amount
                stored.date = expense.date
                stored.position = position
                cents = int(expense.amount * 100)
                base, remainder = divmod(cents, len(expense.participant_ids))
                stored.shares = [
                    ExpenseShareRow(
                        participant_id=participant_id,
                        share_amount=Decimal(base + (1 if index < remainder else 0)) / 100,
                        position=index,
                    )
                    for index, participant_id in enumerate(expense.participant_ids)
                ]

            for position, settlement in enumerate(group.settlements):
                stored = session.get(SettlementRow, settlement.id)
                if stored is None:
                    stored = SettlementRow(id=settlement.id, group_id=group.id)
                    session.add(stored)
                stored.group_id = group.id
                stored.payer_id = settlement.payer_id
                stored.receiver_id = settlement.receiver_id
                stored.amount = settlement.amount
                stored.date = settlement.date
                stored.position = position

        result = self.get_group(group.id)
        if result is None:
            raise RuntimeError("Saved group could not be read back")
        return result

    def delete_group(self, group_id: str) -> bool:
        with self.sessions.begin() as session:
            row = session.get(GroupRow, group_id)
            if row is None:
                return False
            session.delete(row)
        return True

    def get_expense(self, expense_id: str) -> tuple[GroupRecord, ExpenseRead] | None:
        with self.sessions() as session:
            row = session.get(ExpenseRow, expense_id)
            if row is None:
                return None
            group_row = session.get(GroupRow, row.group_id)
            if group_row is None:
                return None
            group = self._to_record(session, group_row)
            expense = next((item for item in group.expenses if item.id == expense_id), None)
            return (group, expense) if expense is not None else None

    def get_settlement(self, settlement_id: str) -> tuple[GroupRecord, SettlementRead] | None:
        with self.sessions() as session:
            row = session.get(SettlementRow, settlement_id)
            if row is None:
                return None
            group_row = session.get(GroupRow, row.group_id)
            if group_row is None:
                return None
            group = self._to_record(session, group_row)
            settlement = next((item for item in group.settlements if item.id == settlement_id), None)
            return (group, settlement) if settlement is not None else None

    @staticmethod
    def _to_record(session: Session, row: GroupRow) -> GroupRecord:
        participants = session.scalars(
            select(ParticipantRow).where(ParticipantRow.group_id == row.id).order_by(ParticipantRow.position)
        ).all()
        expense_rows = session.scalars(
            select(ExpenseRow).where(ExpenseRow.group_id == row.id).order_by(ExpenseRow.position)
        ).all()
        settlement_rows = session.scalars(
            select(SettlementRow).where(SettlementRow.group_id == row.id).order_by(SettlementRow.position)
        ).all()
        expenses = [
            ExpenseRead(
                id=expense.id,
                description=expense.description,
                amount=expense.amount,
                payer_id=expense.payer_id,
                date=expense.date,
                participant_ids=[share.participant_id for share in expense.shares],
            )
            for expense in expense_rows
        ]
        return GroupRecord(
            id=row.id,
            name=row.name,
            description=row.description,
            currency=row.currency,
            created_at=row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc),
            participants=[ParticipantRead(id=person.id, name=person.name) for person in participants],
            expenses=expenses,
            settlements=[
                SettlementRead(
                    id=settlement.id,
                    payer_id=settlement.payer_id,
                    receiver_id=settlement.receiver_id,
                    amount=settlement.amount,
                    date=settlement.date,
                )
                for settlement in settlement_rows
            ],
        )
