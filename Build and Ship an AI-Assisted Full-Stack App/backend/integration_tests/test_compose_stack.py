"""Black-box checks against the running Docker Compose app and PostgreSQL."""

from __future__ import annotations

import os
import re
import uuid
from datetime import date
from typing import Iterator

import httpx
import pytest
from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.orm import Session

from expense_splitter.database import GroupRow


APP_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://expense_splitter:local-dev-change-me@127.0.0.1:55432/expense_splitter",
)


@pytest.fixture(scope="session")
def client() -> Iterator[httpx.Client]:
    test_client = httpx.Client(base_url=APP_URL, timeout=5)
    try:
        response = test_client.get("/health")
    except httpx.HTTPError as exc:
        pytest.fail(
            f"Compose app is not reachable at {APP_URL}. Start it with "
            f"`docker compose up --build -d` before running integration tests. ({exc})"
        )
    if response.status_code != 200:
        pytest.fail(f"Compose app health check failed: HTTP {response.status_code}")
    yield test_client
    test_client.close()


@pytest.fixture(scope="session")
def postgres_engine() -> Iterator[Engine]:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("select current_database()")) == "expense_splitter"
    except Exception as exc:
        engine.dispose()
        pytest.fail(
            "Could not connect to the Compose PostgreSQL service. Check that db is healthy "
            f"and TEST_DATABASE_URL matches POSTGRES_PASSWORD. ({exc})"
        )
    yield engine
    engine.dispose()


def test_frontend_and_api_are_served_by_backend(client: httpx.Client) -> None:
    frontend = client.get("/")
    assert frontend.status_code == 200
    assert "<div id=\"root\"></div>" in frontend.text

    assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', frontend.text)
    assert assets, "The built frontend should reference at least one static asset"
    for asset_path in assets:
        assert client.get(asset_path).status_code == 200

    assert client.get("/api/groups").status_code == 200


def test_end_to_end_user_can_split_and_settle_an_expense_in_postgres(
    client: httpx.Client,
    postgres_engine,
) -> None:
    # Start at the deployed frontend, then use its same-origin API path.
    frontend = client.get("/")
    assert frontend.status_code == 200
    assert "<div id=\"root\"></div>" in frontend.text
    assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', frontend.text)
    assert assets
    assert all(client.get(asset_path).status_code == 200 for asset_path in assets)
    assert client.get("/api/groups").status_code == 200

    group_name = f"Compose integration {uuid.uuid4()}"
    group_response = client.post(
        "/api/groups",
        json={"name": group_name, "description": "integration test", "currency": "XOF"},
    )
    assert group_response.status_code == 201, group_response.text
    group = group_response.json()
    group_id = group["id"]

    try:
        participants: dict[str, str] = {}
        for name in ("Amina", "Ibrahima", "Fatou"):
            response = client.post(f"/api/groups/{group_id}/participants", json={"name": name})
            assert response.status_code == 201, response.text
            participants[name] = response.json()["id"]

        expense_response = client.post(
            f"/api/groups/{group_id}/expenses",
            json={
                "description": "Shared dinner",
                "amount": "10000.00",
                "payer_id": participants["Amina"],
                "date": date.today().isoformat(),
                "participant_ids": list(participants.values()),
            },
        )
        assert expense_response.status_code == 201, expense_response.text

        balances_response = client.get(f"/api/groups/{group_id}/balances")
        assert balances_response.status_code == 200
        balances = {line["name"]: line for line in balances_response.json()["balances"]}
        assert balances["Amina"]["net_balance"] == "6666.66"
        assert balances["Ibrahima"]["net_balance"] == "-3333.33"
        assert balances["Fatou"]["net_balance"] == "-3333.33"

        suggestions = client.get(f"/api/groups/{group_id}/settlement-suggestions").json()["transfers"]
        assert len(suggestions) == 2
        for transfer in suggestions:
            response = client.post(
                f"/api/groups/{group_id}/settlements",
                json={**transfer, "date": date.today().isoformat()},
            )
            assert response.status_code == 201, response.text

        final_balances = client.get(f"/api/groups/{group_id}/balances").json()["balances"]
        assert all(line["net_balance"] == "0.00" for line in final_balances)

        # Assert the API writes to PostgreSQL itself, not a local SQLite file.
        with Session(postgres_engine) as session:
            stored_group = session.scalar(select(GroupRow).where(GroupRow.id == group_id))
            assert stored_group is not None
            assert stored_group.name == group_name
            assert len(stored_group.participants) == 3
            assert len(stored_group.expenses) == 1
            assert len(stored_group.settlements) == 2

        # A subsequent request re-reads the committed record from the backend.
        persisted = client.get(f"/api/groups/{group_id}")
        assert persisted.status_code == 200
        assert persisted.json()["name"] == group_name
    finally:
        deleted = client.delete(f"/api/groups/{group_id}")
        assert deleted.status_code == 204, deleted.text

    with Session(postgres_engine) as session:
        assert session.get(GroupRow, group_id) is None


def test_invalid_expense_references_are_rejected(client: httpx.Client) -> None:
    group_name = f"Compose validation {uuid.uuid4()}"
    response = client.post("/api/groups", json={"name": group_name})
    assert response.status_code == 201, response.text
    group_id = response.json()["id"]
    try:
        person = client.post(f"/api/groups/{group_id}/participants", json={"name": "Amina"})
        assert person.status_code == 201, person.text
        invalid_expense = client.post(
            f"/api/groups/{group_id}/expenses",
            json={
                "description": "Invalid payer",
                "amount": "100.00",
                "payer_id": "not-a-member",
                "date": date.today().isoformat(),
                "participant_ids": [person.json()["id"]],
            },
        )
        assert invalid_expense.status_code == 422
    finally:
        deleted = client.delete(f"/api/groups/{group_id}")
        assert deleted.status_code == 204, deleted.text
