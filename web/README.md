# 足球分析台 Web MVP

这是项目的网站第一版，先完成免费 MVP 闭环：

```text
500 网抓取 -> 本地 JSON / Supabase -> 网页展示 -> 手动或定时刷新
```

## 本地运行

```bash
cd web
npm install
npm run dev
```

打开：

```text
http://127.0.0.1:3000
```

## 构建检查

```bash
npm run build
npm audit --audit-level=moderate
```

## 手动刷新

网页首页右上方的“刷新”按钮会调用：

```text
POST /api/admin/refresh
```

该接口会运行仓库根目录下的 Python 抓取脚本：

```bash
python3 scripts/fetch_500_on_sale.py --with-deep
```

刷新成功后会覆盖：

```text
web/data/current_matches.json
```

## 自动定时抓取

Vercel Cron 配置在：

```text
web/vercel.json
```

当前配置：

```json
{
  "crons": [
    {
      "path": "/api/cron/fetch-matches",
      "schedule": "0 4 * * *"
    }
  ]
}
```

Vercel Cron 使用 UTC 时间，`0 4 * * *` 对应北京时间每天 12:00。

本地测试定时接口：

```bash
curl http://127.0.0.1:3000/api/cron/fetch-matches
```

如果在 Vercel 环境变量里设置 `CRON_SECRET`，接口会要求请求头：

```text
Authorization: Bearer <CRON_SECRET>
```

## 后续上线注意

当前刷新接口适合本地 MVP。上 Vercel 后不应长期写本地 JSON，因为 Vercel 文件系统不是持久数据库。下一步应把刷新结果写入 Supabase Free 或 Neon Free。

## 接入 Supabase Free

1. 在 Supabase 创建免费项目。
2. 打开 SQL Editor，执行 `supabase/schema.sql`。
3. 复制 `.env.example` 为 `.env.local`，填入 Supabase 项目 URL 和 service role key。
4. 重启开发服务器，再点击首页“刷新”。

配置 `NEXT_PUBLIC_SUPABASE_URL` 和 `SUPABASE_SERVICE_ROLE_KEY` 后，每次抓取会保存：

- `scrape_runs`：每次抓取的时间、来源和统计。
- `matches`：比赛最新状态和完整原始数据。
- `odds_snapshots`：每次抓取的赔率快照，便于以后画赔率变化。
- `match_reports`：分析方向、预估 xG、分析比分 Top3 和完整报告。

未配置 Supabase 时，网站继续使用 `data/current_matches.json`，适合开发阶段。
