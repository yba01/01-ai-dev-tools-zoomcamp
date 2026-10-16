# Expense Splitter

Expense Splitter helps a group track shared expenses, see participant balances, and record settlements. The backend is the source of truth for balances and settlement suggestions. The app records settlements but does not transfer money.

## Features

- Create, edit, view, and delete groups.
- Add participants and record shared expenses split equally among selected members.
- View group totals, participant balances, expenses, and settlement history.
- Get settlement suggestions and record completed settlements.
- Persist application data in SQLite by default, using SQLAlchemy so another supported database can be configured.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js and npm

## Run the project

Run the backend and frontend in separate terminals.

### 1. Start the backend

```sh
cd "Build and Ship an AI-Assisted Full-Stack App/backend"
uv sync
uv run uvicorn expense_splitter.main:app --reload
```

The API runs at <http://127.0.0.1:8000>. Interactive API documentation is at <http://127.0.0.1:8000/docs> and the health check is at <http://127.0.0.1:8000/health>.

By default, the backend creates a persistent `backend/expense_splitter.db` SQLite database for local development. Psycopg 3 is included for PostgreSQL, and the backend accepts `postgresql://`, `postgres://`, and `postgresql+psycopg://` URLs. For example:

```sh
DATABASE_URL="postgresql://user:password@localhost:5432/expense_splitter" uv run uvicorn expense_splitter.main:app --reload
```

For a hosted PostgreSQL database that requires TLS, include its SSL options in the URL (for example, `?sslmode=require`). Keep credentials in environment configuration and do not commit them. The current MVP creates tables on startup; use database migrations before evolving a deployed schema.

### Run the full app with PostgreSQL in Docker

The Linux workspace Compose setup starts PostgreSQL with a persistent Docker volume, waits for the database health check, then starts the backend and serves the frontend on port 8000. It uses host networking for the backend because this workspace restricts TCP traffic between bridged containers; PostgreSQL is published only on host loopback port 55432:

```sh
cp .env.example .env
docker compose up --build
```

Open <http://localhost:8000>. Stop the services with `docker compose down`; the database volume is preserved. To also remove local database data, use `docker compose down --volumes`. The sample password in `.env.example` is for local development only.

For production, provision PostgreSQL with your hosting provider and pass its actual connection URL through the deployment platform’s secret or environment configuration. For example, set `DATABASE_URL` to `postgresql://USER:PASSWORD@DB_HOST:5432/expense_splitter?sslmode=require`. Do not use the sample Compose password in production.

### Deploy to Render

The repository-root `render.yaml` Blueprint defines only a free Render web service. It does not create a Render database. The Dockerfile builds the React/Vite frontend, copies its static output into the FastAPI image, and starts the backend on Render's injected `PORT`. FastAPI serves both the frontend and its `/api` routes from the same origin.

#### Configure Supabase

Create a Supabase project on the Free plan, then open **Connect** and copy the **Session pooler** URI. Use the session pooler for this long-running SQLAlchemy/Psycopg backend; the Supabase direct database host may require IPv6, and its transaction pooler has constraints for session-style clients. Add `sslmode=require` to the URI if it is not already present. Supabase's shared pooler supports IPv4, which is useful for external hosts such as Render.

In Render, connect this Git repository and choose **New + → Blueprint** to apply `render.yaml`. During the initial sync, enter the Supabase URI for `DATABASE_URL`. If configuring the service manually, add the same variable under **Environment**. Keep the URI only in Render's environment settings; do not commit it, put it in a frontend variable, or paste it into logs. The URI contains the database password. Do not use a Supabase `anon` or `service_role` API key as `DATABASE_URL`.

Required runtime configuration:

- `DATABASE_URL`: the secret Postgres connection URI from Supabase's Session pooler, with TLS (`sslmode=require`). The Blueprint marks this variable `sync: false` so the secret is entered in Render rather than stored in Git.
- `PORT`: supplied by Render. The Dockerfile uses it automatically; do not set a fixed port yourself.
- `VITE_API_BASE_URL`: not required for this deployment. The frontend defaults to same-origin `/api`, so leave this unset. Only set it at frontend build time if you intentionally host the frontend on a different origin.

The frontend and backend share the Render URL, so browser API calls are same-origin and do not need production CORS permission. The backend's localhost CORS entries are for separate local development origins. If you later split frontend and backend hosting, set `VITE_API_BASE_URL` to the backend's public URL and add the frontend's exact origin to the backend's CORS allowlist.

#### Database schema and migrations

The SQLAlchemy schema contains groups, participants, expenses, expense shares, and settlements, with foreign keys and uniqueness constraints. At startup, `SQLAlchemyStore` calls `Base.metadata.create_all()`. That creates missing tables on a new Supabase database, but it does not alter existing tables when models change. There is no migration tool or migration history in the project today. Before changing a deployed schema, add and review explicit versioned migrations (for example, Alembic) and run them as a controlled pre-deploy step; do not rely on `create_all()` for schema upgrades.

This setup uses only Render's free web-service plan and an independently created Supabase Free project. Free plans have sleep/pausing and quota limits; Supabase Free currently has a 500 MB database quota and can pause projects after a week of low activity. This is suitable for a small demo only while both providers' free-tier limits are respected. Check the current [Render free-tier limits](https://render.com/docs/free), [Supabase free-plan quotas](https://supabase.com/docs/guides/platform/billing-on-supabase), and [Supabase project pausing behavior](https://supabase.com/docs/guides/platform/free-project-pausing). The app has no authentication, so do not enter real or sensitive expense data.

### 2. Start the frontend

In a second terminal:

```sh
cd "Build and Ship an AI-Assisted Full-Stack App/frontent"
npm install
npm run dev
```

Open the URL printed by Vite, usually <http://localhost:5173>. In development, the frontend sends API requests through Vite's same-origin `/api` proxy to `http://127.0.0.1:8000`. This also works when the frontend is opened through a forwarded workspace URL. To call another backend directly, create `frontent/.env` using `frontent/.env.example`, set `VITE_API_BASE_URL`, and restart Vite.

## Run tests

From the backend directory:

```sh
uv run pytest
```

## Run Docker Compose integration tests

These black-box tests expect the Docker Compose stack to be running. From the project directory:

```sh
docker compose up --build -d
cd backend
TEST_DATABASE_URL="postgresql+psycopg://expense_splitter:local-dev-change-me@127.0.0.1:55432/expense_splitter" uv run pytest integration_tests
```

The integration suite includes a full end-to-end journey from the served frontend and assets through the `/api` routes, group and participant creation, expense splitting, settlements, and a direct PostgreSQL persistence check. It also checks that invalid expense references are rejected and that group deletion cascades cleanly. Test-created groups are deleted afterward. If you changed `POSTGRES_PASSWORD` in the project `.env`, use that same password in `TEST_DATABASE_URL`.

## Project layout

```text
backend/   FastAPI API, SQLAlchemy persistence, and pytest suite
frontent/  React + TypeScript + Vite application
_docs/     Product specification
```

## Notes

- The default group currency is XOF.
- Expense shares use decimal-safe amounts, and remainder cents are allocated deterministically.
- The backend currently has no authentication; it is intended for local development and demonstration.
