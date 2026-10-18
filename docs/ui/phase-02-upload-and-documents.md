# Phase 2 — Upload and documents (match the mock)

Goal: one clean screen like your reference: **cream page background**, **centered white card**, **soft orange** primary actions. Left: **drag-and-drop** + **Browse**. Right: **Upload Progress** list with status icons. No new backend APIs — only what exists in [README.md](../../README.md).

## APIs used

| Action | Method | Path | Auth |
| ------ | ------ | ---- | ---- |
| Upload one file | `POST` | `/documents` | Bearer |
| List documents | `GET` | `/documents` | Bearer |
| Document detail (poll) | `GET` | `/documents/{document_id}` | Bearer |
| Delete document | `DELETE` | `/documents/{document_id}` | Bearer |

### Upload

- **`multipart/form-data`**, field name **`file`** (single PDF or TXT).
- Response: **`201`** with `data` containing document `id`, `status` (often **`processing`** initially), etc.
- Duplicate file bytes for the same user: **`409`** with `message` mentioning an existing filename.

### Poll until ready

Call **`GET /documents/{id}`** until **`data.status`** is **`ready`** or **`failed`**. If **`failed`**, show **`data.error_message`**.

### List

**`GET /documents`** returns `data.documents` (newest first) with metadata including **`category`** when **`ready`** (`null` while **`processing`**).

## Layout (two columns inside one card)

**Header row**

- Title: **Upload your Documents** (or similar).
- **← Go back** link: navigates to Phase 1 shell (e.g. “home” with email + logout) or previous route — no API call.

**Left column — drop zone**

- Dashed border box.
- Short text: **Drag your files here**.
- **Or**
- Button or link style: **Browse your Computer** → hidden `<input type="file" accept=".pdf,.txt">`.

**Right column — Upload Progress**

- Subtitle: **Upload Progress**.
- Small text field **Search all files**: filters only the **rows in this list** (client-side string match on filename). Does **not** call the server.
- Vertical list of items. Each row shows:
  - Filename
  - Status: **queued** → **uploading** → **processing** (polling) → **ready** / **failed**
  - **Cancel** (before `POST` starts): remove from queue, no request.
  - After upload started: optional **Cancel** can mean “stop polling” / remove row from UI only — the server job may still finish (keep it simple: disable cancel after upload starts, or only allow remove before upload).

**Footer**

- Primary button **Continue**: goes to the chat/search screen, or next route in your app.

## Client-side queue flow

1. User picks one or more files in the browser.
2. For each file, add a **queued** row.
3. Process **one file at a time** (simplest): send **`POST /documents`** with `FormData` and `file` attached.
4. On success, set row to **processing** with `document_id` from `data.id`.
5. **Poll `GET /documents/{document_id}`** every 2–3 seconds until **`ready`** or **`failed`**.
6. On **409** duplicate, show `message` and mark row **failed** (or skip).

## List + delete (minimal)

Add a small section below the card or a second simple view:

- Button **Refresh** → **`GET /documents`**, render table: filename, status, category, created_at.
- Per row **Delete** → **`DELETE /documents/{id}`**, then refresh list.

Optional: **View** opens a read-only panel using **`GET /documents/{id}`** to show chunk text (large — keep collapsed by default).

## Styling notes

- Keep spacing generous; rounded card; one orange accent for buttons and links.
- Do **not** add charts, notifications library, or extra features beyond upload progress, list, delete, and navigation.

## Checklist before Phase 3

- [ ] Upload works with Bearer token
- [ ] Status reaches **ready** after poll
- [ ] Duplicate upload shows **409** message
- [ ] **← Go back** and **Continue** routes work
- [ ] Search box only filters local upload rows
