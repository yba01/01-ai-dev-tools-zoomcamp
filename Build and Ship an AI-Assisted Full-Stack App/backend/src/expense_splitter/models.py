from datetime import date as Date, datetime, timezone
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
def fixed_scale(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


Money = Annotated[Decimal, Field(gt=Decimal("0"), max_digits=14, decimal_places=2), AfterValidator(fixed_scale)]
Amount = Annotated[Decimal, AfterValidator(fixed_scale)]
Currency = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$", to_upper=True)]


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GroupCreate(APIModel):
    name: Name
    description: str = Field(default="", max_length=500)
    currency: Currency = "XOF"


class GroupPatch(APIModel):
    name: Name | None = None
    description: str | None = Field(default=None, max_length=500)
    currency: Currency | None = None

    @model_validator(mode="after")
    def reject_null_updates(self):
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Group fields cannot be null")
        return self


class ParticipantCreate(APIModel):
    name: Name


class ParticipantRead(APIModel):
    id: str
    name: str


class ExpenseCreate(APIModel):
    description: Description
    amount: Money
    payer_id: str
    date: Date
    participant_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_participants(self):
        if len(set(self.participant_ids)) != len(self.participant_ids):
            raise ValueError("participant_ids must not contain duplicates")
        return self


class ExpensePatch(APIModel):
    description: Description | None = None
    amount: Money | None = None
    payer_id: str | None = None
    date: Date | None = None
    participant_ids: list[str] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def reject_null_updates(self):
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Expense fields cannot be null")
        return self

    @model_validator(mode="after")
    def unique_participants(self):
        if self.participant_ids is not None and len(set(self.participant_ids)) != len(self.participant_ids):
            raise ValueError("participant_ids must not contain duplicates")
        return self


class ExpenseRead(APIModel):
    id: str
    description: str
    amount: Amount
    payer_id: str
    date: Date
    participant_ids: list[str]


class SettlementCreate(APIModel):
    payer_id: str
    receiver_id: str
    amount: Money
    date: Date


class SettlementRead(APIModel):
    id: str
    payer_id: str
    receiver_id: str
    amount: Amount
    date: Date


class GroupRead(APIModel):
    id: str
    name: str
    description: str
    currency: str
    created_at: datetime
    participants: list[ParticipantRead]
    expenses: list[ExpenseRead]
    settlements: list[SettlementRead]


class BalanceLine(APIModel):
    participant_id: str
    name: str
    total_paid: Decimal
    total_share: Decimal
    net_balance: Decimal


class BalancesRead(APIModel):
    group_id: str
    currency: str
    total_expenses: Decimal
    participant_count: int
    expense_count: int
    outstanding_amount: Decimal
    balances: list[BalanceLine]


class Transfer(APIModel):
    payer_id: str
    receiver_id: str
    amount: Decimal


class SuggestionsRead(APIModel):
    group_id: str
    currency: str
    transfers: list[Transfer]


class GroupRecord(BaseModel):
    id: str
    name: str
    description: str = ""
    currency: str = "XOF"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    participants: list[ParticipantRead] = Field(default_factory=list)
    expenses: list[ExpenseRead] = Field(default_factory=list)
    settlements: list[SettlementRead] = Field(default_factory=list)
