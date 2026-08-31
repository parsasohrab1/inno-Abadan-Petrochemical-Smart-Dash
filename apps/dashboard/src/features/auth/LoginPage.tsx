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
      setError("نام کاربری یا گذرواژه نادرست است");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <h3>ورود به داشبرد CBM پتروشیمی آبادان</h3>
        <div className="grid" style={{ gap: 10 }}>
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="نام کاربری" />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="گذرواژه"
          />
          {error && <div style={{ color: "var(--red)", fontSize: 13 }}>{error}</div>}
          <button className="primary" disabled={busy}>{busy ? "..." : "ورود"}</button>
          <div className="muted">
            کاربران نمونه: manager / engineer / operator / viewer (گذرواژه: نام‌کاربری + 123)
          </div>
        </div>
      </form>
    </div>
  );
}
