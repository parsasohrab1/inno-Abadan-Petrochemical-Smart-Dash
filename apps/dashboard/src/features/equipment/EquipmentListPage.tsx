import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { api } from "../../lib/api";
import { Badge, Color } from "../../components/common";

export function EquipmentListPage() {
  const [q, setQ] = useState("");
  const { data } = useQuery({
    queryKey: ["heatmap"],
    queryFn: () => api.get("/api/heatmap").then((r) => r.data),
  });

  const rows = (data ?? []).filter(
    (e: any) =>
      e.tag.toLowerCase().includes(q.toLowerCase()) ||
      e.name.toLowerCase().includes(q.toLowerCase()) ||
      e.unit.includes(q),
  );

  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Equipment ({rows.length})</h3>
        <input placeholder="Search by tag / name / unit" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <table>
        <thead>
          <tr>
            <th>Tag</th><th>Name</th><th>Type</th><th>Unit/Line</th>
            <th>Health index</th><th>Status</th><th>Run state</th><th>Spare</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((e: any) => (
            <tr key={e.tag}>
              <td><Link to={`/equipment/${e.tag}`}>{e.tag}</Link></td>
              <td>{e.name}</td>
              <td>{e.type}</td>
              <td>{e.unit}/{e.line}</td>
              <td>{e.health_score}</td>
              <td><Badge color={e.color as Color}>{e.color}</Badge></td>
              <td>{e.run_state}</td>
              <td>{e.has_spare ? "Yes" : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
