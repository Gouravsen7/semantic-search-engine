import { createContext, useCallback, useContext, useMemo, useState } from "react";

const LEGACY_MESSAGES_KEY = "semantic_chat_messages";

export const CHAT_SESSIONS_KEY = "semantic_chat_sessions";

/**
 * @typedef {{ id: string, role: 'user' | 'assistant', text: string }} ChatMsg
 */

/**
 * @typedef {{ id: string, title: string, createdAt: number, updatedAt: number, messages: ChatMsg[] }} ChatSession
 */

function newSessionId() {
  return `s-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/** Title from first user line in conversation */
export function titleFromFirstMessage(text) {
  const line = text.trim().split(/\r?\n/)[0] || "New chat";
  const shortened = line.length > 52 ? `${line.slice(0, 49)}…` : line;
  return shortened || "New chat";
}

function ensureTitle(messages, previousTitle) {
  const firstUser = messages.find((m) => m.role === "user" && typeof m.text === "string");
  if (!firstUser) {
    return previousTitle === "New chat" || !previousTitle ? "New chat" : previousTitle;
  }
  if (previousTitle === "New chat" || !previousTitle) {
    return titleFromFirstMessage(firstUser.text);
  }
  return previousTitle;
}

function loadInitialState() {
  try {
    const raw = sessionStorage.getItem(CHAT_SESSIONS_KEY);
    if (raw) {
      const data = JSON.parse(raw);
      if (
        data &&
        Array.isArray(data.sessions) &&
        data.sessions.length > 0 &&
        typeof data.currentSessionId === "string"
      ) {
        return data;
      }
    }
    const legacy = sessionStorage.getItem(LEGACY_MESSAGES_KEY);
    if (legacy) {
      const messages = JSON.parse(legacy);
      if (Array.isArray(messages) && messages.length > 0) {
        const sid = newSessionId();
        const now = Date.now();
        const migrated = {
          sessions: [
            {
              id: sid,
              title: ensureTitle(messages, "New chat"),
              createdAt: now,
              updatedAt: now,
              messages,
            },
          ],
          currentSessionId: sid,
        };
        sessionStorage.setItem(CHAT_SESSIONS_KEY, JSON.stringify(migrated));
        sessionStorage.removeItem(LEGACY_MESSAGES_KEY);
        return migrated;
      }
      sessionStorage.removeItem(LEGACY_MESSAGES_KEY);
    }
  } catch {
    /* ignore */
  }
  const sid = newSessionId();
  const now = Date.now();
  return {
    sessions: [{ id: sid, title: "New chat", createdAt: now, updatedAt: now, messages: [] }],
    currentSessionId: sid,
  };
}

function persistPayload(sessions, currentSessionId) {
  try {
    sessionStorage.setItem(CHAT_SESSIONS_KEY, JSON.stringify({ sessions, currentSessionId }));
  } catch {
    /* quota */
  }
}

const ChatContext = createContext(
  /** @type {{
   *   sessions: ChatSession[],
   *   currentSessionId: string,
   *   currentSession: ChatSession | undefined,
   *   setCurrentSessionId: (id: string) => void,
   *   createNewChat: () => string,
   *   setSessionMessages: (sessionId: string, action: ChatMsg[] | ((prev: ChatMsg[]) => ChatMsg[])) => void,
   * } | null} */ (null)
);

export function ChatProvider({ children }) {
  const init = loadInitialState();
  const [sessions, setSessions] = useState(/** @type {ChatSession[]} */ (init.sessions));
  const [currentSessionId, setCurrentSessionIdState] = useState(init.currentSessionId);

  const commit = useCallback((nextSessions, nextCurrentId) => {
    setSessions(nextSessions);
    setCurrentSessionIdState(nextCurrentId);
    persistPayload(nextSessions, nextCurrentId);
  }, []);

  const setCurrentSessionId = useCallback(
    (id) => {
      setCurrentSessionIdState(id);
      persistPayload(sessions, id);
    },
    [sessions]
  );

  const createNewChat = useCallback(() => {
    const now = Date.now();
    const id = newSessionId();
    const nextSessions = [{ id, title: "New chat", createdAt: now, updatedAt: now, messages: [] }, ...sessions];
    commit(nextSessions, id);
    return id;
  }, [sessions, commit]);

  /**
   * @param {string} sessionId
   * @param {ChatMsg[] | ((prev: ChatMsg[]) => ChatMsg[])} action
   */
  const setSessionMessages = useCallback(
    (sessionId, action) => {
      setSessions((prev) => {
        const next = prev.map((s) => {
          if (s.id !== sessionId) return s;
          const messages = typeof action === "function" ? action(s.messages) : action;
          const title = ensureTitle(messages, s.title);
          return {
            ...s,
            messages,
            title,
            updatedAt: Date.now(),
          };
        });
        persistPayload(next, currentSessionId);
        return next;
      });
    },
    [currentSessionId]
  );

  const currentSession = sessions.find((s) => s.id === currentSessionId);

  const sortedSessions = useMemo(
    () => [...sessions].sort((a, b) => b.updatedAt - a.updatedAt),
    [sessions]
  );

  const value = useMemo(
    () => ({
      sessions: sortedSessions,
      currentSessionId,
      currentSession,
      setCurrentSessionId,
      createNewChat,
      setSessionMessages,
    }),
    [
      sortedSessions,
      currentSessionId,
      currentSession,
      setCurrentSessionId,
      createNewChat,
      setSessionMessages,
    ]
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function clearChatStorage() {
  sessionStorage.removeItem(CHAT_SESSIONS_KEY);
  sessionStorage.removeItem(LEGACY_MESSAGES_KEY);
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error("useChat must be used within ChatProvider");
  }
  return ctx;
}
