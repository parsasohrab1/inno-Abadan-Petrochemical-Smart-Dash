import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { StatCard } from "../../components/common";

export function OverviewPage() {
  const nav = useNavigate();
  const overview = useQuery({
    queryKey: ["overview"],
    queryFn: () => api.get("/api/overview").then((r) => r.data),
  });
  const heat = useQuery({
    queryKey: ["heatmap"],
    queryFn: () => api.get("/api/heatmap").then((r) => r.data),
  });

  const o = overview.data;

  return (
    <div className="grid" style={{ gap: 18 }}>
      <div className="grid cols-4">
        <StatCard
          title="Equipment"
          value={o?.equipment.total ?? "…"}
          sub={
            o && (
              <>
                <span className="dot green" />{o.equipment.by_color.green}{" "}
                <span className="dot yellow" />{o.equipment.by_color.yellow}{" "}
                <span className="dot red" />{o.equipment.by_color.red}
              </>
            )
          }
        />
        <StatCard
          title="Run state"
          value={o ? `${o.equipment.running} running` : "…"}
          sub={o && `${o.equipment.standby} standby · ${o.equipment.stopped} stopped`}
        />
        <StatCard
          title="Sensors"
          value={o?.sensors.total ?? "…"}
          sub={
            o && (
              <>
                <span className="dot green" />{o.sensors.by_color.green}{" "}
                <span className="dot yellow" />{o.sensors.by_color.yellow}{" "}
                <span className="dot red" />{o.sensors.by_color.red}
              </>
            )
          }
        />
        <StatCard
          title="Active alerts"
          value={o?.alerts.active ?? "…"}
          sub={o && `${o.alerts.critical} critical · ${o.alerts.predictive} predictive`}
        />
      </div>

      <div className="card">
        <h3>Heat map of the complex equipment status (click for details)</h3>
        {(heat.data ?? []).length === 0 && <div className="muted">Loading…</div>}
        <div className="heatmap">
          {(heat.data ?? []).map((e: any) => (
            <div
              key={e.tag}
              className={`heat-cell ${e.color} ${e.has_spare ? "spare" : ""}`}
              title={`${e.name} — ${e.unit}/${e.line} — health index ${e.health_score} — ${e.run_state}`}
              onClick={() => nav(`/equipment/${e.tag}`)}
            >
              <b>{e.tag.split("-").slice(-2).join("-")}</b>
              <span>{e.health_score}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3>Production units</h3>
        <table>
          <thead>
            <tr><th>Unit code</th><th>Title</th><th>Criticality</th></tr>
          </thead>
          <tbody>
            {(o?.units ?? []).map((u: any) => (
              <tr key={u.code}><td>{u.code}</td><td>{u.title}</td><td>{u.criticality}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
