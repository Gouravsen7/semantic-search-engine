# Phase 3 — Search

Goal: one screen that calls **`POST /search`** with the same JSON as Postman and shows the answer plus hit list. **Back** returns to the Phase 2 upload/documents screen.

## API

**`POST /search`**

Headers: `Authorization: Bearer <token>`, `Content-Type: application/json`

Body:

```json
{
  "query": "your question in natural language",
  "top_k": 5
}
```

`top_k` is optional (server default from [README.md](../../README.md)).

### Response `data` fields to show

| Field | Note |
| ----- | ---- |
| `answer` | Plain-language answer |
| `query` | Echo of the user query (trimmed by API) |
| `interpreted_query` | Rewritten search phrase |
| `category` | Category scope used for search, or **`null`** if search ran across all documents |
| `top_k` | Number of chunks requested |
| `results` | Array of hits: `filename`, `score`, `content`, `document_id`, `chunk_index`, etc. |

If there are no hits, `message` may say no matches and **`answer`** still explains nothing was found.

## UI (minimal)

1. **← Back** link → Phase 2 route (no API).
2. Single-line or multi-line **Question** input (required).
3. Optional number input **top_k** (1–20, aligned with API max).
4. **Search** button → `POST /search`.
5. After response:
   - Show **`answer`** in a clear block.
   - Show **`interpreted_query`** and **`category`** as small read-only lines (or labels).
   - Table or list of **`results`**: **filename**, **score**, first lines of **content**.

## Errors

- **401**: token missing/expired — send user to login (Phase 1).
- **422**: validation — show `message` from JSON.
- Other: show `message`.

## Out of scope

- No chat history, no saved searches, no export — only this one request/response view.
