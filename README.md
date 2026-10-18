# Semantic Search Engine

REST API that accepts PDF and TXT documents, splits them into chunks, stores embeddings in PostgreSQL with pgvector, and searches those chunks with natural language. Each account sees only its own documents and search results.

The original file is not kept. The API stores the filename, file size, extracted text chunks, and a 384-dimensional embedding for each chunk.

Phased **React (Vite) UI** notes (no API changes): [docs/ui/README.md](docs/ui/README.md).

Run the included UI from [frontend/](frontend/): `cd frontend && cp .env.example .env && npm install && npm run dev` (see [frontend/README.md](frontend/README.md)). After login you land on **Chat**; use the sidebar for **Documents** (listing and upload).

## Stack

- Python 3.11
- FastAPI and Pydantic
- PostgreSQL 16 with pgvector
- SQLAlchemy
- `sentence-transformers/all-MiniLM-L6-v2`
- PyMuPDF

Embedding runs inside the API process. There is no Redis, queue, or separate model service.

## Layout

```
app/
  main.py                      # app factory, lifespan, error handlers
  api/routes/                  # documents, search, health
  api/deps.py                  # database session and service wiring
  core/config.py               # environment settings
  db/database.py               # engine, sessions, schema setup
  db/models.py                 # documents and chunks
  schemas/                     # request and response models
  services/document_processor.py
  services/document_service.py
  services/embedding_service.py
  services/search_service.py
  utils/text_chunker.py
tests/
```

## Run with Docker

Docker Compose starts PostgreSQL with pgvector and the API.

```bash
docker compose up --build
```

The API listens on `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

The first search or upload downloads the embedding model into a Docker volume. That request can take a minute.

## Run locally

Use this when you want to run the API on the host and keep Postgres in Docker.

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up db -d
uvicorn app.main:app --reload
```

Startup creates the `vector` extension, the tables, and an HNSW index on chunk embeddings.

If this database was created before accounts existed, reset it once with `docker compose down -v`. That deletes the local Postgres volume.

Postgres is published on host port 5433 so it does not collide with a Postgres already listening on 5432. Inside Compose, the API still reaches the database on port 5432.

## API

- `GET /health` checks PostgreSQL. No token.
- `POST /auth/register` creates an account and returns a bearer token.
- `POST /auth/login` checks email and password and returns a bearer token.
- `GET /auth/me` returns the user for the token.
- `POST /documents` uploads one PDF or TXT file (`multipart/form-data`, field name `file`).
- `GET /documents` lists the signed-in user's documents, newest first.
- `GET /documents/{document_id}` returns that user's document and chunk text.
- `DELETE /documents/{document_id}` deletes that user's document and its chunks. Returns `{"message": "Document deleted."}`.
- `POST /search` uses Gemini to pick a document category and rewrite the query, searches the closest chunks (scoped to that category when the matches are strong enough), then writes a plain-language `answer` from those passages. Body: `{"query": "natural language", "top_k": 5}`. The response includes `interpreted_query`, `category` (the category actually searched, or null when search ran across all documents), and `answer`. If nothing relevant is stored, `answer` says it was not found.

Document and search routes expect `Authorization: Bearer <access_token>`. A missing or bad token returns 401. Another user's document returns 404.

A successful response always has two keys. `message` says what happened. `data` holds the record. An empty list still uses `data`, with a message such as `No documents found.` A failure returns only `message`, and that text is the error that actually happened.

```json
{
  "message": "User fetched.",
  "data": {
    "id": "9d7a277c-c91b-47d8-a1ec-c286a6878dd8",
    "email": "ada@example.com",
    "created_at": "2026-11-03T10:48:15.281574Z"
  }
}
```

`top_k` is optional. The default is 5 and the maximum is 20. Results are ordered by cosine similarity. A higher `score` is a closer match.

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "ada@example.com", "password": "password12"}'

curl -F "file=@notes.txt;type=text/plain" \
  -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/documents

curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"query": "household pets", "top_k": 3}'
```

The upload response returns immediately with `status: "processing"`. Call `GET /documents/{id}` until `status` is `ready` or `failed`. Search includes a document only after it is `ready`. A failed document keeps the error in `error_message`.

Uploads are rejected when the file is empty, the type is not PDF or TXT, or the file is larger than `MAX_UPLOAD_SIZE_BYTES` (50 MB by default). Uploading the same file bytes again for the same user returns 409 while an earlier copy is still `processing` or `ready`; a `failed` upload of the same bytes can be retried. Document list and detail responses include `category` once processing finishes (`null` while `processing`). A file with no readable text is accepted, then marked `failed`.

Import `postman/semantic-search-engine.postman_collection.json` to call the same endpoints. The collection variable `baseUrl` defaults to `http://localhost:8000`. Register or log in first; that saves `token` for the document and search requests. Choose a PDF or TXT file on the upload request. A successful upload stores `documentId` for the get and delete requests.

## Configuration

Copy `.env.example` to `.env`. The useful values are:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | local Postgres URL | SQLAlchemy connection string |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Hugging Face model id |
| `EMBEDDING_DIMENSION` | `384` | Must match the model |
| `CHUNK_SIZE` | `500` | Target chunk size in characters |
| `CHUNK_OVERLAP` | `50` | Trailing words copied into the next chunk |
| `MAX_UPLOAD_SIZE_BYTES` | `52428800` | Upload limit, 50 MB |
| `DEFAULT_TOP_K` | `5` | Search results when `top_k` is omitted |
| `MAX_TOP_K` | `20` | Largest accepted `top_k` |
| `JWT_SECRET` | local dev value | Signs access tokens. Use a strong random value in production |
| `ALLOW_INSECURE_JWT` | `false` | Set `true` only for local dev with the default `JWT_SECRET` |
| `JWT_EXPIRE_MINUTES` | `1440` | Token lifetime |
| `MIN_SEARCH_SCORE` | `0.25` | Drop search hits below this cosine similarity |
| `MAX_CONCURRENT_UPLOAD_JOBS` | `2` | Parallel background upload workers per API process |
| `CORS_ORIGINS` | local React ports | Comma-separated browser origins allowed to call the API |
| `GEMINI_API_KEY` | empty | Google AI Studio key for document category, query understanding, and answers |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Free-tier Gemini model for those steps |
| `CATEGORY_MIN_SCORE` | `0.35` | Minimum cosine score to keep category-scoped search results |

`all-MiniLM-L6-v2` produces 384-dimensional vectors. If you change the model, set `EMBEDDING_DIMENSION` to match, drop the `document_chunks` table, and start the app again so the column is recreated. `create_all` does not alter an existing vector column.

The database password in `.env.example` is for local use. Change it before exposing Postgres.

Before production, see [docs/PRODUCTION-CHECKLIST.md](docs/PRODUCTION-CHECKLIST.md). Optional dependency scan: `pip install pip-audit && pip-audit -r requirements.txt`.

## Tests

Unit tests do not need Postgres or the embedding model:

```bash
pytest
```

The integration test uploads a TXT file and a PDF, searches with the real model, and deletes the documents. It also clears any documents already in the configured database.

```bash
docker compose up db -d
INTEGRATION=1 pytest -m integration
```

## Processing path

1. Validate the extension, content type, and size, reject duplicate file bytes for the same user, then save the document as `processing`.
2. A background thread extracts text with PyMuPDF, or decodes TXT as UTF-8.
3. Clean whitespace and split the text into word-aligned chunks. Each chunk keeps its document id and a zero-based index.
4. Assign one category with Gemini from a fixed list: HR, Legal, Finance, Technical, Policy, General. Without a key or on failure, the category is General.
5. Encode every chunk with MiniLM. Vectors are normalized, and search uses pgvector cosine distance.
6. Save the chunks and mark the document `ready`. A processing error marks it `failed` instead. Deleting a document deletes its chunks.

A chunk stays within `CHUNK_SIZE` unless one word is longer than that limit. Overlap copies a short tail from the previous chunk when that tail still fits.
