# Semantic Search — web UI

Minimal React (Vite) client for the API in this repo. Same requests as Postman.

## Setup

```bash
cd frontend
cp .env.example .env
# edit .env if your API is not on http://localhost:8000
npm install
npm run dev
```

Open the URL Vite prints (usually **http://localhost:5173**).

## Backend

- Run the API on the host URL in `VITE_API_BASE_URL`.
- `CORS_ORIGINS` must include the UI origin (default Vite: `http://localhost:5173`).

## Routes

- `/register` — create account
- `/login` — sign in
- `/chat` / `/chat/:sessionId` — chat-style search with **Recents** in the sidebar; each thread title comes from your first message in that chat (POST `/search` with only `query`)
- `/documents` — document listing (GET `/documents`, delete, links to detail)
- `/documents/upload` — upload queue + progress (POST `/documents`, poll GET `/documents/{id}`)
- `/documents/view/:documentId` — document detail with chunks (GET `/documents/{id}`)
