import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getToken, jsonRequest } from "../api.js";

export default function DocumentDetailPage() {
  const { documentId } = useParams();
  const token = getToken();
  const [detail, setDetail] = useState(/** @type {any | null} */ (null));
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!token || !documentId) return;
    setError("");
    try {
      const res = await jsonRequest("GET", `/documents/${documentId}`, { token });
      setDetail(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load document.");
    }
  }, [token, documentId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!token || !documentId || !detail) return;
    if (detail.status !== "processing") return;
    const t = window.setInterval(() => void load(), 2500);
    return () => window.clearInterval(t);
  }, [token, documentId, detail?.status, load]);

  if (!documentId) {
    return <p className="error">Missing document id.</p>;
  }

  if (error) {
    return (
      <div>
        <p className="error">{error}</p>
        <Link to="/documents" className="link-doc">
          ← Back to listing
        </Link>
      </div>
    );
  }

  if (!detail) {
    return <p className="muted">Loading…</p>;
  }

  return (
    <div>
      <div className="docs-toolbar">
        <h1 className="docs-title">{detail.filename}</h1>
        <Link to="/documents" className="link-doc">
          ← Listing
        </Link>
      </div>
      <p className="muted">
        Status: <strong>{detail.status}</strong>
        {detail.category != null ? (
          <>
            {" "}
            · Category: <strong>{detail.category}</strong>
          </>
        ) : null}
        {detail.error_message ? (
          <>
            <br />
            <span className="error">{detail.error_message}</span>
          </>
        ) : null}
      </p>

      <h2 className="docs-h2">Chunks</h2>
      {detail.status === "processing" ? (
        <p className="muted">Processing… chunks will appear when ready.</p>
      ) : null}
      {detail.chunks?.length ? (
        <ul className="chunk-list">
          {detail.chunks.map((c) => (
            <li key={c.id} className="chunk-item">
              <div className="chunk-meta">Chunk {c.chunk_index}</div>
              <pre className="chunk-text">{c.content}</pre>
            </li>
          ))}
        </ul>
      ) : null}
      {detail.status === "ready" && !detail.chunks?.length ? (
        <p className="muted">No chunks stored.</p>
      ) : null}
    </div>
  );
}
