import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { api } from "../../lib/api";
import { useLiveFeed } from "../../lib/useLiveFeed";

const SEV_COLOR: Record<string, string> = {
  info: "var(--muted)", warning: "var(--yellow)", major: "var(--red)", critical: "var(--red)",
};

export function AlertsPage() {
  const [flash, setFlash] = useState<any[]>([]);
  const { data, refetch } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api.get("/api/alerts").then((r) => r.data),
  });

  useLiveFeed((m) => {
    if (m.channel === "alert") {
      setFlash((f) => [m.data, ...f].slice(0, 5));
      refetch();
    }
  });

  return (
    <div className="grid" style={{ gap: 14 }}>
      {flash.length > 0 && (
        <div className="card" style={{ borderColor: "var(--red)" }}>
          <h3>Newly arrived alerts</h3>
          {flash.map((a, i) => (
            <div key={i} className="row" style={{ padding: "4px 0" }}>
              <span className="dot red" /> {a.title} — <span className="muted">{a.description}</span>
            </div>
          ))}
        </div>
      )}
      <div className="card">
        <h3>Active alerts ({data?.length ?? 0})</h3>
        <table>
          <thead>
            <tr>
              <th>Time</th><th>Severity</th><th>Code</th><th>Title</th>
              <th>Equipment/Device</th><th>Type</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((a: any) => (
              <tr key={a.id}>
                <td>{formatDistanceToNow(new Date(a.created_at))}</td>
                <td style={{ color: SEV_COLOR[a.severity] }}>{a.severity}</td>
                <td>{a.code}</td>
                <td>{a.title}</td>
                <td>{a.equipment_tag ?? a.device_tag ?? "—"}</td>
                <td>{a.is_predictive ? "Predictive" : "Real-time"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
