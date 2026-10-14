import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { clearToken, getToken, jsonRequest } from "../api.js";
import { useTheme } from "../context/ThemeContext.jsx";
import { clearChatStorage, useChat } from "../context/ChatContext.jsx";

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const token = getToken();
  const [email, setEmail] = useState("");
  const { theme, toggleTheme } = useTheme();
  const { sessions, currentSessionId, setCurrentSessionId, createNewChat } = useChat();

  useEffect(() => {
    if (!token) return;
    jsonRequest("GET", "/auth/me", { token })
      .then((res) => setEmail(res.data?.email ?? ""))
      .catch(() => setEmail(""));
  }, [token]);

  function logout() {
    clearToken();
    clearChatStorage();
    navigate("/login", { replace: true });
  }

  function handleNewChat() {
    const id = createNewChat();
    navigate(`/chat/${id}`);
  }

  function openSession(id) {
    setCurrentSessionId(id);
    navigate(`/chat/${id}`);
  }

  const sessionMatch = location.pathname.match(/^\/chat\/([^/]+)/);
  const activeSessionFromUrl = sessionMatch ? sessionMatch[1] : null;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">Semantic Search</div>
        <nav className="sidebar-nav">
          <button type="button" className="sidebar-new-chat" onClick={handleNewChat}>
            + New chat
          </button>
          <div className="sidebar-section-label">Recents</div>
          <ul className="sidebar-history">
            {sessions.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  className={`sidebar-history-item${
                    (activeSessionFromUrl === s.id ||
                      (!activeSessionFromUrl && location.pathname === "/chat" && s.id === currentSessionId))
                      ? " active"
                      : ""
                  }`}
                  onClick={() => openSession(s.id)}
                  title={s.title}
                >
                  {s.title}
                </button>
              </li>
            ))}
          </ul>
          <NavLink
            to="/documents"
            end
            className={({ isActive }) => (isActive ? "sidebar-link active" : "sidebar-link")}
          >
            Documents
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          <span className="sidebar-email">{email || "…"}</span>
          <button type="button" className="btn-sidebar-ghost" onClick={logout}>
            Log out
          </button>
        </div>
      </aside>
      <main className="main-panel">
        <div className="main-toolbar">
          <span className="grow" />
          <button
            type="button"
            className="btn-theme-toggle"
            onClick={toggleTheme}
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
        </div>
        <div className="main-panel-body">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
