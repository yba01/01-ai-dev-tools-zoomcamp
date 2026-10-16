# Expense Splitter API

FastAPI backend for the Expense Splitter. The repository did not contain the referenced `openapi.yaml`, so this API follows the routes and product behavior in `../_docs/spec.md`. FastAPI publishes the generated OpenAPI schema at `/openapi.json` and interactive docs at `/docs`.

## Run it

From this directory:

```sh
uv sync
uv run uvicorn expense_splitter.main:app --reload
```

The API listens on `http://127.0.0.1:8000`. The Vite frontend at `http://localhost:5173` is allowed by CORS.

The default database is a persistent SQLite file at `./expense_splitter.db`. PostgreSQL is supported with the included Psycopg 3 driver. Set `DATABASE_URL` to your PostgreSQL connection string, for example:

```sh
DATABASE_URL="postgresql://user:password@host:5432/expense_splitter" uv run uvicorn expense_splitter.main:app --host 0.0.0.0 --port 8000
```

The backend also accepts the `postgres://` and `postgresql+psycopg://` URL schemes. For hosted databases that require TLS, include the provider's SSL options in `DATABASE_URL` (for example, `?sslmode=require`). Keep credentials in environment configuration and do not commit them. The current MVP creates missing tables at startup; use database migrations before changing schemas in production.

## Tests

```sh
uv run pytest
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `GET`, `POST` | `/groups` | List and create groups |
| `GET`, `PATCH`, `DELETE` | `/groups/{group_id}` | Read, update, and delete a group |
| `GET`, `POST` | `/groups/{group_id}/participants` | List and add participants |
| `DELETE` | `/groups/{group_id}/participants/{participant_id}` | Remove a participant without financial history |
| `GET`, `POST` | `/groups/{group_id}/expenses` | List and create expenses |
| `PATCH`, `DELETE` | `/expenses/{expense_id}` | Update and delete expenses |
| `GET` | `/groups/{group_id}/balances` | Read totals and participant balances |
| `GET` | `/groups/{group_id}/settlement-suggestions` | Suggest transfers to settle outstanding balances |
| `GET`, `POST` | `/groups/{group_id}/settlements` | List and record completed settlements |

Money is accepted and returned as decimal strings with two fractional digits. Expense splits allocate remainder cents in the order of `participant_ids`. Settlement history is applied to reduce the debtor's outstanding amount and the creditor's claim.

## Persistence and schema

`SQLAlchemyStore` is the data access boundary. Groups, participants, expenses, ordered expense shares, and settlements are stored in relational tables with decimal-safe `NUMERIC` amounts and foreign keys. The repository hydrates the existing API records, so calculation code does not depend on SQLAlchemy or a specific database dialect.

The current MVP creates missing tables with SQLAlchemy metadata at startup. Introduce migrations before changing schemas in a deployed database.
