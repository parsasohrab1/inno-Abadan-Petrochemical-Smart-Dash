import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../lib/api";
import { HealthDot, Color, StatCard } from "../../components/common";

export function SensorHealthPage() {
  const [color, setColor] = useState("");
  const { data } = useQuery({
    queryKey: ["sensor-health", color],
    queryFn: () =>
      api.get("/api/sensor-health", { params: color ? { color } : {} }).then((r) => r.data),
  });

  const s = data?.summary;

  return (
    <div className="grid" style={{ gap: 14 }}>
      <div className="grid cols-3">
        <StatCard title="سنسورهای سالم" value={<span><HealthDot color="green" /> {s?.green ?? "…"}</span>} />
        <StatCard title="نیازمند بررسی/کالیبراسیون" value={<span><HealthDot color="yellow" /> {s?.yellow ?? "…"}</span>} />
        <StatCard title="خراب / داده‌ی نامعتبر" value={<span><HealthDot color="red" /> {s?.red ?? "…"}</span>} />
      </div>

      <div className="card">
        <div className="row" style={{ marginBottom: 10 }}>
          <h3 style={{ margin: 0 }}>پایش سه‌چراغِ سنسورها و دوربین‌ها</h3>
          <select value={color} onChange={(e) => setColor(e.target.value)}>
            <option value="">همه</option>
            <option value="green">سبز</option>
            <option value="yellow">زرد</option>
            <option value="red">قرمز</option>
          </select>
        </div>
        <table>
          <thead>
            <tr><th>تگ</th><th>نوع</th><th>واحد اندازه‌گیری</th><th>محدوده</th><th>وضعیت</th></tr>
          </thead>
          <tbody>
            {(data?.sensors ?? []).slice(0, 400).map((x: any) => (
              <tr key={x.tag}>
                <td>{x.tag}</td>
                <td>{x.kind}</td>
                <td><b>{x.unit}</b></td>
                <td className="muted">{x.range?.[0]} … {x.range?.[1]} {x.unit}</td>
                <td><HealthDot color={x.status as Color} label /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>دوربین‌ها ({data?.cameras?.length ?? 0})</h3>
        <table>
          <thead>
            <tr><th>تگ</th><th>نوع</th><th>واحد اندازه‌گیری</th><th>وضعیت</th></tr>
          </thead>
          <tbody>
            {(data?.cameras ?? []).map((c: any) => (
              <tr key={c.tag}>
                <td>{c.tag}</td>
                <td>{c.kind}</td>
                <td><b>{c.unit}</b></td>
                <td><HealthDot color={c.status as Color} label /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
