FROM node:22-alpine AS frontend-build

WORKDIR /app/frontent
COPY frontent/package.json frontent/package-lock.json ./
RUN npm ci
COPY frontent/ ./
RUN npm run build

FROM python:3.12-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIST=/app/frontend/dist \
    UV_PROJECT_ENVIRONMENT=/app/backend/.venv
WORKDIR /app/backend

RUN pip install --no-cache-dir uv
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --locked --no-dev

COPY --from=frontend-build /app/frontent/dist /app/frontend/dist

EXPOSE 8000
CMD ["/bin/sh", "-c", "exec /app/backend/.venv/bin/uvicorn expense_splitter.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
