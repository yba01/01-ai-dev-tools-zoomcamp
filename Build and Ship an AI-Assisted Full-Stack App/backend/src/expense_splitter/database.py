"""Portable SQLAlchemy schema and engine setup for the current MVP."""

from datetime import date as DateType, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class GroupRow(Base):
    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="XOF")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    participants: Mapped[list["ParticipantRow"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True
    )
    expenses: Mapped[list["ExpenseRow"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True
    )
    settlements: Mapped[list["SettlementRow"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True
    )


class ParticipantRow(Base):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("group_id", "normalized_name", name="uq_participant_group_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    group: Mapped[GroupRow] = relationship(back_populates="participants")


class ExpenseRow(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    payer_id: Mapped[str] = mapped_column(ForeignKey("participants.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    date: Mapped[DateType] = mapped_column(Date, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    group: Mapped[GroupRow] = relationship(back_populates="expenses")
    shares: Mapped[list["ExpenseShareRow"]] = relationship(
        back_populates="expense",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ExpenseShareRow.position",
    )


class ExpenseShareRow(Base):
    __tablename__ = "expense_shares"

    expense_id: Mapped[str] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True)
    participant_id: Mapped[str] = mapped_column(ForeignKey("participants.id"), primary_key=True)
    share_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    expense: Mapped[ExpenseRow] = relationship(back_populates="shares")


class SettlementRow(Base):
    __tablename__ = "settlements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    payer_id: Mapped[str] = mapped_column(ForeignKey("participants.id"), nullable=False)
    receiver_id: Mapped[str] = mapped_column(ForeignKey("participants.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    group: Mapped[GroupRow] = relationship(back_populates="settlements")


def build_engine(database_url: str):
    options: dict = {"pool_pre_ping": True}
    if database_url.startswith("sqlite:"):
        options["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            options["poolclass"] = StaticPool
    engine = create_engine(database_url, **options)

    if database_url.startswith("sqlite:"):
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(connection, _record) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def initialize_schema(engine) -> None:
    Base.metadata.create_all(engine)
