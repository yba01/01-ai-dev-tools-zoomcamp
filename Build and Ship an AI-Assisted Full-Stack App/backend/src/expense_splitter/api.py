from decimal import Decimal
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import URL

from .calculations import balances_for, suggestions_for
from .models import (
    BalancesRead,
    ExpenseCreate,
    ExpensePatch,
    ExpenseRead,
    GroupCreate,
    GroupPatch,
    GroupRead,
    GroupRecord,
    ParticipantCreate,
    ParticipantRead,
    SettlementCreate,
    SettlementRead,
    SuggestionsRead,
)
from .store import SQLAlchemyStore, Store


def create_app(store: Store | None = None, *, database_url: str | None = None) -> FastAPI:
    app = FastAPI(
        title="Expense Splitter API",
        version="1.0.0",
        description="REST API for groups, shared expenses, balances, and manual settlements.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def strip_api_prefix(request, call_next):
        # The Vite development proxy strips /api before forwarding requests.
        # In the single-container deployment, accept that same prefix here.
        path = request.scope["path"]
        if path == "/api" or path.startswith("/api/"):
            request.scope["path"] = path[4:] or "/"
        return await call_next(request)

    frontend_dist = Path(os.getenv("FRONTEND_DIST", "/app/frontend/dist"))
    if store is None:
        configured_url = database_url or os.getenv("DATABASE_URL")
        if configured_url is None and os.getenv("POSTGRES_HOST"):
            configured_url = URL.create(
                "postgresql+psycopg",
                username=os.environ["POSTGRES_USER"],
                password=os.environ["POSTGRES_PASSWORD"],
                host=os.environ["POSTGRES_HOST"],
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "expense_splitter"),
                query={"sslmode": os.getenv("POSTGRES_SSLMODE", "require")},
            ).render_as_string(hide_password=False)
        configured_url = configured_url or "sqlite:///./expense_splitter.db"
        store = SQLAlchemyStore(configured_url)
    app.state.store = store

    def get_store() -> Store:
        return app.state.store

    def require_group(group_id: str) -> GroupRecord:
        group = get_store().get_group(group_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        return group

    def validate_expense_members(group: GroupRecord, payer_id: str, participant_ids: list[str]) -> None:
        member_ids = {person.id for person in group.participants}
        if payer_id not in member_ids:
            raise HTTPException(status_code=422, detail="Payer must be a participant in this group")
        if any(participant_id not in member_ids for participant_id in participant_ids):
            raise HTTPException(status_code=422, detail="All expense participants must belong to this group")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    async def frontend_index() -> FileResponse:
        index_file = frontend_dist / "index.html"
        if not index_file.is_file():
            raise HTTPException(
                status_code=503,
                detail="Frontend build is missing. Rebuild the Docker image from the project directory.",
            )
        return FileResponse(index_file)

    @app.post("/groups", response_model=GroupRead, status_code=status.HTTP_201_CREATED, tags=["groups"])
    async def create_group(payload: GroupCreate) -> GroupRecord:
        group = GroupRecord(id=str(uuid4()), **payload.model_dump())
        return get_store().put_group(group)

    @app.get("/groups", response_model=list[GroupRead], tags=["groups"])
    async def list_groups() -> list[GroupRecord]:
        return get_store().list_groups()

    @app.get("/groups/{group_id}", response_model=GroupRead, tags=["groups"])
    async def read_group(group_id: str) -> GroupRecord:
        return require_group(group_id)

    @app.patch("/groups/{group_id}", response_model=GroupRead, tags=["groups"])
    async def update_group(group_id: str, payload: GroupPatch) -> GroupRecord:
        group = require_group(group_id)
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=422, detail="At least one group field must be supplied")
        return get_store().put_group(group.model_copy(update=updates))

    @app.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["groups"])
    async def delete_group(group_id: str) -> Response:
        if not get_store().delete_group(group_id):
            raise HTTPException(status_code=404, detail="Group not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/groups/{group_id}/participants", response_model=ParticipantRead, status_code=status.HTTP_201_CREATED, tags=["participants"])
    async def create_participant(group_id: str, payload: ParticipantCreate) -> ParticipantRead:
        group = require_group(group_id)
        if any(person.name.casefold() == payload.name.casefold() for person in group.participants):
            raise HTTPException(status_code=409, detail="A participant with this name already exists in the group")
        person = ParticipantRead(id=str(uuid4()), name=payload.name)
        group.participants.append(person)
        get_store().put_group(group)
        return person

    @app.get("/groups/{group_id}/participants", response_model=list[ParticipantRead], tags=["participants"])
    async def list_participants(group_id: str) -> list[ParticipantRead]:
        return require_group(group_id).participants

    @app.delete("/groups/{group_id}/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["participants"])
    async def delete_participant(group_id: str, participant_id: str) -> Response:
        group = require_group(group_id)
        if not any(person.id == participant_id for person in group.participants):
            raise HTTPException(status_code=404, detail="Participant not found")
        has_history = any(expense.payer_id == participant_id or participant_id in expense.participant_ids for expense in group.expenses)
        has_history = has_history or any(s.payer_id == participant_id or s.receiver_id == participant_id for s in group.settlements)
        if has_history:
            raise HTTPException(status_code=409, detail="Participant has financial history and cannot be removed")
        group.participants = [person for person in group.participants if person.id != participant_id]
        get_store().put_group(group)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/groups/{group_id}/expenses", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED, tags=["expenses"])
    async def create_expense(group_id: str, payload: ExpenseCreate) -> ExpenseRead:
        group = require_group(group_id)
        validate_expense_members(group, payload.payer_id, payload.participant_ids)
        expense = ExpenseRead(id=str(uuid4()), **payload.model_dump())
        group.expenses.insert(0, expense)
        get_store().put_group(group)
        return expense

    @app.get("/groups/{group_id}/expenses", response_model=list[ExpenseRead], tags=["expenses"])
    async def list_expenses(group_id: str) -> list[ExpenseRead]:
        return require_group(group_id).expenses

    @app.patch("/expenses/{expense_id}", response_model=ExpenseRead, tags=["expenses"])
    async def update_expense(expense_id: str, payload: ExpensePatch) -> ExpenseRead:
        result = get_store().get_expense(expense_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Expense not found")
        group, old_expense = result
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=422, detail="At least one expense field must be supplied")
        data = old_expense.model_dump() | updates
        validate_expense_members(group, data["payer_id"], data["participant_ids"])
        updated = ExpenseRead(**(data | {"id": expense_id}))
        group.expenses = [updated if item.id == expense_id else item for item in group.expenses]
        get_store().put_group(group)
        return updated

    @app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["expenses"])
    async def delete_expense(expense_id: str) -> Response:
        result = get_store().get_expense(expense_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Expense not found")
        group, _ = result
        group.expenses = [item for item in group.expenses if item.id != expense_id]
        get_store().put_group(group)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/groups/{group_id}/balances", response_model=BalancesRead, tags=["balances"])
    async def read_balances(group_id: str) -> BalancesRead:
        group = require_group(group_id)
        balances = balances_for(group)
        total_expenses = sum((expense.amount for expense in group.expenses), Decimal("0.00"))
        outstanding = sum((line.net_balance for line in balances if line.net_balance > 0), Decimal("0.00"))
        return BalancesRead(
            group_id=group.id,
            currency=group.currency,
            total_expenses=total_expenses,
            participant_count=len(group.participants),
            expense_count=len(group.expenses),
            outstanding_amount=outstanding,
            balances=balances,
        )

    @app.get("/groups/{group_id}/settlement-suggestions", response_model=SuggestionsRead, tags=["settlements"])
    async def settlement_suggestions(group_id: str) -> SuggestionsRead:
        group = require_group(group_id)
        return SuggestionsRead(group_id=group.id, currency=group.currency, transfers=suggestions_for(balances_for(group)))

    @app.post("/groups/{group_id}/settlements", response_model=SettlementRead, status_code=status.HTTP_201_CREATED, tags=["settlements"])
    async def create_settlement(group_id: str, payload: SettlementCreate) -> SettlementRead:
        group = require_group(group_id)
        member_ids = {person.id for person in group.participants}
        if payload.payer_id not in member_ids or payload.receiver_id not in member_ids:
            raise HTTPException(status_code=422, detail="Both settlement participants must belong to this group")
        if payload.payer_id == payload.receiver_id:
            raise HTTPException(status_code=422, detail="A participant cannot settle with themselves")
        balances = {line.participant_id: line.net_balance for line in balances_for(group)}
        if balances.get(payload.payer_id, Decimal("0")) >= 0 or balances.get(payload.receiver_id, Decimal("0")) <= 0:
            raise HTTPException(status_code=422, detail="Settlement must go from a debtor to a creditor")
        if payload.amount > min(-balances[payload.payer_id], balances[payload.receiver_id]):
            raise HTTPException(status_code=422, detail="Settlement exceeds the outstanding debt or claim")
        settlement = SettlementRead(id=str(uuid4()), **payload.model_dump())
        group.settlements.insert(0, settlement)
        get_store().put_group(group)
        return settlement

    @app.get("/groups/{group_id}/settlements", response_model=list[SettlementRead], tags=["settlements"])
    async def list_settlements(group_id: str) -> list[SettlementRead]:
        return require_group(group_id).settlements

    # Mount last so the catch-all frontend route does not shadow API routes.
    # In production, Docker copies the Vite build here; local API development
    # remains possible when no frontend build is present.
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app
