# Expense Splitter frontend

During development, the frontend calls the backend through Vite's same-origin `/api` proxy, which forwards requests to `http://127.0.0.1:8000`. This works when the frontend is opened through a forwarded workspace URL. Set `VITE_API_BASE_URL` in a local `.env` file only if you need to call a backend directly from the browser.

```sh
npm install
npm run dev
```

Start the backend separately from `../backend` with `uv run uvicorn expense_splitter.main:app --reload`.
