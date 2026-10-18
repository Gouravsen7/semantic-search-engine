# Semantic Search Engine — React UI (phased docs)

These files describe a **minimal** browser UI for the existing REST API. They do **not** change the backend. You can still use [postman/semantic-search-engine.postman_collection.json](../../postman/semantic-search-engine.postman_collection.json) for the same requests.

## App in this repo

A runnable UI lives in **[frontend/](../../frontend/)** (see [frontend/README.md](../../frontend/README.md)) with **Chat** (`/chat`) and **Documents** (`/documents`, `/documents/upload`).

## Stack

- **React** with **Vite** (JavaScript, not TypeScript unless you choose otherwise)
- **`fetch`** for HTTP (no extra dependency required)
- **React Router** (or similar) for a few routes — optional; you can use one page with conditional views if you prefer

## Environment

| Variable | Example | Purpose |
| -------- | ------- | ------- |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Base URL for all API calls (no trailing slash) |

Put this in `.env` at the root of the Vite app. Vite exposes only variables prefixed with `VITE_`.

## CORS

The API reads allowed browser origins from `CORS_ORIGINS` (see [README.md](../../README.md)). For Vite’s dev server, include **`http://localhost:5173`** (or whatever port you use). Restart the API after changing `.env`.

## Response shape

Successful responses: `{ "message": string, "data": ... }`.

Errors: `{ "message": string }` with a non-2xx status (e.g. 401, 409). Read `message` and show it to the user.

## Phases (build in order)

| Phase | File | Covers |
| ----- | ---- | ------ |
| 1 | [phase-01-setup-and-auth.md](phase-01-setup-and-auth.md) | Project setup, health check, register, login, current user |
| 2 | [phase-02-upload-and-documents.md](phase-02-upload-and-documents.md) | Upload UI (mock style), list, detail, delete, polling |
| 3 | [phase-03-search.md](phase-03-search.md) | Search query and results |

## Backend URL

Default API: `http://localhost:8000` (see [README.md](../../README.md) for Docker vs local).
