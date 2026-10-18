# Production checklist (no API contract changes)

Use this after the audit fixes already in the repo.

## Before exposing the API

1. Set a long random `JWT_SECRET` and `ALLOW_INSECURE_JWT=false`.
2. Set strong `POSTGRES_USER` / `POSTGRES_PASSWORD`; do not publish Postgres beyond localhost without a firewall.
3. Set `CORS_ORIGINS` to your real UI origins only.
4. Configure `GEMINI_API_KEY` only if you accept that queries and retrieved excerpts are sent to Google.

## Dependency audit (CI or locally)

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

Install from `requirements.txt` (same packages as today; versions are bounded there).

## Still recommended later (larger projects)

- Durable upload queue and stored file bytes (reliability after crashes).
- Versioned DB migrations (Alembic).
- HttpOnly cookie sessions instead of bearer tokens in the browser.
- Pagination on large document lists.

None of these require changing current endpoint paths or JSON shapes when implemented carefully.