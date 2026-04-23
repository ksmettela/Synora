import React, { useState } from "react";

export function Settings() {
  const [apiKey] = useState("syn_sk_live_" + Math.random().toString(36).slice(2, 14));
  const [revealed, setRevealed] = useState(false);
  const [contactEmail, setContactEmail] = useState("ops@example.com");
  const [openrtbUrl, setOpenrtbUrl] = useState("https://rtb.synora.example/bid");
  const [revShare, setRevShare] = useState(30);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Settings</h1>
          <p className="page-sub">API credentials, RTB wiring, and billing configuration.</p>
        </div>
      </header>

      <section className="card">
        <div className="card-head">
          <h2>API key</h2>
          <span className="card-sub">Used for advertiser API authentication.</span>
        </div>
        <div className="key-row">
          <code className="key-value">{revealed ? apiKey : "•".repeat(apiKey.length)}</code>
          <button className="btn btn-ghost" onClick={() => setRevealed(!revealed)}>
            {revealed ? "Hide" : "Reveal"}
          </button>
          <button
            className="btn btn-ghost"
            onClick={() => {
              navigator.clipboard?.writeText(apiKey);
            }}
          >
            Copy
          </button>
          <button className="btn btn-ghost danger">Rotate</button>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <h2>OpenRTB endpoint</h2>
          <span className="card-sub">DSPs POST bid requests here.</span>
        </div>
        <div className="form-row">
          <label className="form-label">Endpoint</label>
          <input
            className="form-input"
            value={openrtbUrl}
            onChange={(e) => setOpenrtbUrl(e.target.value)}
          />
        </div>
        <div className="form-row">
          <label className="form-label">Protocol</label>
          <input className="form-input" value="OpenRTB 2.6" disabled />
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Billing</h2>
          <span className="card-sub">Manufacturer revenue share + Stripe payouts.</span>
        </div>
        <div className="form-grid">
          <div className="form-row">
            <label className="form-label">Ops contact</label>
            <input
              className="form-input"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
            />
          </div>
          <div className="form-row">
            <label className="form-label">Manufacturer share (%)</label>
            <input
              className="form-input"
              type="number"
              min={0}
              max={100}
              value={revShare}
              onChange={(e) => setRevShare(Number(e.target.value))}
            />
          </div>
          <div className="form-row">
            <label className="form-label">Platform share (%)</label>
            <input className="form-input" value={100 - revShare} disabled />
          </div>
          <div className="form-row">
            <label className="form-label">Payout cadence</label>
            <input className="form-input" value="Monthly (1st)" disabled />
          </div>
        </div>
      </section>
    </div>
  );
}
