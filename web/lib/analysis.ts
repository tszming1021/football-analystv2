import { oddsTriplet, pct, topEntries } from "./data";
import type { MatchItem, OddsMap } from "./types";

type Pick = {
  label: string;
  odds?: number;
  probability?: number;
};

export type MatchAnalysis = {
  level: "强" | "中" | "弱";
  risk: "低" | "中" | "高";
  primary: Pick;
  handicap: Pick;
  goals: Pick;
  xg: {
    home: number;
    away: number;
    total: number;
    note: string;
  };
  scoreCandidates: Pick[];
  scoreSummary: string;
  summary: string;
  signals: string[];
};

const SIDE_NAME: Record<string, string> = {
  "3": "主胜",
  "1": "平局",
  "0": "客胜"
};

const SHORT_SIDE_NAME: Record<string, string> = {
  "3": "胜",
  "1": "平",
  "0": "负"
};

export function analyzeMatch(match: MatchItem): MatchAnalysis {
  const resultRows = oddsTriplet(match.one_x_two);
  const handicapRows = oddsTriplet(match.handicap_three_way);
  const primary = sortedByProbability(resultRows)[0];
  const second = sortedByProbability(resultRows)[1];
  const handicap = sortedByProbability(handicapRows)[0];
  const margin = primary && second ? primary.normalized - second.normalized : 0;
  const goals = chooseGoals(match.total_exact);
  const xg = estimateXg(match, primary?.key);
  const scoreCandidates = chooseScoreCandidates(match.scores, primary?.key, goals.label);
  const movement = marketMovement(match);
  const risk = assessRisk(margin, movement.conflictCount, match.handicap);
  const level = assessLevel(margin, risk);
  const signals = buildSignals(match, primary, handicap, goals, movement, margin);

  return {
    level,
    risk,
    primary: {
      label: primary ? SIDE_NAME[primary.key] || primary.label : "-",
      odds: primary?.odds,
      probability: primary?.normalized
    },
    handicap: {
      label: handicap ? `${formatHandicapText(match.handicap)} ${SHORT_SIDE_NAME[handicap.key] || handicap.label}` : "-",
      odds: handicap?.odds,
      probability: handicap?.normalized
    },
    goals,
    xg,
    scoreCandidates,
    scoreSummary: formatScoreSummary(scoreCandidates.slice(0, 3)),
    summary: buildSummary(match, primary, handicap, goals, scoreCandidates.slice(0, 3), risk, level, movement),
    signals
  };
}

function estimateXg(match: MatchItem, sideKey: string | undefined) {
  const totalFromLine = match.deep_market?.daxiao?.current?.[1];
  const totalFromGoals = expectedTotalGoals(match.total_exact);
  const totalFromScores = expectedTotalFromScores(match.scores);
  const blendedTotal = weightedAverage([
    [totalFromLine, 0.45],
    [totalFromGoals, 0.35],
    [totalFromScores, 0.2]
  ]);
  const total = clamp(blendedTotal || 2.35, 1.2, 4.2);
  const share = clamp(homeGoalShare(match, sideKey), 0.28, 0.72);
  const home = roundXg(total * share);
  const away = roundXg(total - home);
  return {
    home,
    away,
    total: roundXg(home + away),
    note: "盘口/总进球/比分盘反推"
  };
}

function expectedTotalGoals(totalExact: OddsMap) {
  const entries = Object.entries(totalExact)
    .map(([goals, odds]) => [Number(goals), odds] as const)
    .filter(([goals, odds]) => Number.isFinite(goals) && odds > 0);
  const weight = entries.reduce((sum, [, odds]) => sum + 1 / odds, 0);
  if (!weight) return undefined;
  return entries.reduce((sum, [goals, odds]) => sum + goals / odds, 0) / weight;
}

function expectedTotalFromScores(scores: OddsMap) {
  const entries = Object.entries(scores)
    .map(([label, odds]) => {
      const match = label.match(/^(\d+)-(\d+)$/);
      if (!match || odds <= 0) return null;
      return [Number(match[1]) + Number(match[2]), odds] as const;
    })
    .filter((item): item is readonly [number, number] => Boolean(item));
  const weight = entries.reduce((sum, [, odds]) => sum + 1 / odds, 0);
  if (!weight) return undefined;
  return entries.reduce((sum, [goals, odds]) => sum + goals / odds, 0) / weight;
}

function homeGoalShare(match: MatchItem, sideKey: string | undefined) {
  const rows = oddsTriplet(match.one_x_two);
  const homeProb = rows.find((row) => row.key === "3")?.normalized || 0.33;
  const awayProb = rows.find((row) => row.key === "0")?.normalized || 0.33;
  const marketShare = 0.5 + (homeProb - awayProb) * 0.42;
  const handicapTilt = match.handicap ? -match.handicap * 0.035 : 0;
  const sideTilt = sideKey === "3" ? 0.035 : sideKey === "0" ? -0.035 : 0;
  return marketShare + handicapTilt + sideTilt;
}

function weightedAverage(values: Array<[number | undefined, number]>) {
  const valid = values.filter((item): item is [number, number] => typeof item[0] === "number" && Number.isFinite(item[0]));
  const weight = valid.reduce((sum, [, itemWeight]) => sum + itemWeight, 0);
  if (!weight) return undefined;
  return valid.reduce((sum, [value, itemWeight]) => sum + value * itemWeight, 0) / weight;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function roundXg(value: number) {
  return Math.round(value * 100) / 100;
}

function sortedByProbability(rows: ReturnType<typeof oddsTriplet>) {
  return [...rows].sort((a, b) => b.normalized - a.normalized);
}

function chooseGoals(totalExact: OddsMap): Pick {
  const top = topEntries(totalExact, 3);
  if (!top.length) return { label: "-" };
  const weighted = top.reduce((sum, [goals, odds]) => sum + Number(goals) / odds, 0);
  const weight = top.reduce((sum, [, odds]) => sum + 1 / odds, 0);
  const expected = weight > 0 ? weighted / weight : Number(top[0][0]);
  const label = expected >= 2.75 ? "偏大球" : expected <= 1.85 ? "偏小球" : "2-3球区间";
  return {
    label,
    odds: top[0][1],
    probability: 1 / top[0][1]
  };
}

function chooseScoreCandidates(scores: OddsMap, sideKey: string | undefined, goalLabel: string): Pick[] {
  const parsed = Object.entries(scores)
    .map(([label, odds]) => {
      const match = label.match(/^(\d+)-(\d+)$/);
      if (!match) return null;
      const home = Number(match[1]);
      const away = Number(match[2]);
      const total = home + away;
      const sideScore = sideFitScore(home, away, sideKey);
      const goalScore = goalFitScore(total, goalLabel);
      const marketScore = 1 / odds;
      return {
        label,
        odds,
        score: sideScore * 0.48 + goalScore * 0.32 + marketScore * 0.2
      };
    })
    .filter((item): item is { label: string; odds: number; score: number } => Boolean(item));

  return parsed
    .sort((a, b) => b.score - a.score || a.odds - b.odds)
    .slice(0, 4)
    .map(({ label, odds }) => ({ label, odds }));
}

function sideFitScore(home: number, away: number, sideKey: string | undefined) {
  if (sideKey === "3") {
    if (home > away) return 1;
    if (home === away) return 0.35;
    return 0;
  }
  if (sideKey === "1") {
    if (home === away) return 1;
    if (Math.abs(home - away) === 1) return 0.25;
    return 0;
  }
  if (sideKey === "0") {
    if (away > home) return 1;
    if (home === away) return 0.35;
    return 0;
  }
  return 0.5;
}

function goalFitScore(total: number, goalLabel: string) {
  if (goalLabel === "偏大球") {
    if (total >= 3 && total <= 4) return 1;
    if (total === 2 || total === 5) return 0.5;
    return 0.15;
  }
  if (goalLabel === "偏小球") {
    if (total <= 2) return 1;
    if (total === 3) return 0.45;
    return 0.1;
  }
  if (total === 2 || total === 3) return 1;
  if (total === 1 || total === 4) return 0.45;
  return 0.1;
}

function marketMovement(match: MatchItem) {
  const ouzhi = match.deep_market?.ouzhi;
  const yazhi = match.deep_market?.yazhi;
  const daxiao = match.deep_market?.daxiao;
  const hostOddsDown = Boolean(ouzhi && ouzhi.current[0] < ouzhi.opening[0]);
  const awayOddsDown = Boolean(ouzhi && ouzhi.current[2] < ouzhi.opening[2]);
  const drawOddsDown = Boolean(ouzhi && ouzhi.current[1] < ouzhi.opening[1]);
  const hostWaterUp = Boolean(yazhi && yazhi.current[0] > yazhi.opening[0]);
  const awayWaterDown = Boolean(yazhi && yazhi.current[2] < yazhi.opening[2]);
  const bigWaterUp = Boolean(daxiao && daxiao.current[0] > daxiao.opening[0]);
  const smallWaterDown = Boolean(daxiao && daxiao.current[2] < daxiao.opening[2]);
  const conflictCount = [hostOddsDown && hostWaterUp, awayOddsDown && awayWaterDown, drawOddsDown].filter(Boolean).length;
  return {
    hostOddsDown,
    awayOddsDown,
    drawOddsDown,
    hostWaterUp,
    awayWaterDown,
    bigWaterUp,
    smallWaterDown,
    conflictCount
  };
}

function assessRisk(margin: number, conflictCount: number, handicap: number | null): MatchAnalysis["risk"] {
  if (margin < 0.07 || conflictCount >= 2 || Math.abs(handicap || 0) >= 2) return "高";
  if (margin < 0.13 || conflictCount === 1) return "中";
  return "低";
}

function assessLevel(margin: number, risk: MatchAnalysis["risk"]): MatchAnalysis["level"] {
  if (risk === "低" && margin >= 0.18) return "强";
  if (risk === "高" || margin < 0.09) return "弱";
  return "中";
}

function buildSignals(
  match: MatchItem,
  primary: ReturnType<typeof oddsTriplet>[number] | undefined,
  handicap: ReturnType<typeof oddsTriplet>[number] | undefined,
  goals: Pick,
  movement: ReturnType<typeof marketMovement>,
  margin: number
) {
  const signals = [
    `胜平负最高隐含方向为 ${primary ? SIDE_NAME[primary.key] : "-"}，归一概率 ${primary ? pct(primary.normalized) : "-"}`,
    `方向优势差为 ${pct(margin)}，${margin >= 0.13 ? "主方向区分度尚可" : "三项分布偏接近"}`,
    `让球盘倾向 ${handicap ? `${formatHandicapText(match.handicap)} ${SHORT_SIDE_NAME[handicap.key]}` : "-"}`,
    `总进球倾向：${goals.label}`,
  ];

  if (movement.hostOddsDown) signals.push("欧赔主胜即时均值低于初盘，主队方向有降赔信号");
  if (movement.awayOddsDown) signals.push("欧赔客胜即时均值低于初盘，客队方向有降赔信号");
  if (movement.drawOddsDown) signals.push("平赔即时均值低于初盘，需要防平局分流");
  if (movement.hostWaterUp) signals.push("亚盘主水上调，主队让球打穿存在阻力");
  if (movement.smallWaterDown) signals.push("大小球小球水位下调，进球数上限需谨慎");
  return signals;
}

function buildSummary(
  match: MatchItem,
  primary: ReturnType<typeof oddsTriplet>[number] | undefined,
  handicap: ReturnType<typeof oddsTriplet>[number] | undefined,
  goals: Pick,
  topScores: Pick[],
  risk: MatchAnalysis["risk"],
  level: MatchAnalysis["level"],
  movement: ReturnType<typeof marketMovement>
) {
  const side = primary ? SIDE_NAME[primary.key] : "-";
  const hcap = handicap ? `${formatHandicapText(match.handicap)} ${SHORT_SIDE_NAME[handicap.key]}` : "-";
  const scoreText = topScores.length
    ? `分析比分参考 ${topScores.map((item) => item.label).join("、")}。`
    : "";
  const caution = movement.hostWaterUp || movement.drawOddsDown ? "盘口存在分歧，建议降低串关权重。" : "赔率结构相对顺，适合继续观察临场变化。";
  return `${match.home} vs ${match.away} 当前主结论为 ${side}，强度 ${level}、风险 ${risk}。让球方向参考 ${hcap}，进球数倾向 ${goals.label}。${scoreText}${caution}`;
}

function formatScoreSummary(scores: Pick[]) {
  return scores.length
    ? scores.map((item) => `${item.label}${item.odds ? `(${item.odds.toFixed(2)})` : ""}`).join("、")
    : "-";
}

function formatHandicapText(value: number | null) {
  if (value === null) return "让球";
  if (value > 0) return `受让${value}`;
  if (value < 0) return `让${Math.abs(value)}`;
  return "平手";
}
