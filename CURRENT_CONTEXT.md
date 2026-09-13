# Current Context Snapshot

Updated: 2026-09-13

## Repository

- Local path: `/Users/jamesm/Desktop/football-analystv2`
- Remote: `git@github.com:tszming1021/football-analystv2.git`
- Branch: `main`
- Latest pushed commit: `5859af7 Update README for odds-driven workflow`

## User Direction

The project should be refocused around odds-driven football analysis:

1. Audit the repository for leaked API keys or tokens and remove any real secrets.
2. Remove the xG/proxy xG analysis layer.
3. Keep the core modeling stack focused on Elo, Poisson, EV/Kelly and LEG.
4. Make odds data the primary evidence source.
5. Use model outputs to cross-check the market, then produce a final conclusion only after explaining alignment, conflict or rejection.

## Completed Changes

- Cloned `tszming1021/football-analystv2` into the local workspace.
- Confirmed no real `.env` file, API key, GitHub token, OpenAI key, Anthropic key, or common secret pattern was present in the repository.
- Removed the active xG/proxy xG path from the main Python workflow.
- Deleted the xG proxy model and TheStatsAPI xG source adapter:
  - `core/xg_proxy_model.py`
  - `core/data_sources/thestatsapi.py`
- Removed xG/proxy xG from `core/__init__.py`, `core/data_collector.py`, `core/source_registry.py`, `core/workflow_coordinator.py`, `core/leg_model.py`, `core/report_renderer.py`, report templates and the web UI.
- Reworked `WorkflowCoordinator` so Poisson lambda comes from:
  - recent goals for/against and home/away splits,
  - ClubElo where available,
  - market-implied 1X2 probabilities,
  - total-goals odds and score-market calibration.
- Reworked LEG so the E layer uses odds total, Poisson lambda, score-market space and final goals distribution, not xG.
- Updated the web app from an xG panel/database shape to Poisson lambda fields:
  - `analysis.poisson`
  - `lambda_home`
  - `lambda_away`
  - `lambda_total`
- Updated README to describe the new odds-first workflow and explicitly state that xG/proxy xG has been removed.
- Updated package metadata from `football-analyst-skill` to `football-analystv2`.

## Current Analysis Policy

Formal analysis should follow this order:

1. Read and dewater odds first: 1X2, handicap 3-way, Asian handicap, total goals, score odds and odds movement.
2. Build independent Elo/Poisson prior from team history and available rating data.
3. Compare model prior with market probabilities.
4. If model-market deviation is material, lower confidence, protect the opposite side or reject the bet rather than force a high-confidence pick.
5. Use EV/Kelly only after market/model consistency checks.
6. Use LEG to decide whether a favorite has enough depth to cover the handicap.
7. Report the final pick with a clear explanation of market evidence, model agreement/conflict, risk and downgrade triggers.

## Verification Already Run

Python:

```bash
python3 -m compileall -q core new_main.py review_cli.py worldcup_predictor.py scripts/analyze_worldcup_0620_strict.py scripts/analyze_worldcup_0620_strict_1847.py
python3 -m unittest discover -s tests -v
```

Result: compile passed; 4 tests passed.

Web:

```bash
cd web
npm ci
npm run build
```

Result: Next.js production build passed. `npm ci` reported 3 high severity vulnerabilities; no automatic `npm audit fix --force` was run because it may introduce dependency churn.

## Git History

- `5859af7 Update README for odds-driven workflow`
- `4ee3adc Refocus analysis on odds-driven modeling`
- `7bbb47a add Vercel noon backup cron`

## Notes For Future Work

- Several older report-generation scripts and archived markdown reports still contain historical xG wording because they represent previous generated outputs. The active core workflow and web UI no longer use or display xG.
- `web/node_modules/` may exist locally after verification and is ignored by git.
- If database migrations are used in production, ensure existing `xg_*` columns are migrated or mapped to the new `lambda_*` columns before deploying the web app against an existing Supabase database.
