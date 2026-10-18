# Phase 1 — Setup and authentication

Goal: run a small React app that can call **`GET /health`**, **`POST /auth/register`**, **`POST /auth/login`**, and **`GET /auth/me`**. Store the JWT so later phases can send **`Authorization: Bearer &lt;token&gt;`**.

## Create the app

From a folder **outside** this repo (or a `frontend/` subfolder if you add it locally):

```bash
npm create vite@latest semantic-search-ui -- --template react
cd semantic-search-ui
npm install
```

Optional: `npm install react-router-dom` if you want separate URLs for login vs register.

## Configure the API base

Create `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Use `import.meta.env.VITE_API_BASE_URL` in your fetch helpers.

## Small API helper

- **`jsonRequest(method, path, { body?, token? })`**
  - Builds `URL` from base + path
  - Sets `Content-Type: application/json` when `body` is present
  - Sets `Authorization: Bearer ${token}` when `token` is present
  - `response.json()`; if `!response.ok`, throw with `data.message` or a fallback string

Register and login send **`POST`** with JSON body:

```json
{ "email": "user@example.com", "password": "password12" }
```

Password must be at least **8** characters (API validation).

## Token storage

After **register** or **login**, read **`data.access_token`** from the response and save it (e.g. **`sessionStorage.setItem('token', ...)`**). Clear it on logout.

**`GET /auth/me`** needs the header:

`Authorization: Bearer <access_token>`

Response includes **`data.email`** (and `id`, `created_at`).

## Screens (minimal)

1. **Health** (optional dev-only): button calls **`GET /health`**, show JSON or “ok”.
2. **Register**: email + password + submit → **`POST /auth/register`** → save token → go to “app shell” (Phase 2).
3. **Login**: same → **`POST /auth/login`**.
4. **Back / switch**: link “Already have an account? Log in” on register, and “Create account” on login (no separate cancel needed).

## Error handling

- **409** on register: duplicate email — show `message`.
- **401** on login: wrong credentials — show `message`.
- Network errors: show a short generic line.

## Checklist before Phase 2

- [ ] `VITE_API_BASE_URL` points at a running API
- [ ] CORS allows your Vite origin
- [ ] Token is stored and sent to **`/auth/me`**
- [ ] User can log out by clearing the token (simple link or button)
