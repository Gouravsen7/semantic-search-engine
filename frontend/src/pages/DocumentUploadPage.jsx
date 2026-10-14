import { useEffect, useRef, useState } from "react";
import { formRequest, getToken, jsonRequest } from "../api.js";

let clientIdSeq = 0;
function nextClientId() {
  clientIdSeq += 1;
  return `up-${clientIdSeq}`;
}

const POLL_MS = 2500;
const MAX_POLLS = 240; // 10 minutes

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function statusClass(status) {
  if (status === "queued") return "status-queued";
  if (status === "uploading") return "status-uploading";
  if (status === "processing") return "status-processing";
  if (status === "ready") return "status-ready";
  if (status === "failed") return "status-failed";
  return "status-queued";
}

function statusIcon(status) {
  if (status === "ready") return "✓";
  if (status === "failed") return "✕";
  if (status === "uploading" || status === "processing") return "◌";
  return "—";
}

export default function DocumentUploadPage() {
  const token = getToken();
  const inputRef = useRef(null);
  const workerLock = useRef(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const [filter, setFilter] = useState("");
  const [dragOver, setDragOver] = useState(false);

  /**
   * @typedef {{ clientId: string, file: File, name: string, status: string, documentId?: string, error?: string }} QueueItem
   */
  const [queue, setQueue] = useState(/** @type {QueueItem[]} */ ([]));

  /** @type {import("react").CSSProperties} */
  const dropzoneStyle = { cursor: "pointer" };

  useEffect(() => {
    if (!token || workerLock.current) {
      return;
    }
    const next = queue.find((q) => q.status === "queued");
    if (!next) {
      return;
    }

    workerLock.current = true;
    const { clientId, file } = next;

    void (async () => {
      try {
        setQueue((prev) =>
          prev.map((q) => (q.clientId === clientId ? { ...q, status: "uploading", error: undefined } : q))
        );

        const body = new FormData();
        body.append("file", file);
        const res = await formRequest("/documents", body, token);
        const documentId = res.data?.id;
        if (!documentId) {
          throw new Error("No document id returned.");
        }

        setQueue((prev) =>
          prev.map((q) =>
            q.clientId === clientId ? { ...q, status: "processing", documentId: String(documentId) } : q
          )
        );

        let finished = false;
        for (let polls = 0; polls < MAX_POLLS; polls += 1) {
          await sleep(POLL_MS);
          if (!mountedRef.current) {
            break;
          }
          const detail = await jsonRequest("GET", `/documents/${documentId}`, { token });
          const status = detail.data?.status;
          if (status === "ready") {
            setQueue((prev) =>
              prev.map((q) => (q.clientId === clientId ? { ...q, status: "ready" } : q))
            );
            finished = true;
            break;
          }
          if (status === "failed") {
            const msg = detail.data?.error_message || "Processing failed.";
            setQueue((prev) =>
              prev.map((q) =>
                q.clientId === clientId ? { ...q, status: "failed", error: msg } : q
              )
            );
            finished = true;
            break;
          }
        }
        if (!finished && mountedRef.current) {
          setQueue((prev) =>
            prev.map((q) =>
              q.clientId === clientId && q.status === "processing"
                ? {
                    ...q,
                    status: "failed",
                    error: "Processing timed out. Refresh the document list or upload again.",
                  }
                : q
            )
          );
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Upload failed.";
        setQueue((prev) =>
          prev.map((q) =>
            q.clientId === clientId ? { ...q, status: "failed", error: msg } : q
          )
        );
      } finally {
        workerLock.current = false;
      }
    })();
  }, [token, queue]);

  function addFiles(fileList) {
    const accepted = [...fileList].filter(
      (f) => f.name.toLowerCase().endsWith(".pdf") || f.name.toLowerCase().endsWith(".txt")
    );
    if (accepted.length === 0) return;
    setQueue((prev) => [
      ...prev,
      ...accepted.map((file) => ({
        clientId: nextClientId(),
        file,
        name: file.name,
        status: "queued",
      })),
    ]);
  }

  function cancelQueued(clientId) {
    setQueue((prev) => prev.filter((q) => !(q.clientId === clientId && q.status === "queued")));
  }

  const filteredQueue = queue.filter((q) =>
    q.name.toLowerCase().includes(filter.trim().toLowerCase())
  );

  return (
    <div>
      <h1 className="docs-title">Upload</h1>
      <p className="muted" style={{ marginBottom: "1.25rem" }}>
        PDF or TXT only. Duplicates (same file bytes) are rejected while an earlier copy is processing or ready.
      </p>

      <div className="upload-grid-dark">
        <div>
          <h2 className="docs-h2">Drop zone</h2>
          <div
            className={`dropzone-dark${dragOver ? " dragover" : ""}`}
            style={dropzoneStyle}
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                inputRef.current?.click();
              }
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              addFiles(e.dataTransfer.files);
            }}
          >
            <div className="dropzone-icon">📁</div>
            <div>Drag your files here</div>
            <div className="muted">Or</div>
            <button
              type="button"
              className="btn-ghost-dark"
              onClick={(e) => {
                e.stopPropagation();
                inputRef.current?.click();
              }}
            >
              Browse your Computer
            </button>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.txt"
            multiple
            hidden
            onChange={(e) => {
              if (e.target.files) {
                addFiles(e.target.files);
                e.target.value = "";
              }
            }}
          />
        </div>

        <div>
          <h2 className="docs-h2">Upload progress</h2>
          <input
            type="search"
            className="input-dark"
            placeholder="Filter this queue"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ marginBottom: "0.75rem" }}
          />
          {filteredQueue.length === 0 ? (
            <p className="muted">No files in the queue.</p>
          ) : (
            <ul className="progress-list">
              {filteredQueue.map((q) => (
                <li key={q.clientId} className="progress-item progress-item-dark">
                  <span>{q.name}</span>
                  <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span className={statusClass(q.status)}>
                      {statusIcon(q.status)} {q.status}
                    </span>
                    {q.error ? (
                      <span className="status-failed" title={q.error}>
                        ({q.error.length > 50 ? `${q.error.slice(0, 50)}…` : q.error})
                      </span>
                    ) : null}
                    {q.status === "queued" ? (
                      <button type="button" className="btn-ghost-dark" onClick={() => cancelQueued(q.clientId)}>
                        Cancel
                      </button>
                    ) : null}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
