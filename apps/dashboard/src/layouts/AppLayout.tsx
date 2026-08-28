import { NavLink, Outlet } from "react-router-dom";
import { EconomicsBar } from "../components/EconomicsBar";
import { useLiveFeed } from "../lib/useLiveFeed";
import { logout } from "../lib/api";

const NAV = [
  ["/overview", "نمای کلی مجتمع"],
  ["/equipment", "تجهیزات"],
  ["/alerts", "هشدارها"],
  ["/prediction", "پیش‌بینی خرابی (RUL)"],
  ["/auto-operation", "اوپراتور هوشمند"],
  ["/sensor-health", "سلامت سنسور و دوربین"],
  ["/reports", "گزارش‌ها"],
];

export function AppLayout() {
  const { connected } = useLiveFeed();
  const name = localStorage.getItem("cbm_name") || localStorage.getItem("cbm_role");

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>داشبرد هوشمند CBM<br />پتروشیمی آبادان</h1>
        <nav className="nav">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : "")}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div style={{ marginTop: "auto" }}>
          <div className={`ws-status ${connected ? "on" : "off"}`}>
            {connected ? "● جریان زنده متصل" : "○ قطع ارتباط زنده"}
          </div>
          <div className="muted" style={{ margin: "8px 0" }}>{name}</div>
          <button onClick={logout}>خروج</button>
        </div>
      </aside>
      <main className="main">
        <div className="topbar">
          <EconomicsBar />
        </div>
        <Outlet />
      </main>
    </div>
  );
}
