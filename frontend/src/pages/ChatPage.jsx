import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getToken, jsonRequest } from "../api.js";
import { useChat } from "../context/ChatContext.jsx";

function newId() {
  return `m-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export default function ChatPage() {
  const token = getToken();
  const navigate = useNavigate();
  const { sessionId: sessionIdParam } = useParams();
  const bottomRef = useRef(null);

  const {
    sessions,
    currentSessionId,
    currentSession,
    setCurrentSessionId,
    setSessionMessages,
  } = useChat();

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // URL ↔ active session
  useEffect(() => {
    if (!sessionIdParam && currentSessionId) {
      navigate(`/chat/${currentSessionId}`, { replace: true });
      return;
    }
    const exists = sessions.some((s) => s.id === sessionIdParam);
    if (exists && sessionIdParam !== currentSessionId) {
      setCurrentSessionId(sessionIdParam);
    } else if (!exists) {
      navigate(`/chat/${currentSessionId}`, { replace: true });
    }
  }, [sessionIdParam, currentSessionId, sessions, navigate, setCurrentSessionId]);

  const messages = currentSession?.messages ?? [];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, currentSessionId]);

  async function send() {
    const q = input.trim();
    if (!q || !token || loading || !currentSessionId) return;
    setInput("");
    const userMsg = { id: newId(), role: "user", text: q };
    setSessionMessages(currentSessionId, (prev) => [...prev, userMsg]);
    setLoading(true);
    try {
      const res = await jsonRequest("POST", "/search", {
        body: { query: q },
        token,
      });
      const answer = res.data?.answer ?? "No answer returned.";
      setSessionMessages(currentSessionId, (prev) => [
        ...prev,
        { id: newId(), role: "assistant", text: String(answer) },
      ]);
    } catch (err) {
      const text = err instanceof Error ? err.message : "Search failed.";
      setSessionMessages(currentSessionId, (prev) => [
        ...prev,
        { id: newId(), role: "assistant", text: text },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-messages">
        {messages.length === 0 && !loading ? (
          <div className="chat-empty">
            <p className="chat-greeting">How can I help you today?</p>
            <p className="chat-sub">Ask anything about your uploaded documents.</p>
          </div>
        ) : (
          messages.map((m) =>
            m.role === "user" ? (
              <div key={m.id} className="chat-row user">
                <div className="chat-bubble user">{m.text}</div>
              </div>
            ) : (
              <div key={m.id} className="chat-row assistant">
                <div className="chat-bubble assistant">{m.text}</div>
              </div>
            )
          )
        )}
        {loading ? (
          <div className="chat-row assistant">
            <div className="chat-bubble assistant muted">Thinking…</div>
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>
      <p className="chat-privacy muted">
        Questions and document excerpts are sent to Google Gemini when configured on the server, only to answer from your
        uploads.
      </p>
      <div className="chat-composer-wrap">
        <div className="chat-composer">
          <textarea
            className="chat-input"
            rows={1}
            placeholder="Message…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={!token || loading}
          />
          <button
            type="button"
            className="chat-send"
            onClick={() => void send()}
            disabled={!token || loading || !input.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
