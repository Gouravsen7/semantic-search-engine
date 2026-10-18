# One-week completion plan

This is a proposed seven-day work schedule, not a record of past development.
The initial import commits use their actual creation dates.

| Day | Focus | Completion evidence |
| --- | --- | --- |
| 1 | Backend and account isolation | Unit tests pass; inspect ownership checks |
| 2 | Document ingestion and recovery | Exercise PDF/TXT, duplicate uploads, failures and restart recovery against a dedicated test database |
| 3 | Retrieval and generated answers | Run real pgvector/model integration; verify Gemini success, failure and missing-key behavior |
| 4 | Frontend workflows | Browser-test registration, login, upload, document details, search and logout |
| 5 | Security hardening | Replace custom JWT implementation with a maintained library, strengthen password hashing, move browser tokens to memory or secure cookie sessions, and fix trusted-proxy rate limiting |
| 6 | Deployment and operations | Configure production secrets, origins, TLS, database backups and dependency auditing; smoke-test deployment |
| 7 | Acceptance and handover | Repeat relevant checks after fixes, document remaining limitations and publish release |

## Initial import verification

- Backend: 72 unit tests passed using Python 3.11 and a fresh test environment.
- Frontend: `npm ci` and `npm run build` passed; npm reported zero known vulnerabilities.
- Source review: no matching API-key/private-key patterns found in reviewed application, test, example and documentation files. This is a heuristic check, not proof of absence.
- Local secrets, dependency directories, caches and frontend build output are ignored by Git.
- Real PostgreSQL, embedding-model and Gemini integration, Docker startup, and browser workflows have not been verified.
- The backend test environment excludes sentence-transformers and uvicorn; its dependency audit does not cover the complete deployed stack.
- The optional security skill scanner is unavailable; review was manual.

## Production findings

- Browser access tokens currently use sessionStorage, which is readable by injected JavaScript.
- JWTs are implemented manually; verification does not validate the header algorithm, issuer or audience. Configure a strong random signing secret and adopt a maintained JWT library.
- Passwords use salted PBKDF2-HMAC-SHA256 with 200,000 iterations. Plan migration to Argon2id or an appropriately configured maintained password library.
- Authentication rate limiting trusts arbitrary X-Forwarded-For headers and stores limits per process. Configure trusted proxies and enforce shared limits with Retry-After responses.
- Development database credentials must be replaced before production. MFA is absent; assess requirements for sensitive document accounts.
- React escapes rendered content, but a production Content-Security-Policy still needs configuration.
- SQL queries use SQLAlchemy expressions or static SQL; document access and search are scoped to authenticated owners. The database is accessed through the backend.
- Uploads have size/type checks and sanitized names; original uploaded files are not written to user-selected paths. TXT content detection remains permissive, and PDF parser resource limits need integration testing.
- CORS uses configured origins. Authentication uses explicit bearer headers rather than cookies. No webhook handlers were found.
- Gemini requests use a fixed provider host; queries and retrieved excerpts may be sent to Google when configured. Keep credentials server-side and review provider-error logging for accidental disclosures.
- Frontend production output contains no emitted source maps with the current Vite defaults.
- Python requirements have broad lower bounds and no lockfile. Audit and lock the full deployment dependency set before release.

Passing unit tests and a frontend build does not establish production readiness.
