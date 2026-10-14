import { Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./api.js";
import MainLayout from "./layout/MainLayout.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import DocumentsLayout from "./pages/DocumentsLayout.jsx";
import DocumentListPage from "./pages/DocumentListPage.jsx";
import DocumentUploadPage from "./pages/DocumentUploadPage.jsx";
import DocumentDetailPage from "./pages/DocumentDetailPage.jsx";
import { ChatProvider } from "./context/ChatContext.jsx";

function ProtectedRoute({ children }) {
  const token = getToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  const token = getToken();
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <ChatProvider>
              <MainLayout />
            </ChatProvider>
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat/:sessionId?" element={<ChatPage />} />
        <Route path="documents" element={<DocumentsLayout />}>
          <Route index element={<DocumentListPage />} />
          <Route path="upload" element={<DocumentUploadPage />} />
          <Route path="view/:documentId" element={<DocumentDetailPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to={token ? "/chat" : "/login"} replace />} />
    </Routes>
  );
}
