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
          <h3>هشدارهای تازه‌رسیده</h3>
          {flash.map((a, i) => (
            <div key={i} className="row" style={{ padding: "4px 0" }}>
              <span className="dot red" /> {a.title} — <span className="muted">{a.description}</span>
            </div>
          ))}
        </div>
      )}
      <div className="card">
        <h3>هشدارهای فعال ({data?.length ?? 0})</h3>
        <table>
          <thead>
            <tr>
              <th>زمان</th><th>شدت</th><th>کد</th><th>عنوان</th>
              <th>تجهیز/دستگاه</th><th>نوع</th>
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
                <td>{a.is_predictive ? "پیش‌بینی" : "لحظه‌ای"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
