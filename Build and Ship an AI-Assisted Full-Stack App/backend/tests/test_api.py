import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from expense_splitter.api import create_app
from expense_splitter.database import ExpenseRow, ExpenseShareRow, GroupRow, ParticipantRow
from expense_splitter.store import SQLAlchemyStore


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def client() -> AsyncClient:
    app = create_app(store=SQLAlchemyStore("sqlite://"))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def create_group(client: AsyncClient, name: str = "Dakar weekend") -> dict:
    response = await client.post(
        "/groups",
        json={"name": name, "description": "A trip", "currency": "XOF"},
    )
    assert response.status_code == 201
    return response.json()


async def add_people(client: AsyncClient, group_id: str) -> dict[str, str]:
    people = {}
    for name in ("Amina", "Ibrahima", "Fatou"):
        response = await client.post(
            f"/groups/{group_id}/participants", json={"name": name}
        )
        assert response.status_code == 201
        people[name] = response.json()["id"]
    return people


@pytest.mark.anyio
async def test_group_crud_and_validation(client: AsyncClient) -> None:
    assert (await client.get("/groups")).json() == []
    group = await create_group(client)
    assert (await client.get(f"/groups/{group['id']}")).json()["name"] == "Dakar weekend"
    update = await client.patch(f"/groups/{group['id']}", json={"name": "Trip"})
    assert update.json()["name"] == "Trip"
    assert (await client.post("/groups", json={"name": "  "})).status_code == 422
    assert (await client.delete(f"/groups/{group['id']}")).status_code == 204
    assert (await client.get(f"/groups/{group['id']}")).status_code == 404
    await client.aclose()


@pytest.mark.anyio
async def test_participant_validation_and_history_protection(client: AsyncClient) -> None:
    group = await create_group(client)
    people = await add_people(client, group["id"])
    path = f"/groups/{group['id']}/participants"
    assert (await client.get(path)).status_code == 200
    assert (await client.post(path, json={"name": "amina"})).status_code == 409
    assert (await client.delete(f"{path}/{people['Amina']}")).status_code == 204
    assert (await client.get(path)).json()[0]["name"] == "Ibrahima"
    remaining = (await client.get(path)).json()
    expense = {"description": "Lunch", "amount": "10", "payer_id": remaining[0]["id"], "date": "2026-10-15", "participant_ids": [person["id"] for person in remaining]}
    assert (await client.post(f"/groups/{group['id']}/expenses", json=expense)).status_code == 201
    assert (await client.delete(f"{path}/{remaining[0]['id']}")).status_code == 409
    await client.aclose()


@pytest.mark.anyio
async def test_expenses_split_balances_and_settlement_suggestions(client: AsyncClient) -> None:
    group = await create_group(client)
    gid = group["id"]
    people = await add_people(client, gid)
    expense = {
        "description": "Villa groceries",
        "amount": "10000",
        "payer_id": people["Amina"],
        "date": "2026-10-15",
        "participant_ids": list(people.values()),
    }
    created = await client.post(f"/groups/{gid}/expenses", json=expense)
    assert created.status_code == 201
    assert (await client.get(f"/groups/{gid}/expenses")).json()[0]["amount"] == "10000.00"
    balances = (await client.get(f"/groups/{gid}/balances")).json()
    by_name = {item["name"]: item for item in balances["balances"]}
    assert by_name["Amina"]["total_share"] == "3333.34"
    assert by_name["Ibrahima"]["total_share"] == "3333.33"
    assert by_name["Fatou"]["total_share"] == "3333.33"
    suggestions = (await client.get(f"/groups/{gid}/settlement-suggestions")).json()["transfers"]
    assert suggestions == [
        {"payer_id": people["Ibrahima"], "receiver_id": people["Amina"], "amount": "3333.33"},
        {"payer_id": people["Fatou"], "receiver_id": people["Amina"], "amount": "3333.33"},
    ]
    await client.aclose()


@pytest.mark.anyio
async def test_expense_update_delete_and_invalid_references(client: AsyncClient) -> None:
    group = await create_group(client)
    gid = group["id"]
    people = await add_people(client, gid)
    payload = {"description": "Taxi", "amount": "1200", "payer_id": people["Amina"], "date": "2026-10-15", "participant_ids": [people["Amina"], people["Ibrahima"]]}
    assert (await client.post(f"/groups/{gid}/expenses", json={**payload, "amount": "0"})).status_code == 422
    assert (await client.post(f"/groups/{gid}/expenses", json={**payload, "payer_id": "outside"})).status_code == 422
    assert (await client.post(f"/groups/{gid}/expenses", json={**payload, "participant_ids": []})).status_code == 422
    expense = (await client.post(f"/groups/{gid}/expenses", json=payload)).json()
    update = {**payload, "description": "Updated taxi", "amount": "1400"}
    assert (await client.patch(f"/expenses/{expense['id']}", json=update)).json()["description"] == "Updated taxi"
    assert (await client.get(f"/groups/{gid}/balances")).json()["total_expenses"] == "1400.00"
    assert (await client.delete(f"/expenses/{expense['id']}")).status_code == 204
    assert (await client.get(f"/groups/{gid}/balances")).json()["total_expenses"] == "0.00"
    await client.aclose()


@pytest.mark.anyio
async def test_settlement_history_and_balance_recalculation(client: AsyncClient) -> None:
    group = await create_group(client)
    gid = group["id"]
    people = await add_people(client, gid)
    expense = {"description": "Food", "amount": "900", "payer_id": people["Amina"], "date": "2026-10-15", "participant_ids": list(people.values())}
    await client.post(f"/groups/{gid}/expenses", json=expense)
    path = f"/groups/{gid}/settlements"
    bad = {"payer_id": people["Ibrahima"], "receiver_id": people["Amina"], "amount": "999", "date": "2026-10-15"}
    assert (await client.post(path, json=bad)).status_code == 422
    assert (await client.post(path, json={**bad, "amount": "0.01"})).status_code == 201
    assert len((await client.get(path)).json()) == 1
    balances = (await client.get(f"/groups/{gid}/balances")).json()["balances"]
    ibrahima = next(item for item in balances if item["participant_id"] == people["Ibrahima"])
    assert ibrahima["net_balance"] == "-299.99"
    suggestions = (await client.get(f"/groups/{gid}/settlement-suggestions")).json()["transfers"]
    for transfer in suggestions:
        result = await client.post(path, json={**transfer, "date": "2026-10-15"})
        assert result.status_code == 201
    settled_balances = (await client.get(f"/groups/{gid}/balances")).json()["balances"]
    assert all(item["net_balance"] == "0.00" for item in settled_balances)
    await client.aclose()


@pytest.mark.anyio
async def test_missing_resources_return_404(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    assert "/groups/{group_id}/balances" in schema["paths"]
    assert "/groups/{group_id}/settlement-suggestions" in schema["paths"]
    assert (await client.get("/groups/missing")).status_code == 404
    assert (await client.get("/groups/missing/expenses")).status_code == 404
    assert (await client.patch("/expenses/missing", json={})).status_code == 404
    preflight = await client.options(
        "/groups",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
    await client.aclose()


@pytest.mark.anyio
async def test_database_persists_records_between_app_instances(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'expense-splitter.db'}"
    first_store = SQLAlchemyStore(database_url)
    first_client = AsyncClient(
        transport=ASGITransport(app=create_app(store=first_store)),
        base_url="http://test",
    )
    group = await create_group(first_client, "Persistent trip")
    person = await first_client.post(
        f"/groups/{group['id']}/participants", json={"name": "Amina"}
    )
    assert person.status_code == 201
    expense = {
        "description": "Dinner",
        "amount": "1250.00",
        "payer_id": person.json()["id"],
        "date": "2026-10-15",
        "participant_ids": [person.json()["id"]],
    }
    assert (await first_client.post(f"/groups/{group['id']}/expenses", json=expense)).status_code == 201
    await first_client.aclose()
    first_store.dispose()

    reopened_store = SQLAlchemyStore(database_url)
    second_client = AsyncClient(
        transport=ASGITransport(app=create_app(store=reopened_store)),
        base_url="http://test",
    )
    persisted_group = (await second_client.get(f"/groups/{group['id']}")).json()
    assert persisted_group["name"] == "Persistent trip"
    assert persisted_group["participants"][0]["name"] == "Amina"
    assert persisted_group["expenses"][0]["amount"] == "1250.00"
    assert (await second_client.get(f"/groups/{group['id']}/balances")).json()["total_expenses"] == "1250.00"
    await second_client.aclose()
    reopened_store.dispose()


@pytest.mark.anyio
async def test_deleting_group_cascades_related_database_rows() -> None:
    store = SQLAlchemyStore("sqlite://")
    client = AsyncClient(transport=ASGITransport(app=create_app(store=store)), base_url="http://test")
    group = await create_group(client, "Cascade test")
    person = (await client.post(f"/groups/{group['id']}/participants", json={"name": "Amina"})).json()
    expense = {"description": "Coffee", "amount": "450", "payer_id": person["id"], "date": "2026-10-15", "participant_ids": [person["id"]]}
    assert (await client.post(f"/groups/{group['id']}/expenses", json=expense)).status_code == 201
    assert (await client.delete(f"/groups/{group['id']}")).status_code == 204
    with store.sessions() as session:
        assert session.scalar(select(func.count()).select_from(GroupRow)) == 0
        assert session.scalar(select(func.count()).select_from(ParticipantRow)) == 0
        assert session.scalar(select(func.count()).select_from(ExpenseRow)) == 0
        assert session.scalar(select(func.count()).select_from(ExpenseShareRow)) == 0
    await client.aclose()
    store.dispose()
