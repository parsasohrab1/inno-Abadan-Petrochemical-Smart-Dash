import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../lib/api";

const KIND_FA: Record<string, string> = {
  daily: "روزانه", weekly: "هفتگی", monthly: "ماهانه",
  cost_benefit: "هزینه-فایده", ai_performance: "عملکرد AI",
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
        <h3 style={{ margin: 0 }}>گزارش‌های تحلیلی</h3>
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">همه</option>
          {Object.entries(KIND_FA).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>
      <table>
        <thead>
          <tr><th>تاریخ</th><th>نوع</th><th>عنوان</th><th>خلاصه</th></tr>
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
          هنوز گزارشی تولید نشده. زمان‌بند به‌صورت خودکار گزارش روزانه/هفتگی/ماهانه می‌سازد،
          یا از API: <code>POST /reports/generate?kind=daily</code>
        </div>
      )}
    </div>
  );
}
