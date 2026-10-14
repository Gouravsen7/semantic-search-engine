import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { jsonRequest, setToken } from "../api.js";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const res = await jsonRequest("POST", "/auth/register", {
        body: { email: email.trim(), password },
      });
      const token = res.data?.access_token;
      if (!token) {
        throw new Error("No access token returned.");
      }
      setToken(token);
      navigate("/chat", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    }
  }

  return (
    <div className="page page-auth">
      <div className="card card-narrow">
        <h1>Create account</h1>
        <p className="muted">Password must be at least 8 characters.</p>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label className="label" htmlFor="reg-email">
              Email
            </label>
            <input
              id="reg-email"
              className="input"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="reg-password">
              Password
            </label>
            <input
              id="reg-password"
              className="input"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          {error ? <p className="error">{error}</p> : null}
          <button type="submit" className="btn-primary" style={{ width: "100%" }}>
            Register
          </button>
        </form>
        <p className="muted" style={{ marginTop: "1rem" }}>
          Already have an account?{" "}
          <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
