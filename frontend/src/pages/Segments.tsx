import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { Segment } from "../types";
import { SegmentBuilder } from "../components/SegmentBuilder";

function fmtNumber(n: number): string {
  if (n >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toLocaleString();
}

export function Segments() {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [showBuilder, setShowBuilder] = useState(false);

  useEffect(() => {
    api.listSegments().then(setSegments);
  }, []);

  const onCreated = (seg: Segment) => {
    setSegments((cur) => [seg, ...cur]);
    setShowBuilder(false);
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Segments</h1>
          <p className="page-sub">
            Define audience cohorts. Each rule narrows (AND) or widens (OR) the addressable reach.
          </p>
        </div>
        <div className="page-actions">
          <button className="btn btn-primary" onClick={() => setShowBuilder(true)}>
            + New segment
          </button>
        </div>
      </header>

      {showBuilder && (
        <SegmentBuilder onCreated={onCreated} onCancel={() => setShowBuilder(false)} />
      )}

      <section className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Rules</th>
              <th>Logic</th>
              <th className="num">Est. reach</th>
              <th className="num">CPM</th>
            </tr>
          </thead>
          <tbody>
            {segments.map((s) => (
              <tr key={s.id}>
                <td>
                  <div className="cell-primary">{s.name}</div>
                  <div className="cell-sub">{s.description}</div>
                </td>
                <td>
                  <div className="rule-chips">
                    {s.rules.map((r) => (
                      <span key={r.id} className="chip">
                        {r.field} {r.op} {Array.isArray(r.value) ? r.value.join(", ") : String(r.value)}
                      </span>
                    ))}
                  </div>
                </td>
                <td>
                  <span className="chip chip-muted">{s.rule_combinator.toUpperCase()}</span>
                </td>
                <td className="num">{fmtNumber(s.estimated_reach)} devices</td>
                <td className="num">${s.cpm.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
