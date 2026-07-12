import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, BarChart3, Goal, LineChart, Sigma, ShieldAlert, Target, Trophy } from "lucide-react";
import { analyzeMatch } from "../../../lib/analysis";
import { formatHandicap, getMatch, getMatches, oddsTriplet, pct, topEntries } from "../../../lib/data";
import { canViewMatch } from "../../../lib/supabase/server";
import type { DeepMarket, OddsMap } from "../../../lib/types";

export const dynamic = "force-dynamic";

export async function generateStaticParams() {
  const matches = await getMatches();
  return matches.map((match) => ({ id: match.fixture_page_id }));
}

export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const match = await getMatch(id);
  if (!match) notFound();
  const matches = await getMatches();
  const access = await canViewMatch(match.fixture_page_id, matches[0]?.fixture_page_id);
  if (!access.allowed) return <LockedMatch match={match} authenticated={access.authenticated} />;

  const nspf = oddsTriplet(match.one_x_two);
  const spf = oddsTriplet(match.handicap_three_way);
  const analysis = analyzeMatch(match);

  return (
    <main className="shell">
      <header className="detail-head">
        <Link href="/" className="back-link">
          <ArrowLeft size={18} />
          返回
        </Link>
        <div className="match-title-block">
          <p className="eyebrow">{match.match_num} · {match.league} · {match.kickoff}</p>
          <h1>{match.home} <span>vs</span> {match.away}</h1>
        </div>
        <div className="status-pill">
          <Trophy size={18} />
          <span>让球 {formatHandicap(match.handicap)}</span>
        </div>
      </header>

      <section className="analysis-hero">
        <div className="analysis-main">
          <div className="panel-head">
            <Target size={18} />
            <h2>分析结论</h2>
          </div>
          <p>{analysis.summary}</p>
          <div className="recommend-grid">
            <Recommendation label="主方向" value={analysis.primary.label} meta={formatPickMeta(analysis.primary)} />
            <Recommendation label="让球方向" value={analysis.handicap.label} meta={formatPickMeta(analysis.handicap)} />
            <Recommendation label="进球数" value={analysis.goals.label} meta={formatPickMeta(analysis.goals)} />
            <Recommendation label="分析比分Top3" value={analysis.scoreSummary} meta="综合方向/进球数/比分盘" />
          </div>
        </div>
        <div className="analysis-side">
          <div className="panel-head">
            <ShieldAlert size={18} />
            <h2>关键信号</h2>
          </div>
          <ul>
            {analysis.signals.map((signal) => (
              <li key={signal}>{signal}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="detail-grid">
        <OddsPanel title="胜平负" icon={<BarChart3 size={18} />} rows={nspf} />
        <OddsPanel title="让球胜平负" icon={<LineChart size={18} />} rows={spf} />
        <XgPanel home={match.home} away={match.away} xg={analysis.xg} />
        <DeepPanel title="亚盘均值" market={match.deep_market?.yazhi} labels={["主水", "盘口", "客水"]} />
        <DeepPanel title="大小球均值" market={match.deep_market?.daxiao} labels={["大水", "盘口", "小水"]} />
        <ScorePanel values={analysis.scoreCandidates} />
        <DeepPanel title="欧赔均值" market={match.deep_market?.ouzhi} labels={["胜", "平", "负"]} />
        <CompactMarket title="半全场" icon={<LineChart size={18} />} values={match.half_full} limit={9} />
        <CompactMarket title="总进球" icon={<Goal size={18} />} values={match.total_exact} limit={8} />
      </section>
    </main>
  );
}

function LockedMatch({ match, authenticated }: { match: { match_num: string; league: string; kickoff: string; home: string; away: string }; authenticated: boolean }) {
  return (
    <main className="shell">
      <header className="detail-head">
        <Link href="/" className="back-link"><ArrowLeft size={18} /> 返回</Link>
        <div className="match-title-block">
          <p className="eyebrow">{match.match_num} · {match.league} · {match.kickoff}</p>
          <h1>{match.home} <span>vs</span> {match.away}</h1>
        </div>
      </header>
      <section className="locked-panel">
        <ShieldAlert size={34} />
        <h2>{authenticated ? "这场比赛暂未开通" : "请先注册或登录"}</h2>
        <p>{authenticated ? "当前账号已开放第一场比赛，其他比赛需要管理员授权。" : "注册后可查看第一场比赛的完整分析，其他比赛需要管理员授权。"}</p>
        {authenticated ? <p className="contact-note">请联系管理员开通本场比赛权限。</p> : <Link href="/login" className="primary-button">邮箱注册 / 登录</Link>}
        <div className="admin-contact">
          <p>添加管理员 QQ 申请开通</p>
          <img src="/admin-qq-qr.jpg" alt="管理员 QQ 二维码" />
        </div>
      </section>
    </main>
  );
}

function Recommendation({ label, value, meta }: { label: string; value: string; meta: string }) {
  return (
    <div className="recommend-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <em>{meta}</em>
    </div>
  );
}

function ScorePanel({ values }: { values: { label: string; odds?: number }[] }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <Goal size={18} />
        <h2>分析比分Top3</h2>
      </div>
      <div className="chip-grid">
        {values.slice(0, 3).map((item) => (
          <span className="market-chip highlight" key={item.label}>
            <strong>{item.label}</strong>
            <em>{item.odds?.toFixed(2) || "-"}</em>
          </span>
        ))}
      </div>
    </div>
  );
}

function XgPanel({
  home,
  away,
  xg
}: {
  home: string;
  away: string;
  xg: { home: number; away: number; total: number; note: string };
}) {
  return (
    <div className="panel">
      <div className="panel-head">
        <Sigma size={18} />
        <h2>预估 xG</h2>
      </div>
      <div className="xg-grid">
        <div className="xg-total">
          <span>总 xG</span>
          <strong>{xg.total.toFixed(2)}</strong>
        </div>
        <div className="xg-row">
          <span>{home}</span>
          <strong>{xg.home.toFixed(2)}</strong>
        </div>
        <div className="xg-row">
          <span>{away}</span>
          <strong>{xg.away.toFixed(2)}</strong>
        </div>
        <em>{xg.note}</em>
      </div>
    </div>
  );
}

function OddsPanel({
  title,
  icon,
  rows
}: {
  title: string;
  icon: React.ReactNode;
  rows: ReturnType<typeof oddsTriplet>;
}) {
  return (
    <div className="panel">
      <div className="panel-head">
        {icon}
        <h2>{title}</h2>
      </div>
      <div className="prob-list">
        {rows.map((row) => (
          <div className="prob-row" key={row.key}>
            <div>
              <strong>{row.label}</strong>
              <span>{row.odds.toFixed(2)}</span>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: pct(row.normalized) }} />
            </div>
            <em>{pct(row.normalized)}</em>
          </div>
        ))}
      </div>
    </div>
  );
}

function DeepPanel({
  title,
  market,
  labels
}: {
  title: string;
  market?: DeepMarket;
  labels: string[];
}) {
  return (
    <div className="panel">
      <div className="panel-head">
        <LineChart size={18} />
        <h2>{title}</h2>
      </div>
      {market ? (
        <table className="mini-table">
          <thead>
            <tr>
              <th>指标</th>
              <th>初盘</th>
              <th>即时</th>
              <th>变化</th>
            </tr>
          </thead>
          <tbody>
            {labels.map((label, index) => {
              const opening = market.opening[index];
              const current = market.current[index];
              return (
                <tr key={label}>
                  <td>{label}</td>
                  <td>{formatNumber(opening)}</td>
                  <td>{formatNumber(current)}</td>
                  <td className={current - opening >= 0 ? "up" : "down"}>{formatDelta(current - opening)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <p className="empty">暂无数据</p>
      )}
    </div>
  );
}

function CompactMarket({
  title,
  icon,
  values,
  limit
}: {
  title: string;
  icon: React.ReactNode;
  values: OddsMap;
  limit: number;
}) {
  return (
    <div className="panel">
      <div className="panel-head">
        {icon}
        <h2>{title}</h2>
      </div>
      <div className="chip-grid">
        {topEntries(values, limit).map(([key, value]) => (
          <span className="market-chip" key={key}>
            <strong>{key}</strong>
            <em>{value.toFixed(2)}</em>
          </span>
        ))}
      </div>
    </div>
  );
}

function formatNumber(value: number | undefined): string {
  return typeof value === "number" ? value.toFixed(3).replace(/0$/, "").replace(/0$/, "") : "-";
}

function formatDelta(value: number): string {
  if (!Number.isFinite(value)) return "-";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(3).replace(/0$/, "").replace(/0$/, "")}`;
}

function formatPickMeta(pick: { odds?: number; probability?: number }) {
  const parts = [];
  if (typeof pick.odds === "number") parts.push(`赔率 ${pick.odds.toFixed(2)}`);
  if (typeof pick.probability === "number") parts.push(`概率 ${pct(pick.probability)}`);
  return parts.join(" · ") || "规则判断";
}
