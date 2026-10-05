import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../../lib/api";

export function LoginPage() {
  const nav = useNavigate();
  const [username, setUsername] = useState("manager");
  const [password, setPassword] = useState("manager123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username, password);
      nav("/overview");
    } catch {
      setError("Username or password is incorrect");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <h3>Sign in to the Abadan Petrochemical CBM Dashboard</h3>
        <div className="grid" style={{ gap: 10 }}>
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
          />
          {error && <div style={{ color: "var(--red)", fontSize: 13 }}>{error}</div>}
          <button className="primary" disabled={busy}>{busy ? "..." : "Sign in"}</button>
          <div className="muted">
            Sample users: manager / engineer / operator / viewer (password: username + 123)
          </div>
        </div>
      </form>
    </div>
  );
}
