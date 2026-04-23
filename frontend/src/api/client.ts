// API client with an offline mock layer. The advertiser-api endpoints are
// stubbed today; when they become real we flip USE_MOCKS to false and the
// pages keep working.

import axios from "axios";
import {
  Campaign,
  HealthStatus,
  OverviewStats,
  ReachSample,
  Segment,
  SegmentRule,
} from "../types";
import * as mocks from "./mocks";

const BASE = process.env.REACT_APP_ADVERTISER_API || "http://localhost:8084";
const USE_MOCKS = (process.env.REACT_APP_USE_MOCKS || "true").toLowerCase() === "true";

const http = axios.create({ baseURL: BASE, timeout: 8000 });

async function tryReal<T>(fn: () => Promise<T>, fallback: () => T): Promise<T> {
  if (USE_MOCKS) return fallback();
  try {
    return await fn();
  } catch (_e) {
    console.warn("API call failed, falling back to mock data");
    return fallback();
  }
}

export const api = {
  overview: () =>
    tryReal<OverviewStats>(
      async () => (await http.get<OverviewStats>("/v1/overview")).data,
      () => mocks.overview(),
    ),

  health: () =>
    tryReal<HealthStatus[]>(
      async () => (await http.get<HealthStatus[]>("/v1/health/all")).data,
      () => mocks.health(),
    ),

  listSegments: () =>
    tryReal<Segment[]>(
      async () => (await http.get<Segment[]>("/v1/segments")).data,
      () => mocks.segments(),
    ),

  getSegment: (id: string) =>
    tryReal<Segment | null>(
      async () => (await http.get<Segment>(`/v1/segments/${id}`)).data,
      () => mocks.segments().find((s) => s.id === id) ?? null,
    ),

  createSegment: (draft: Omit<Segment, "id" | "created_at" | "estimated_reach" | "cpm">) =>
    tryReal<Segment>(
      async () => (await http.post<Segment>("/v1/segments", draft)).data,
      () => mocks.saveSegment(draft),
    ),

  estimateReach: (rules: SegmentRule[], combinator: "and" | "or") =>
    tryReal<{ reach: number; cpm: number }>(
      async () =>
        (
          await http.post<{ reach: number; cpm: number }>("/v1/segments/estimate", {
            rules,
            rule_combinator: combinator,
          })
        ).data,
      () => mocks.estimateReach(rules, combinator),
    ),

  listCampaigns: () =>
    tryReal<Campaign[]>(
      async () => (await http.get<Campaign[]>("/v1/campaigns")).data,
      () => mocks.campaigns(),
    ),

  createCampaign: (draft: Omit<Campaign, "id" | "spend_to_date_usd" | "impressions_delivered">) =>
    tryReal<Campaign>(
      async () => (await http.post<Campaign>("/v1/campaigns", draft)).data,
      () => mocks.saveCampaign(draft),
    ),

  reachSeries: (days: number) =>
    tryReal<ReachSample[]>(
      async () =>
        (await http.get<ReachSample[]>(`/v1/reports/reach?days=${days}`)).data,
      () => mocks.reachSeries(days),
    ),
};
