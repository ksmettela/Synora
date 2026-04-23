import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { Campaign, Segment } from "../types";

function fmtMoney(n: number): string {
  return "$" + n.toLocaleString();
}

function fmtNumber(n: number): string {
  if (n >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toLocaleString();
}

export function Campaigns() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    api.listCampaigns().then(setCampaigns);
    api.listSegments().then(setSegments);
  }, []);

  const onCreated = (c: Campaign) => {
    setCampaigns((cur) => [c, ...cur]);
    setShowForm(false);
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Campaigns</h1>
          <p className="page-sub">Live buys against your audience segments.</p>
        </div>
        <div className="page-actions">
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            + New campaign
          </button>
        </div>
      </header>

      {showForm && (
        <CampaignForm
          segments={segments}
          onCreated={onCreated}
          onCancel={() => setShowForm(false)}
        />
      )}

      <section className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Campaign</th>
              <th>Advertiser</th>
              <th>Segment</th>
              <th>Status</th>
              <th className="num">Budget</th>
              <th className="num">Spent</th>
              <th className="num">Impressions</th>
              <th>Flight</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => {
              const pct = (c.spend_to_date_usd / c.budget_usd) * 100;
              return (
                <tr key={c.id}>
                  <td>
                    <div className="cell-primary">{c.name}</div>
                    <div className="cell-sub">{c.id}</div>
                  </td>
                  <td>{c.advertiser}</td>
                  <td>{c.segment_name}</td>
                  <td>
                    <span className={`status-pill status-${c.status}`}>{c.status}</span>
                  </td>
                  <td className="num">{fmtMoney(c.budget_usd)}</td>
                  <td className="num">
                    <div>{fmtMoney(c.spend_to_date_usd)}</div>
                    <div className="progress">
                      <div className="progress-fill" style={{ width: `${Math.min(100, pct)}%` }} />
                    </div>
                  </td>
                  <td className="num">{fmtNumber(c.impressions_delivered)}</td>
                  <td>
                    <div className="cell-sub">
                      {c.start_date} → {c.end_date}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function CampaignForm({
  segments,
  onCreated,
  onCancel,
}: {
  segments: Segment[];
  onCreated: (c: Campaign) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [advertiser, setAdvertiser] = useState("");
  const [segmentId, setSegmentId] = useState(segments[0]?.id ?? "");
  const [budget, setBudget] = useState("50000");
  const [start, setStart] = useState(new Date().toISOString().slice(0, 10));
  const [end, setEnd] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().slice(0, 10);
  });
  const [saving, setSaving] = useState(false);

  const segment = segments.find((s) => s.id === segmentId);
  const canSave = name && advertiser && segmentId && Number(budget) > 0;

  const save = async () => {
    if (!canSave || !segment) return;
    setSaving(true);
    const c = await api.createCampaign({
      name,
      advertiser,
      segment_id: segmentId,
      segment_name: segment.name,
      budget_usd: Number(budget),
      status: "draft",
      start_date: start,
      end_date: end,
    });
    setSaving(false);
    onCreated(c);
  };

  return (
    <section className="card builder">
      <div className="card-head">
        <h2>New campaign</h2>
      </div>

      <div className="form-grid">
        <div className="form-row">
          <label className="form-label">Name</label>
          <input className="form-input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="form-row">
          <label className="form-label">Advertiser</label>
          <input
            className="form-input"
            value={advertiser}
            onChange={(e) => setAdvertiser(e.target.value)}
          />
        </div>
        <div className="form-row">
          <label className="form-label">Segment</label>
          <select
            className="form-input"
            value={segmentId}
            onChange={(e) => setSegmentId(e.target.value)}
          >
            {segments.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} · ${s.cpm.toFixed(2)} CPM
              </option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label className="form-label">Budget (USD)</label>
          <input
            className="form-input"
            value={budget}
            inputMode="numeric"
            onChange={(e) => setBudget(e.target.value.replace(/[^\d]/g, ""))}
          />
        </div>
        <div className="form-row">
          <label className="form-label">Start</label>
          <input
            type="date"
            className="form-input"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </div>
        <div className="form-row">
          <label className="form-label">End</label>
          <input
            type="date"
            className="form-input"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </div>
      </div>

      <div className="form-footer">
        <button className="btn btn-ghost" onClick={onCancel}>
          Cancel
        </button>
        <button className="btn btn-primary" disabled={!canSave || saving} onClick={save}>
          {saving ? "Saving…" : "Launch as draft"}
        </button>
      </div>
    </section>
  );
}
