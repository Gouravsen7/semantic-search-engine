import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { jsonRequest, setToken } from "../api.js";

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const res = await jsonRequest("POST", "/auth/login", {
        body: { email: email.trim(), password },
      });
      const token = res.data?.access_token;
      if (!token) {
        throw new Error("No access token returned.");
      }
      setToken(token);
      navigate("/chat", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    }
  }

  return (
    <div className="page page-auth">
      <div className="card card-narrow">
        <h1>Log in</h1>
        <p className="muted">Use the same account as in Postman.</p>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label className="label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              className="input"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              className="input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          {error ? <p className="error">{error}</p> : null}
          <button type="submit" className="btn-primary" style={{ width: "100%" }}>
            Log in
          </button>
        </form>
        <p className="muted" style={{ marginTop: "1rem" }}>
          Need an account?{" "}
          <Link to="/register">Create one</Link>
        </p>
      </div>
    </div>
  );
}
