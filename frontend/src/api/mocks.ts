// Deterministic mocks. In-memory writes persist for the session only; this
// is enough to dogfood flows without standing up the backend.

import {
  Campaign,
  HealthStatus,
  OverviewStats,
  ReachSample,
  Segment,
  SegmentRule,
} from "../types";

// Seed data is deliberately plausible (mid-market US ACR platform numbers).

let _segments: Segment[] = [
  {
    id: "seg_sports_ca_50k",
    name: "Sports Fans — CA, $50K+",
    description: "Sports-viewing households in California with household income over $50K.",
    rules: [
      { id: "r1", field: "genre", op: "eq", value: "sports" },
      { id: "r2", field: "dma", op: "in", value: ["Los Angeles", "San Francisco", "Sacramento"] },
      { id: "r3", field: "income", op: "gte", value: 50000 },
    ],
    rule_combinator: "and",
    estimated_reach: 2_340_000,
    cpm: 0.23,
    created_at: "2026-04-01T12:00:00Z",
  },
  {
    id: "seg_cord_cutters_sports",
    name: "Cord-cutters watching live sports",
    description: "Devices with no detected cable box that surface live sports broadcasts.",
    rules: [
      { id: "r1", field: "behavior", op: "eq", value: "cord_cutter" },
      { id: "r2", field: "genre", op: "eq", value: "sports" },
    ],
    rule_combinator: "and",
    estimated_reach: 1_120_000,
    cpm: 0.28,
    created_at: "2026-04-05T15:30:00Z",
  },
  {
    id: "seg_news_all",
    name: "Daily news viewers",
    description: "Households regularly watching evening news across broadcast and cable.",
    rules: [{ id: "r1", field: "genre", op: "eq", value: "news" }],
    rule_combinator: "and",
    estimated_reach: 8_600_000,
    cpm: 0.12,
    created_at: "2026-03-18T09:00:00Z",
  },
];

let _campaigns: Campaign[] = [
  {
    id: "cmp_001",
    name: "Playoff Push — National",
    advertiser: "Bud Light",
    segment_id: "seg_sports_ca_50k",
    segment_name: "Sports Fans — CA, $50K+",
    budget_usd: 250_000,
    status: "active",
    start_date: "2026-04-10",
    end_date: "2026-05-31",
    spend_to_date_usd: 84_320,
    impressions_delivered: 4_120_000,
  },
  {
    id: "cmp_002",
    name: "Spring Truck Launch",
    advertiser: "Ford Motor Co",
    segment_id: "seg_cord_cutters_sports",
    segment_name: "Cord-cutters watching live sports",
    budget_usd: 180_000,
    status: "active",
    start_date: "2026-04-15",
    end_date: "2026-06-15",
    spend_to_date_usd: 31_290,
    impressions_delivered: 1_470_000,
  },
  {
    id: "cmp_003",
    name: "Quarterly Brand Awareness",
    advertiser: "Geico",
    segment_id: "seg_news_all",
    segment_name: "Daily news viewers",
    budget_usd: 420_000,
    status: "paused",
    start_date: "2026-03-20",
    end_date: "2026-06-20",
    spend_to_date_usd: 220_440,
    impressions_delivered: 18_700_000,
  },
];

export function overview(): OverviewStats {
  return {
    active_campaigns: _campaigns.filter((c) => c.status === "active").length,
    devices_online_24h: 11_430_000,
    fingerprints_matched_24h: 712_400_000,
    match_rate_pct: 87.4,
    spend_mtd_usd: 336_050,
  };
}

export function health(): HealthStatus[] {
  return [
    { service: "fingerprint-ingestor", status: "ok", latency_ms: 42 },
    { service: "matching-engine", status: "ok", latency_ms: 186 },
    { service: "fingerprint-indexer", status: "ok", latency_ms: 18 },
    { service: "segmentation-engine", status: "ok", latency_ms: 71 },
    { service: "advertiser-api", status: "ok", latency_ms: 9 },
    { service: "privacy-service", status: "ok", latency_ms: 24 },
    { service: "billing-service", status: "degraded", latency_ms: 480 },
  ];
}

export function segments(): Segment[] {
  return _segments.slice();
}

export function saveSegment(
  draft: Omit<Segment, "id" | "created_at" | "estimated_reach" | "cpm">,
): Segment {
  const { reach, cpm } = estimateReach(draft.rules, draft.rule_combinator);
  const seg: Segment = {
    ...draft,
    id: `seg_${Date.now().toString(36)}`,
    created_at: new Date().toISOString(),
    estimated_reach: reach,
    cpm,
  };
  _segments = [seg, ..._segments];
  return seg;
}

export function campaigns(): Campaign[] {
  return _campaigns.slice();
}

export function saveCampaign(
  draft: Omit<Campaign, "id" | "spend_to_date_usd" | "impressions_delivered">,
): Campaign {
  const cmp: Campaign = {
    ...draft,
    id: `cmp_${Date.now().toString(36)}`,
    spend_to_date_usd: 0,
    impressions_delivered: 0,
  };
  _campaigns = [cmp, ..._campaigns];
  return cmp;
}

export function estimateReach(
  rules: SegmentRule[],
  combinator: "and" | "or",
): { reach: number; cpm: number } {
  // Base of ~120M US Smart TV households. Each rule tightens or widens the
  // estimate; CPM scales up as the segment narrows.
  const base = 120_000_000;
  const ruleFactor = (rule: SegmentRule): number => {
    switch (rule.field) {
      case "genre":
        return rule.value === "sports" ? 0.18 : rule.value === "news" ? 0.32 : 0.22;
      case "dma":
        return Array.isArray(rule.value) ? Math.min(1, rule.value.length * 0.06) : 0.1;
      case "income":
        return 0.45;
      case "behavior":
        return 0.09;
      case "device_type":
        return 0.3;
      default:
        return 0.5;
    }
  };

  if (rules.length === 0) {
    return { reach: base, cpm: 0.05 };
  }

  const factors = rules.map(ruleFactor);
  const combined =
    combinator === "and"
      ? factors.reduce((a, b) => a * b, 1)
      : 1 - factors.reduce((a, b) => a * (1 - b), 1);
  const reach = Math.round(base * combined);
  // CPM loosely inverse to reach saturation.
  const cpm = Math.min(0.95, 0.05 + (1 - combined) * 0.6);
  return { reach, cpm: Number(cpm.toFixed(2)) };
}

export function reachSeries(days: number): ReachSample[] {
  const out: ReachSample[] = [];
  const today = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const dayIndex = days - i;
    const base = 9_500_000 + Math.sin(dayIndex / 3) * 400_000;
    out.push({
      ts: d.toISOString().slice(0, 10),
      unique_devices: Math.round(base + Math.random() * 200_000),
      impressions: Math.round(base * 3.2 + Math.random() * 600_000),
      spend_usd: Math.round(base * 0.018 + Math.random() * 2_500),
    });
  }
  return out;
}
