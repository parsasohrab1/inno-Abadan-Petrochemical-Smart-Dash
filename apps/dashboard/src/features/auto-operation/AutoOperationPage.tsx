import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, currentRole } from "../../lib/api";
import { StatCard, usd } from "../../components/common";
import { useLiveFeed } from "../../lib/useLiveFeed";

const LEVEL_FA = ["", "پایش", "تحلیل", "هشدار", "توصیه", "اقدام"];

export function AutoOperationPage() {
  const qc = useQueryClient();
  const canApprove = ["operator", "maintenance", "engineer", "manager", "admin"].includes(currentRole());

  const stats = useQuery({
    queryKey: ["ao-stats"],
    queryFn: () => api.get("/api/auto-operation/stats").then((r) => r.data),
  });
  const actions = useQuery({
    queryKey: ["ao-actions"],
    queryFn: () => api.get("/api/auto-operation/actions").then((r) => r.data),
  });

  useLiveFeed((m) => {
    if (m.channel === "auto_action") {
      qc.invalidateQueries({ queryKey: ["ao-actions"] });
      qc.invalidateQueries({ queryKey: ["ao-stats"] });
    }
  });

  const decide = useMutation({
    mutationFn: ({ id, decision }: { id: number; decision: "approve" | "reject" }) =>
      api.post(`/api/auto-operation/actions/${id}/${decision}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ao-actions"] });
      qc.invalidateQueries({ queryKey: ["ao-stats"] });
    },
  });

  const pending = (actions.data ?? []).filter((a: any) => a.status === "awaiting_approval");
  const history = (actions.data ?? []).filter((a: any) => a.status !== "awaiting_approval");

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="grid cols-4">
        <StatCard title="حالت سیستم" value={stats.data?.mode ?? "…"} />
        <StatCard title="کل اقدامات" value={stats.data?.total_actions ?? "…"} />
        <StatCard title="در انتظار تأیید" value={pending.length} />
        <StatCard title="صرفه‌جویی محقق‌شده" value={usd(stats.data?.realized_savings_usd)} />
      </div>

      <div className="card">
        <h3>اقدامات در انتظار تأیید انسانی (Human-in-the-loop — FR-17)</h3>
        {pending.length === 0 && <div className="muted">موردی در انتظار نیست.</div>}
        <table>
          <tbody>
            {pending.map((a: any) => (
              <tr key={a.id}>
                <td>سطح {a.level} · {LEVEL_FA[a.level]}</td>
                <td><b>{a.action_type}</b></td>
                <td>{a.equipment_tag}</td>
                <td>{a.rationale}</td>
                <td>{usd(a.estimated_savings_usd)}</td>
                <td>
                  {canApprove && (
                    <div className="row">
                      <button className="ok" onClick={() => decide.mutate({ id: a.id, decision: "approve" })}>
                        تأیید و اجرا
                      </button>
                      <button className="danger" onClick={() => decide.mutate({ id: a.id, decision: "reject" })}>
                        رد
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>لاگ اقدامات خودکار</h3>
        <table>
          <thead>
            <tr><th>زمان</th><th>سطح</th><th>نوع</th><th>تجهیز</th><th>وضعیت</th><th>صرفه‌جویی</th><th>دلیل</th></tr>
          </thead>
          <tbody>
            {history.slice(0, 100).map((a: any) => (
              <tr key={a.id}>
                <td>{new Date(a.created_at).toLocaleString("fa-IR")}</td>
                <td>{a.level}</td>
                <td>{a.action_type}</td>
                <td>{a.equipment_tag ?? "—"}</td>
                <td>{a.status}</td>
                <td>{usd(a.estimated_savings_usd)}</td>
                <td>{a.rationale}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
