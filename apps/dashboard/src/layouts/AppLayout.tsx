import { NavLink, Outlet } from "react-router-dom";
import { EconomicsBar } from "../components/EconomicsBar";
import { useLiveFeed } from "../lib/useLiveFeed";
import { logout } from "../lib/api";

const NAV = [
  ["/overview", "Complex overview"],
  ["/equipment", "Equipment"],
  ["/alerts", "Alerts"],
  ["/prediction", "Failure prediction (RUL)"],
  ["/auto-operation", "Smart operator"],
  ["/sensor-health", "Sensor and camera health"],
  ["/reports", "Reports"],
];

export function AppLayout() {
  const { connected } = useLiveFeed();
  const name = localStorage.getItem("cbm_name") || localStorage.getItem("cbm_role");

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>CBM Smart Dashboard<br />Abadan Petrochemical</h1>
        <nav className="nav">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : "")}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div style={{ marginTop: "auto" }}>
          <div className={`ws-status ${connected ? "on" : "off"}`}>
            {connected ? "● Live stream connected" : "○ Live connection lost"}
          </div>
          <div className="muted" style={{ margin: "8px 0" }}>{name}</div>
          <button onClick={logout}>Log out</button>
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
