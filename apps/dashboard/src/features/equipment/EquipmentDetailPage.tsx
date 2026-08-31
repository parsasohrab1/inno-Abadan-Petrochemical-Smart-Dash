import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { api, currentRole } from "../../lib/api";
import { Badge, Color, StatCard } from "../../components/common";

function TrendChart({ title, series, unit }: { title: string; series: any[]; unit?: string }) {
  return (
    <div className="card">
      <h3>{title}{unit ? ` (${unit})` : ""}</h3>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={(series ?? []).map((d) => ({ ...d, t: d.ts?.slice(5, 16) }))}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3742" />
          <XAxis dataKey="t" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#58a6ff" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function EquipmentDetailPage() {
  const { tag = "" } = useParams();
  const qc = useQueryClient();
  const canControl = ["operator", "maintenance", "engineer", "manager", "admin"].includes(currentRole());

  const { data } = useQuery({
    queryKey: ["equipment", tag],
    queryFn: () => api.get(`/api/equipment/${tag}`).then((r) => r.data),
  });

  const control = useMutation({
    mutationFn: (action: "start" | "stop" | "changeover") =>
      api.post(`/api/auto-operation/control/${tag}/${action}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipment", tag] }),
  });

  const eq = data?.equipment;
  const diag = data?.diagnosis;
  const rul = data?.rul;
  const trends = data?.trends ?? {};

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2 style={{ margin: 0 }}>{tag} — {eq?.name}</h2>
        {eq && <Badge color={eq.health_color as Color}>{eq.health_color} · {eq.run_state}</Badge>}
      </div>

      <div className="grid cols-4">
        <StatCard title="شاخص سلامت" value={eq?.health_score ?? "…"} />
        <StatCard
          title="عیب تشخیص‌داده‌شده"
          value={diag?.fault_type ?? "—"}
          sub={diag && `شدت ${(diag.severity * 100).toFixed(0)}٪ · اعتماد ${(diag.confidence * 100).toFixed(0)}٪`}
        />
        <StatCard
          title="RUL (عمر باقی‌مانده)"
          value={rul ? `${Math.round(rul.predicted_rul_hours)} ساعت` : "…"}
          sub={rul && `اعتماد ${(rul.confidence * 100).toFixed(0)}٪`}
        />
        <StatCard title="بحرانیت" value={eq?.criticality ?? "…"} sub={eq?.manufacturer} />
      </div>

      {canControl && (
        <div className="card">
          <h3>کنترل تجهیز (Auto Operation)</h3>
          <div className="row">
            <button className="ok" onClick={() => control.mutate("start")}>روشن‌کردن</button>
            <button className="danger" onClick={() => control.mutate("stop")}>خاموش‌کردن</button>
            <button className="primary" disabled={!eq?.has_spare} onClick={() => control.mutate("changeover")}>
              تعویض به زاپاس
            </button>
            {control.isPending && <span className="muted">در حال اجرا…</span>}
          </div>
          <div className="muted" style={{ marginTop: 8 }}>
            اقدامات بحرانی طبق سیاست، نیازمند تأیید انسانی است (Human-in-the-loop).
          </div>
        </div>
      )}

      <div className="grid cols-2">
        <TrendChart title="روند RMS ارتعاش" series={trends.rms} unit="g" />
        <TrendChart title="روند Kurtosis" series={trends.kurtosis} />
        <TrendChart title="روند شاخص سلامت (۳۰ روز)" series={trends.health_score} />
        <TrendChart title="روند RUL (۳۰ روز)" series={trends.rul_hours} unit="ساعت" />
      </div>
    </div>
  );
}
