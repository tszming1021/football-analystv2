import type { MatchItem, MatchPayload, OddsMap } from "./types";
import { persistPayload, type PersistenceResult } from "./database";

const TRADE_URL = "https://trade.500.com/jczq/index.php?playid=312&g=2";
const USER_AGENT = "Mozilla/5.0 (compatible; FootballAnalyst/1.0)";

export type RefreshResult = {
  payload: MatchPayload;
  stdout: string;
  stderr: string;
  persistence: PersistenceResult;
};

export async function refreshMatchData(): Promise<RefreshResult> {
  const html = await fetch500(TRADE_URL);
  const { matches, counts } = parseMatches(html);
  const payload: MatchPayload = {
    fetched_at: new Date().toISOString(),
    source_url: TRADE_URL,
    counts,
    matches,
    errors: {}
  };
  const persistence = await persistPayload(payload);
  return { payload, stdout: "", stderr: "", persistence };
}

async function fetch500(url: string) {
  const response = await fetch(url, {
    headers: { "User-Agent": USER_AGENT, Accept: "text/html,application/xhtml+xml" },
    cache: "no-store",
    signal: AbortSignal.timeout(45_000)
  });
  if (!response.ok) throw new Error(`500网抓取失败: HTTP ${response.status}`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  return decodeGb18030(bytes);
}

function decodeGb18030(bytes: Uint8Array) {
  try {
    return new TextDecoder("gb18030").decode(bytes);
  } catch {
    return new TextDecoder().decode(bytes);
  }
}

function parseMatches(html: string) {
  const rows = [...html.matchAll(/<tr\b([^>]*data-matchnum[^>]*)>([\s\S]*?)<\/tr>/gi)];
  const matches: MatchItem[] = [];
  let ended = 0;

  for (let index = 0; index < rows.length; index += 1) {
    const attrs = rows[index][1];
    const body = rows[index][2];
    const isEnd = attr(attrs, "data-isend") === "1";
    if (isEnd) ended += 1;
    if (isEnd) continue;
    const next = html.slice((rows[index].index || 0) + rows[index][0].length, rows[index + 1]?.index || html.length);
    const more = next.match(/<tr\b[^>]*class=["'][^"']*bet-more-wrap[^"']*["'][^>]*>([\s\S]*?)<\/tr>/i)?.[1] || "";
    const match: MatchItem = {
      match_num: attr(attrs, "data-matchnum"),
      fixture_page_id: attr(attrs, "data-fixtureid"),
      league: attr(attrs, "data-simpleleague"),
      home: attr(attrs, "data-homesxname"),
      away: attr(attrs, "data-awaysxname"),
      kickoff: `${attr(attrs, "data-matchdate")} ${attr(attrs, "data-matchtime")}`.trim(),
      match_date: attr(attrs, "data-matchdate"),
      match_time: attr(attrs, "data-matchtime"),
      handicap: numberOrNull(attr(attrs, "data-rangqiu")),
      sale: {
        is_end: false,
        is_active: attr(attrs, "data-isactive") === "1",
        subactive: attr(attrs, "data-subactive"),
        buy_end_time: attr(attrs, "data_buyendtime"),
        display_style: attr(attrs, "style")
      },
      one_x_two: priceMap(body, "nspf"),
      handicap_three_way: priceMap(body, "spf"),
      half_full: priceMap(more, "bqc"),
      scores: renameScores(priceMap(more, "bf")),
      total_exact: priceMap(more, "jqs")
    };
    matches.push(match);
  }

  return {
    matches,
    counts: { rows: rows.length, on_sale: rows.length - ended, ended, included: matches.length }
  };
}

function priceMap(html: string, dataType: string): OddsMap {
  const result: OddsMap = {};
  const tags = html.match(/<[^>]*>/g) || [];
  for (const tag of tags) {
    if (attr(tag, "data-type") !== dataType) continue;
    const key = attr(tag, "data-value");
    const value = Number(attr(tag, "data-sp"));
    if (key && Number.isFinite(value)) result[key] = value;
  }
  return result;
}

function renameScores(scores: OddsMap) {
  return Object.fromEntries(Object.entries(scores).map(([key, value]) => [key.replace(":", "-"), value]));
}

function attr(source: string, name: string) {
  const match = source.match(new RegExp(`${name}\\s*=\\s*["']([^"']*)["']`, "i"));
  return decodeHtml(match?.[1] || "");
}

function decodeHtml(value: string) {
  return value.replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, " ");
}

function numberOrNull(value: string) {
  if (!value) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function toRefreshResponse(result: RefreshResult) {
  return {
    ok: true,
    fetched_at: result.payload.fetched_at,
    counts: result.payload.counts,
    errors: result.payload.errors,
    persistence: result.persistence,
    stdout: safeTail(result.stdout),
    stderr: safeTail(result.stderr)
  };
}

function safeTail(value: string) {
  return value.length > 4000 ? value.slice(-4000) : value;
}
