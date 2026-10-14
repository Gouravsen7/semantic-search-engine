import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deleteRequest, getToken, jsonRequest } from "../api.js";

export default function DocumentListPage() {
  const token = getToken();
  const [docs, setDocs] = useState(/** @type {any[]} */ ([]));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res = await jsonRequest("GET", "/documents", { token });
      setDocs(res.data?.documents ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleDelete(id) {
    if (!token || !window.confirm("Delete this document?")) return;
    try {
      await deleteRequest(`/documents/${id}`, token);
      await load();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed.");
    }
  }

  return (
    <div>
      <div className="docs-toolbar">
        <h1 className="docs-title">Your documents</h1>
        <div className="docs-toolbar-actions">
          <Link to="/documents/upload" className="btn-primary btn-primary-link">
            Upload document
          </Link>
          <button type="button" className="btn-ghost-dark" onClick={() => void load()} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {docs.length === 0 && !loading ? (
        <p className="muted">No documents yet. Use Upload document to add files.</p>
      ) : (
        <div className="table-wrap">
          <table className="table-dark">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Status</th>
                <th>Category</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>
                    <Link to={`/documents/view/${d.id}`} className="link-doc">
                      {d.filename}
                    </Link>
                  </td>
                  <td>{d.status}</td>
                  <td>{d.category ?? "—"}</td>
                  <td>
                    <button type="button" className="btn-ghost-dark" onClick={() => handleDelete(d.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
