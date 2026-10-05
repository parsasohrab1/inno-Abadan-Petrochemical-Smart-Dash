import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";

function rulBadge(h: number) {
  if (h < 72) return "red";
  if (h < 24 * 14) return "yellow";
  return "green";
}

export function PredictionPage() {
  const { data } = useQuery({
    queryKey: ["predictions"],
    queryFn: () => api.get("/api/predictions").then((r) => r.data),
  });

  return (
    <div className="card">
      <h3>Failure prediction — equipment RUL (sorted by urgency)</h3>
      <div className="muted" style={{ marginBottom: 10 }}>
        A predictive alert is issued at least 72 hours before failure (FR-12).
      </div>
      <table>
        <thead>
          <tr>
            <th>Tag</th><th>Name</th><th>Criticality</th>
            <th>RUL (hours)</th><th>Estimated failure date</th><th>Confidence</th><th>Health index</th>
          </tr>
        </thead>
        <tbody>
          {(data ?? []).map((p: any) => (
            <tr key={p.tag}>
              <td><Link to={`/equipment/${p.tag}`}>{p.tag}</Link></td>
              <td>{p.name}</td>
              <td>{p.criticality}</td>
              <td>
                <span className={`badge ${rulBadge(p.predicted_rul_hours)}`}>
                  {Math.round(p.predicted_rul_hours).toLocaleString("fa-IR")}
                </span>
              </td>
              <td>{p.predicted_failure_at ? new Date(p.predicted_failure_at).toLocaleDateString("fa-IR") : "—"}</td>
              <td>{(p.confidence * 100).toFixed(0)}%</td>
              <td>{p.health_score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
