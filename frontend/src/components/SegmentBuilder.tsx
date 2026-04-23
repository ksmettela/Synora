import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { Segment, SegmentRule } from "../types";

interface Props {
  onCreated: (seg: Segment) => void;
  onCancel: () => void;
}

const FIELD_OPTIONS: { value: SegmentRule["field"]; label: string }[] = [
  { value: "genre", label: "Genre" },
  { value: "dma", label: "DMA (market)" },
  { value: "income", label: "Household income" },
  { value: "behavior", label: "Behavior" },
  { value: "device_type", label: "Device type" },
];

const DEFAULTS: Record<SegmentRule["field"], { op: SegmentRule["op"]; value: SegmentRule["value"] }> = {
  genre: { op: "eq", value: "sports" },
  dma: { op: "in", value: ["Los Angeles", "New York"] },
  income: { op: "gte", value: 50000 },
  behavior: { op: "eq", value: "cord_cutter" },
  device_type: { op: "eq", value: "smart_tv" },
};

function newRule(field: SegmentRule["field"] = "genre"): SegmentRule {
  return { id: Math.random().toString(36).slice(2, 9), field, ...DEFAULTS[field] };
}

function fmtNumber(n: number): string {
  if (n >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toLocaleString();
}

export function SegmentBuilder({ onCreated, onCancel }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [rules, setRules] = useState<SegmentRule[]>([newRule()]);
  const [combinator, setCombinator] = useState<"and" | "or">("and");
  const [estimate, setEstimate] = useState<{ reach: number; cpm: number } | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.estimateReach(rules, combinator).then((r) => {
      if (!cancelled) setEstimate(r);
    });
    return () => {
      cancelled = true;
    };
  }, [rules, combinator]);

  const canSave = useMemo(() => name.trim().length > 0 && rules.length > 0, [name, rules]);

  const updateRule = (id: string, patch: Partial<SegmentRule>) => {
    setRules((rs) => rs.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  const changeField = (id: string, field: SegmentRule["field"]) => {
    setRules((rs) => rs.map((r) => (r.id === id ? { id, field, ...DEFAULTS[field] } : r)));
  };

  const save = async () => {
    if (!canSave) return;
    setSaving(true);
    const seg = await api.createSegment({
      name,
      description,
      rules,
      rule_combinator: combinator,
    });
    setSaving(false);
    onCreated(seg);
  };

  return (
    <section className="card builder">
      <div className="card-head">
        <h2>New segment</h2>
        <span className="card-sub">Live reach estimate updates as rules change.</span>
      </div>

      <div className="form-row">
        <label className="form-label">Name</label>
        <input
          className="form-input"
          placeholder="e.g. Sports fans — Northeast, HHI $75K+"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className="form-row">
        <label className="form-label">Description</label>
        <input
          className="form-input"
          placeholder="One-sentence description for your team"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      <div className="rules-header">
        <span className="form-label">Rules</span>
        <div className="combinator">
          <label>
            <input
              type="radio"
              checked={combinator === "and"}
              onChange={() => setCombinator("and")}
            />
            Match ALL (AND)
          </label>
          <label>
            <input
              type="radio"
              checked={combinator === "or"}
              onChange={() => setCombinator("or")}
            />
            Match ANY (OR)
          </label>
        </div>
      </div>

      <div className="rules-stack">
        {rules.map((rule) => (
          <div key={rule.id} className="rule-row">
            <select
              className="form-input"
              value={rule.field}
              onChange={(e) => changeField(rule.id, e.target.value as SegmentRule["field"])}
            >
              {FIELD_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <select
              className="form-input"
              value={rule.op}
              onChange={(e) => updateRule(rule.id, { op: e.target.value as SegmentRule["op"] })}
            >
              <option value="eq">equals</option>
              <option value="in">is any of</option>
              <option value="gte">&ge;</option>
              <option value="lte">&le;</option>
              <option value="between">between</option>
            </select>
            <input
              className="form-input rule-value"
              value={Array.isArray(rule.value) ? rule.value.join(", ") : String(rule.value)}
              onChange={(e) => {
                const txt = e.target.value;
                const v: SegmentRule["value"] =
                  rule.op === "in"
                    ? txt.split(",").map((s) => s.trim()).filter(Boolean)
                    : !isNaN(Number(txt)) && txt.trim() !== ""
                      ? Number(txt)
                      : txt;
                updateRule(rule.id, { value: v });
              }}
            />
            {rules.length > 1 && (
              <button
                className="btn btn-ghost"
                onClick={() => setRules((rs) => rs.filter((r) => r.id !== rule.id))}
              >
                ×
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="rules-actions">
        <button className="btn btn-ghost" onClick={() => setRules((rs) => [...rs, newRule()])}>
          + Add rule
        </button>
      </div>

      <div className="estimate-panel">
        <div>
          <div className="estimate-label">Estimated reach</div>
          <div className="estimate-value">
            {estimate ? `${fmtNumber(estimate.reach)} devices` : "—"}
          </div>
        </div>
        <div>
          <div className="estimate-label">Expected CPM</div>
          <div className="estimate-value">
            {estimate ? `$${estimate.cpm.toFixed(2)}` : "—"}
          </div>
        </div>
      </div>

      <div className="form-footer">
        <button className="btn btn-ghost" onClick={onCancel}>
          Cancel
        </button>
        <button className="btn btn-primary" disabled={!canSave || saving} onClick={save}>
          {saving ? "Saving…" : "Save segment"}
        </button>
      </div>
    </section>
  );
}
