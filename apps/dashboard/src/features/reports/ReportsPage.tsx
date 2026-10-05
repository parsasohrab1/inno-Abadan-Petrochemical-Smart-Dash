import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../lib/api";

const KIND_FA: Record<string, string> = {
  daily: "Daily", weekly: "Weekly", monthly: "Monthly",
  cost_benefit: "Cost-benefit", ai_performance: "AI performance",
};

export function ReportsPage() {
  const [kind, setKind] = useState("");
  const { data } = useQuery({
    queryKey: ["reports", kind],
    queryFn: () => api.get("/api/reports", { params: kind ? { kind } : {} }).then((r) => r.data),
  });

  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 10 }}>
        <h3 style={{ margin: 0 }}>Analytical reports</h3>
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">All</option>
          {Object.entries(KIND_FA).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>
      <table>
        <thead>
          <tr><th>Date</th><th>Type</th><th>Title</th><th>Summary</th></tr>
        </thead>
        <tbody>
          {(data ?? []).map((r: any) => (
            <tr key={r.id}>
              <td>{new Date(r.created_at).toLocaleString("fa-IR")}</td>
              <td>{KIND_FA[r.kind] ?? r.kind}</td>
              <td>{r.title}</td>
              <td className="muted">{r.summary}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {(data ?? []).length === 0 && (
        <div className="muted" style={{ marginTop: 10 }}>
          No report has been generated yet. The scheduler automatically creates daily/weekly/monthly reports,
          or via the API: <code>POST /reports/generate?kind=daily</code>
        </div>
      )}
    </div>
  );
}
