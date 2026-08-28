import { ReactNode } from "react";

export type Color = "green" | "yellow" | "red";

export const FA_COLOR: Record<Color, string> = {
  green: "سالم",
  yellow: "هشدار",
  red: "خطا",
};

export function HealthDot({ color, label }: { color: Color; label?: boolean }) {
  return (
    <span>
      <span className={`dot ${color}`} />
      {label && FA_COLOR[color]}
    </span>
  );
}

export function Badge({ color, children }: { color: Color; children: ReactNode }) {
  return <span className={`badge ${color}`}>{children}</span>;
}

export function StatCard({ title, value, sub }: { title: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="stat">{value}</div>
      {sub && <div className="muted" style={{ marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

export function usd(n: number | undefined | null): string {
  if (n == null || Number.isNaN(n)) return "—";
  return "$" + Math.round(n).toLocaleString("en-US");
}

/** واحد اندازه‌گیری همیشه کنار مقدار (الزام کاربر). */
export function Measure({ value, unit }: { value: number | string; unit: string }) {
  return (
    <span>
      {typeof value === "number" ? value.toLocaleString("fa-IR") : value}{" "}
      <span className="muted">{unit}</span>
    </span>
  );
}
