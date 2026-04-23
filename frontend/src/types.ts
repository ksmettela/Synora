// Domain types shared across pages.

export type Genre = "sports" | "news" | "drama" | "comedy" | "reality" | "kids";

export interface SegmentRule {
  id: string;
  field: "genre" | "dma" | "income" | "behavior" | "device_type";
  op: "eq" | "in" | "gte" | "lte" | "between";
  value: string | number | [number, number] | string[];
}

export interface Segment {
  id: string;
  name: string;
  description: string;
  rules: SegmentRule[];
  rule_combinator: "and" | "or";
  estimated_reach: number;
  cpm: number;
  created_at: string;
}

export interface Campaign {
  id: string;
  name: string;
  advertiser: string;
  segment_id: string;
  segment_name: string;
  budget_usd: number;
  status: "draft" | "active" | "paused" | "ended";
  start_date: string;
  end_date: string;
  spend_to_date_usd: number;
  impressions_delivered: number;
}

export interface ReachSample {
  ts: string; // ISO date
  unique_devices: number;
  impressions: number;
  spend_usd: number;
}

export interface OverviewStats {
  active_campaigns: number;
  devices_online_24h: number;
  fingerprints_matched_24h: number;
  match_rate_pct: number;
  spend_mtd_usd: number;
}

export interface HealthStatus {
  service: string;
  status: "ok" | "degraded" | "down";
  latency_ms?: number;
}
