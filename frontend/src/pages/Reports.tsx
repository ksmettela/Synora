import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { Campaign, ReachSample } from "../types";

function fmtMoney(n: number): string {
  return "$" + Math.round(n).toLocaleString();
}

function fmtNumber(n: number): string {
  if (n >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toLocaleString();
}

export function Reports() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [series, setSeries] = useState<ReachSample[]>([]);
  const [days, setDays] = useState(14);

  useEffect(() => {
    api.listCampaigns().then(setCampaigns);
  }, []);

  useEffect(() => {
    api.reachSeries(days).then(setSeries);
  }, [days]);

  const totals = useMemo(() => {
    const devices = series.reduce((a, s) => a + s.unique_devices, 0);
    const impressions = series.reduce((a, s) => a + s.impressions, 0);
    const spend = series.reduce((a, s) => a + s.spend_usd, 0);
    const frequency = devices > 0 ? impressions / devices : 0;
    const avgCpm = impressions > 0 ? (spend / impressions) * 1000 : 0;
    return { devices, impressions, spend, frequency, avgCpm };
  }, [series]);

  const maxImpressions = Math.max(1, ...series.map((s) => s.impressions));

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Reports</h1>
          <p className="page-sub">Reach, frequency, and CPM trends across your book of business.</p>
        </div>
        <div className="page-actions">
          <div className="segmented">
            {[7, 14, 30, 90].map((d) => (
              <button
                key={d}
                className={`segment ${d === days ? "active" : ""}`}
                onClick={() => setDays(d)}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>
      </header>

      <section className="kpi-grid">
        <div className="kpi">
          <div className="kpi-label">Unique devices</div>
          <div className="kpi-value">{fmtNumber(totals.devices)}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Impressions</div>
          <div className="kpi-value">{fmtNumber(totals.impressions)}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Avg frequency</div>
          <div className="kpi-value">{totals.frequency.toFixed(2)}x</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Spend</div>
          <div className="kpi-value">{fmtMoney(totals.spend)}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Avg CPM</div>
          <div className="kpi-value">${totals.avgCpm.toFixed(2)}</div>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Daily delivery</h2>
          <span className="card-sub">impressions per day</span>
        </div>
        <div className="chart">
          {series.map((s) => {
            const h = Math.round((s.impressions / maxImpressions) * 100);
            return (
              <div
                key={s.ts}
                className="bar-col"
                title={`${s.ts}: ${fmtNumber(s.impressions)} impressions · ${fmtMoney(s.spend_usd)}`}
              >
                <div className="bar" style={{ height: `${h}%` }} />
                <div className="bar-label">{s.ts.slice(5)}</div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <h2>By campaign</h2>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Campaign</th>
              <th>Advertiser</th>
              <th className="num">Impressions</th>
              <th className="num">Spend</th>
              <th className="num">eCPM</th>
              <th className="num">Budget used</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => {
              const ecpm = c.impressions_delivered > 0
                ? (c.spend_to_date_usd / c.impressions_delivered) * 1000
                : 0;
              const pct = (c.spend_to_date_usd / c.budget_usd) * 100;
              return (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>{c.advertiser}</td>
                  <td className="num">{fmtNumber(c.impressions_delivered)}</td>
                  <td className="num">{fmtMoney(c.spend_to_date_usd)}</td>
                  <td className="num">${ecpm.toFixed(2)}</td>
                  <td className="num">{pct.toFixed(1)}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}
