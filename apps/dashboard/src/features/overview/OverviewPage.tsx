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
          title="تجهیزات"
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
          title="وضعیت کارکرد"
          value={o ? `${o.equipment.running} در حال کار` : "…"}
          sub={o && `${o.equipment.standby} زاپاس · ${o.equipment.stopped} متوقف`}
        />
        <StatCard
          title="سنسورها"
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
          title="هشدارهای فعال"
          value={o?.alerts.active ?? "…"}
          sub={o && `${o.alerts.critical} بحرانی · ${o.alerts.predictive} پیش‌بینی`}
        />
      </div>

      <div className="card">
        <h3>نقشه‌ی حرارتی وضعیت تجهیزات مجتمع (کلیک برای جزئیات)</h3>
        {(heat.data ?? []).length === 0 && <div className="muted">در حال بارگذاری…</div>}
        <div className="heatmap">
          {(heat.data ?? []).map((e: any) => (
            <div
              key={e.tag}
              className={`heat-cell ${e.color} ${e.has_spare ? "spare" : ""}`}
              title={`${e.name} — ${e.unit}/${e.line} — شاخص سلامت ${e.health_score} — ${e.run_state}`}
              onClick={() => nav(`/equipment/${e.tag}`)}
            >
              <b>{e.tag.split("-").slice(-2).join("-")}</b>
              <span>{e.health_score}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3>واحدهای تولیدی</h3>
        <table>
          <thead>
            <tr><th>کد واحد</th><th>عنوان</th><th>بحرانیت</th></tr>
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
