import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { HealthStatus, OverviewStats, ReachSample } from "../types";

function fmtNumber(n: number): string {
  if (n >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toLocaleString();
}

function fmtMoney(n: number): string {
  return "$" + n.toLocaleString();
}

export function Overview() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [health, setHealth] = useState<HealthStatus[]>([]);
  const [series, setSeries] = useState<ReachSample[]>([]);

  useEffect(() => {
    api.overview().then(setStats);
    api.health().then(setHealth);
    api.reachSeries(14).then(setSeries);
  }, []);

  const maxDevices = Math.max(1, ...series.map((s) => s.unique_devices));

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Overview</h1>
          <p className="page-sub">Platform health and campaign activity.</p>
        </div>
      </header>

      <section className="kpi-grid">
        <KPI label="Active campaigns" value={stats ? stats.active_campaigns.toString() : "—"} />
        <KPI label="Devices online · 24h" value={stats ? fmtNumber(stats.devices_online_24h) : "—"} />
        <KPI
          label="Fingerprints matched · 24h"
          value={stats ? fmtNumber(stats.fingerprints_matched_24h) : "—"}
        />
        <KPI
          label="Match rate"
          value={stats ? stats.match_rate_pct.toFixed(1) + "%" : "—"}
        />
        <KPI label="Spend · MTD" value={stats ? fmtMoney(stats.spend_mtd_usd) : "—"} />
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Reach · last 14 days</h2>
          <span className="card-sub">unique devices delivering impressions</span>
        </div>
        <div className="chart">
          {series.map((s) => {
            const h = Math.round((s.unique_devices / maxDevices) * 100);
            return (
              <div key={s.ts} className="bar-col" title={`${s.ts}: ${fmtNumber(s.unique_devices)} devices`}>
                <div className="bar" style={{ height: `${h}%` }} />
                <div className="bar-label">{s.ts.slice(5)}</div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Service health</h2>
          <span className="card-sub">live probe of each microservice</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Service</th>
              <th>Status</th>
              <th className="num">Latency (p50)</th>
            </tr>
          </thead>
          <tbody>
            {health.map((h) => (
              <tr key={h.service}>
                <td>{h.service}</td>
                <td>
                  <span className={`status-pill status-${h.status}`}>{h.status}</span>
                </td>
                <td className="num">{h.latency_ms !== undefined ? `${h.latency_ms} ms` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function KPI({ label, value }: { label: string; value: string }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
    </div>
  );
}
