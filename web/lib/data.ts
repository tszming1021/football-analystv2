import fs from "node:fs/promises";
import path from "node:path";
import { createClient } from "@supabase/supabase-js";
import { SUPABASE_URL } from "./supabase/config";
import type { ImpliedProbability, MatchItem, MatchPayload, OddsMap } from "./types";

const DATA_PATH = path.join(process.cwd(), "data", "current_matches.json");

export async function getPayload(): Promise<MatchPayload> {
  const databasePayload = await getLatestDatabasePayload();
  if (databasePayload) return databasePayload;
  const raw = await fs.readFile(DATA_PATH, "utf-8");
  return JSON.parse(raw) as MatchPayload;
}

async function getLatestDatabasePayload(): Promise<MatchPayload | null> {
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!key) return null;
  const client = createClient(SUPABASE_URL, key, { auth: { autoRefreshToken: false, persistSession: false } });
  const { data: run } = await client.from("scrape_runs").select("fetched_at, source_url, counts, errors").order("created_at", { ascending: false }).limit(1).maybeSingle();
  if (!run) return null;
  const { data: rows } = await client.from("matches").select("payload").gte("updated_at", run.fetched_at);
  const matches = (rows || []).map((row) => row.payload as MatchItem);
  if (!matches.length) return null;
  return { fetched_at: run.fetched_at, source_url: run.source_url, counts: run.counts as MatchPayload["counts"], errors: run.errors as Record<string, string>, matches };
}

export async function getMatches(): Promise<MatchItem[]> {
  const payload = await getPayload();
  return payload.matches;
}

export async function getMatch(id: string): Promise<MatchItem | undefined> {
  const matches = await getMatches();
  return matches.find((item) => item.fixture_page_id === id || item.match_num === decodeURIComponent(id));
}

export function formatHandicap(value: number | null): string {
  if (value === null) return "-";
  if (value > 0) return `+${value}`;
  return String(value);
}

export function oddsTriplet(map: OddsMap): ImpliedProbability[] {
  const labels: Record<string, string> = {
    "3": "胜",
    "1": "平",
    "0": "负"
  };
  const rows = ["3", "1", "0"]
    .filter((key) => typeof map[key] === "number")
    .map((key) => ({
      key,
      label: labels[key] || key,
      odds: map[key],
      probability: 1 / map[key],
      normalized: 0
    }));
  const total = rows.reduce((sum, item) => sum + item.probability, 0);
  return rows.map((item) => ({
    ...item,
    normalized: total > 0 ? item.probability / total : 0
  }));
}

export function strongestSide(map: OddsMap): string {
  const rows = oddsTriplet(map);
  const strongest = rows.reduce<ImpliedProbability | undefined>(
    (best, item) => (!best || item.normalized > best.normalized ? item : best),
    undefined
  );
  return strongest ? strongest.label : "-";
}

export function topEntries(map: OddsMap, limit: number): [string, number][] {
  return Object.entries(map)
    .sort((a, b) => a[1] - b[1])
    .slice(0, limit);
}

export function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
