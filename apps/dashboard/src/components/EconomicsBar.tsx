import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useLiveFeed } from "../lib/useLiveFeed";
import { usd } from "./common";

type Econ = {
  profit_rate_usd_per_hour: number;
  savings_rate_usd_per_hour: number;
  profit_today_usd: number;
  savings_today_usd: number;
  savings_mtd_usd: number;
};

/** نوار اقتصادی مدیریتی — سود و صرفه‌جویی لحظه‌ای به دلار (الزام کاربر). */
export function EconomicsBar() {
  const [econ, setEcon] = useState<Econ | null>(null);

  useEffect(() => {
    api.get("/api/economics/live").then((r) => setEcon(r.data)).catch(() => {});
  }, []);

  useLiveFeed((m) => {
    if (m.channel === "economics") setEcon(m.data);
  });

  return (
    <div className="econbar">
      <div className="econ-tile">
        <div className="label">سود لحظه‌ای (نرخ)</div>
        <div className="value pos">{usd(econ?.profit_rate_usd_per_hour)}<span className="muted" style={{ fontSize: 12 }}> / ساعت</span></div>
      </div>
      <div className="econ-tile">
        <div className="label">سود امروز</div>
        <div className="value pos">{usd(econ?.profit_today_usd)}</div>
      </div>
      <div className="econ-tile">
        <div className="label">صرفه‌جویی لحظه‌ای (نرخ)</div>
        <div className="value pos">{usd(econ?.savings_rate_usd_per_hour)}<span className="muted" style={{ fontSize: 12 }}> / ساعت</span></div>
      </div>
      <div className="econ-tile">
        <div className="label">صرفه‌جویی امروز · ماه</div>
        <div className="value pos">
          {usd(econ?.savings_today_usd)} <span className="muted" style={{ fontSize: 13 }}>· {usd(econ?.savings_mtd_usd)}</span>
        </div>
      </div>
    </div>
  );
}
