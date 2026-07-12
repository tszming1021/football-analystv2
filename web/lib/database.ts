import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { analyzeMatch } from "./analysis";
import type { MatchItem, MatchPayload } from "./types";

export type PersistenceResult = {
  enabled: boolean;
  savedMatches: number;
  savedReports: number;
};

export function databaseConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY);
}

export async function persistPayload(payload: MatchPayload): Promise<PersistenceResult> {
  if (!databaseConfigured()) {
    return { enabled: false, savedMatches: 0, savedReports: 0 };
  }

  const client = createServerClient();
  const { data: run, error: runError } = await client
    .from("scrape_runs")
    .insert({
      fetched_at: payload.fetched_at,
      source_url: payload.source_url,
      counts: payload.counts,
      errors: payload.errors
    })
    .select("id")
    .single();

  if (runError) throw new Error(`保存抓取记录失败: ${runError.message}`);

  const matches = payload.matches.map((match) => ({
    fixture_page_id: match.fixture_page_id,
    match_num: match.match_num,
    league: match.league,
    home: match.home,
    away: match.away,
    kickoff: match.kickoff,
    match_date: match.match_date,
    match_time: match.match_time,
    is_end: match.sale.is_end,
    is_active: match.sale.is_active,
    payload: match,
    updated_at: payload.fetched_at
  }));

  const { error: matchesError } = await client.from("matches").upsert(matches);
  if (matchesError) throw new Error(`保存比赛失败: ${matchesError.message}`);

  const snapshots = payload.matches.map((match) => ({
    scrape_run_id: run.id,
    fixture_page_id: match.fixture_page_id,
    one_x_two: match.one_x_two,
    handicap_three_way: match.handicap_three_way,
    half_full: match.half_full,
    scores: match.scores,
    total_exact: match.total_exact,
    deep_market: match.deep_market ?? null,
    captured_at: payload.fetched_at
  }));

  const { error: snapshotsError } = await client.from("odds_snapshots").insert(snapshots);
  if (snapshotsError) throw new Error(`保存赔率快照失败: ${snapshotsError.message}`);

  const reports = payload.matches.map((match) => reportRow(match, payload.fetched_at));
  const { error: reportsError } = await client.from("match_reports").upsert(reports);
  if (reportsError) throw new Error(`保存分析报告失败: ${reportsError.message}`);

  return { enabled: true, savedMatches: matches.length, savedReports: reports.length };
}

function createServerClient(): SupabaseClient {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("Supabase 环境变量不完整");
  return createClient(url, key, { auth: { autoRefreshToken: false, persistSession: false } });
}

function reportRow(match: MatchItem, generatedAt: string) {
  const report = analyzeMatch(match);
  return {
    fixture_page_id: match.fixture_page_id,
    generated_at: generatedAt,
    primary_pick: report.primary.label,
    handicap_pick: report.handicap.label,
    goals_pick: report.goals.label,
    xg_home: report.xg.home,
    xg_away: report.xg.away,
    xg_total: report.xg.total,
    score_top3: report.scoreCandidates.slice(0, 3),
    report
  };
}
