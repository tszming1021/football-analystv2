import Link from "next/link";
import { Activity, Clock3, Database, RefreshCw, ShieldCheck } from "lucide-react";
import { RefreshButton } from "../components/RefreshButton";
import { AuthButton } from "../components/AuthButton";
import { formatHandicap, getPayload, oddsTriplet, pct, strongestSide } from "../lib/data";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const payload = await getPayload();
  const leagues = Array.from(new Set(payload.matches.map((item) => item.league))).join(" / ");

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Football Analyst</p>
          <h1>足球分析台</h1>
        </div>
        <div className="topbar-actions">
          <div className="status-pill">
            <ShieldCheck size={18} />
            <span>总场数 {payload.counts.included}</span>
          </div>
          <AuthButton />
        </div>
      </header>

      <div className="toolbar">
        <RefreshButton />
      </div>

      <section className="metrics-grid" aria-label="今日概览">
        <Metric icon={<Database size={18} />} label="抓取场次" value={`${payload.counts.included}`} />
        <Metric icon={<Activity size={18} />} label="覆盖赛事" value={leagues || "-"} />
        <Metric icon={<Clock3 size={18} />} label="更新时间" value={new Date(payload.fetched_at).toLocaleString("zh-CN")} />
        <Metric icon={<RefreshCw size={18} />} label="异常记录" value={`${Object.keys(payload.errors).length}`} />
      </section>

      <section className="match-table-section">
        <div className="section-head">
          <h2>比赛列表</h2>
          <span>{payload.source_http_date || payload.source_url}</span>
        </div>
        <div className="table-wrap">
          <table className="match-table">
            <thead>
              <tr>
                <th>场次</th>
                <th>联赛</th>
                <th>时间</th>
                <th>对阵</th>
                <th>让球</th>
                <th>胜平负</th>
                <th>倾向</th>
              </tr>
            </thead>
            <tbody>
              {payload.matches.map((match) => {
                const triplet = oddsTriplet(match.one_x_two);
                return (
                  <tr key={match.fixture_page_id}>
                    <td>
                      <Link href={`/matches/${match.fixture_page_id}`} className="match-link">
                        {match.match_num}
                      </Link>
                    </td>
                    <td>{match.league}</td>
                    <td>{match.kickoff}</td>
                    <td>
                      <div className="teams">
                        <strong>{match.home}</strong>
                        <span>vs</span>
                        <strong>{match.away}</strong>
                      </div>
                    </td>
                    <td>{formatHandicap(match.handicap)}</td>
                    <td>
                      <div className="odds-row">
                        {triplet.map((item) => (
                          <span key={item.key}>{item.label} {item.odds.toFixed(2)}</span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <span className="signal">{strongestSide(match.one_x_two)} {pct(Math.max(...triplet.map((item) => item.normalized)))}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

function Metric({
  icon,
  label,
  value
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="metric">
      <div className="metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
