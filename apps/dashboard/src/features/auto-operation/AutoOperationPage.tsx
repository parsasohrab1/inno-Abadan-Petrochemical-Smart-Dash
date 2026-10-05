import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, currentRole } from "../../lib/api";
import { StatCard, usd } from "../../components/common";
import { useLiveFeed } from "../../lib/useLiveFeed";

const LEVEL_FA = ["", "Monitoring", "Analysis", "Alert", "Recommendation", "Action"];

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
        <StatCard title="System mode" value={stats.data?.mode ?? "…"} />
        <StatCard title="Total actions" value={stats.data?.total_actions ?? "…"} />
        <StatCard title="Pending approval" value={pending.length} />
        <StatCard title="Realized savings" value={usd(stats.data?.realized_savings_usd)} />
      </div>

      <div className="card">
        <h3>Actions awaiting human approval (Human-in-the-loop — FR-17)</h3>
        {pending.length === 0 && <div className="muted">Nothing is pending.</div>}
        <table>
          <tbody>
            {pending.map((a: any) => (
              <tr key={a.id}>
                <td>Level {a.level} · {LEVEL_FA[a.level]}</td>
                <td><b>{a.action_type}</b></td>
                <td>{a.equipment_tag}</td>
                <td>{a.rationale}</td>
                <td>{usd(a.estimated_savings_usd)}</td>
                <td>
                  {canApprove && (
                    <div className="row">
                      <button className="ok" onClick={() => decide.mutate({ id: a.id, decision: "approve" })}>
                        Approve and execute
                      </button>
                      <button className="danger" onClick={() => decide.mutate({ id: a.id, decision: "reject" })}>
                        Reject
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
        <h3>Automatic action log</h3>
        <table>
          <thead>
            <tr><th>Time</th><th>Level</th><th>Type</th><th>Equipment</th><th>Status</th><th>Savings</th><th>Reason</th></tr>
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
