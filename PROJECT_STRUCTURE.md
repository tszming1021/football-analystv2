# Project Structure

Last updated: 2026-06-24

## Quick Resume

On a new machine or a new Codex account, start with:

```text
读取 PROJECT_IRON_RULES.md、PROJECT_INTRODUCTION.md 和 PROJECT_STRUCTURE.md，然后继续项目。
```

## Keep Files

```text
README.md
PROJECT_STRUCTURE.md
PROJECT_IRON_RULES.md
PROJECT_INTRODUCTION.md
report_template_jingcai_qimen.md
report_template_jingcai_multi_match.md
report_template_standard.md
requirements.txt
skill.json
.env.example
```

Notes:

```text
.env contains local secrets and must never be committed.
report_template_jingcai_multi_match.md is the preferred template for multi-match Jingcai reports.
report_template_jingcai_qimen.md and report_template_standard.md are legacy/single-match report templates and must be preserved.
PROJECT_CONTEXT.md and CONTEXT_SNAPSHOT files are local project memory and are excluded from GitHub.
PROJECT_IRON_RULES.md contains mandatory analysis rules and must be read before any formal report.
```

## Core Pipeline

```text
core/workflow_coordinator.py
```

Main orchestration layer:

```text
data collection
math model
market signal
match context
handicap model
total-goals model
scoreline fusion model
LEG depth-check model
qimen auxiliary layer
LLM review
report rendering
post-match review storage
```

## Core Modules

```text
core/data_collector.py
```

Collects and merges API-Football, 500 local/deep data, weather and supplemental intelligence.

```text
core/jingcai_500_collector.py
core/data_sources/fivehundred_trade.py
```

500 source integration, including main trade table, score table, total-goals table and half-full table.

```text
core/math_models.py
core/probability_fusion.py
```

Poisson/Dixon-Coles model and probability calibration.

```text
core/context_models.py
```

Match context, handicap direction, total-goals distribution and scoreline fusion.

Important current logic:

```text
GoalsModel uses exact total-goal distribution: 0,1,2,3,4,5,6,7+.
ScorelineModel uses tiered score ranking:
- Top1/Top2 = conservative hit-rate layer
- Top3/Top5 = risk/upside layer
```

```text
core/leg_model.py
```

LEG depth-check model:

```text
L = market line and handicap-depth support
E = expected-goals and scoreline-depth support
G = game context, motivation, lineup/rotation and volatility
```

It answers:

```text
Does the favorite only have a win edge, or enough support to win deep?
```

```text
core/market_signal_model.py
core/odds_movement_analyzer.py
core/odds_history.py
```

Market-number strength, movement and history tracking.

```text
core/match_intelligence.py
core/supplemental_data.py
core/weather_context.py
```

Lineups, absences, motivation, tactical notes, travel/weather context.

```text
core/qimen_assistant.py
```

Low-weight qimen auxiliary risk layer.

```text
core/llm_analyzer.py
```

GPT/LLM review layer.

```text
core/report_renderer.py
```

Standard report rendering. Uses the preserved templates and model outputs.

```text
core/post_match_review.py
core/calibration_rules.py
core/model_consistency.py
```

Post-match review records and calibration rules.

```text
core/calibration_rules.py
- ProjectCalibrationRuleBook reads project calibration JSON files and emits calibration_report for the main workflow.
- Current active calibration sources:
  * data/calibration/jleague_20260606_rank_playoff_calibration.json
  * data/calibration/international_20260609_three_match_review.json

core/model_consistency.py
- ModelConsistencyChecker checks result, handicap, total-goals, scoreline and LEG alignment before report rendering.
- Output is saved as consistency_report and shown in the report.
```

## Data Directories

```text
data/
```

Persistent local data:

```text
data/odds_history.sqlite3
data/post_match_reviews.sqlite3
data/calibration/
data/jleague_20260606/
data/international_20260606/
data/international_20260608/
data/international_20260609/
data/trained/
data/worldcup_2026_api/
data/worldcup_2026_venues_weather/
```

These are local runtime data and should generally be preserved on the workstation, but they are excluded from GitHub. Only stable calibration policies are public.

## Utility Scripts

```text
parse_500_html.py
parse_deep_pages.py
parse_deep_pages_v2.py
parse_everything.py
render_jleague_report.py
review_cli.py
train_worldcup_model.py
worldcup_predictor.py
```

These are helper scripts for parsing, rendering, review and model training.

## Cleaned Report Outputs

Old generated reports were removed on 2026-06-08. Preserved templates:

```text
report_template_jingcai_qimen.md
report_template_jingcai_multi_match.md
report_template_standard.md
```

Removed old report artifacts:

```text
20260603分析报告5.md
6-3 赛果复盘.md
gpt_web_review_20260604.md
multi_match_report_20260606_121104.md
multi_match_report_20260606_docx_api_122445.md
multi_match_report_20260606_docx_api_supplemented.md
multi_match_report_20260606_pdf_trade_api_complete.md
reports_colombia_vs_costa_rica_20260602_112632.json
reports_colombia_vs_costa_rica_20260602_112632.md
reports_colombia_vs_costa_rica_20260602_112920.json
reports_colombia_vs_costa_rica_20260602_112920.md
```

## Current Cleanup Rule

Report outputs can be deleted after review, but keep:

```text
report_template_*.md
PROJECT_CONTEXT.md
CONTEXT_HANDOFF.md
PROJECT_STRUCTURE.md
README.md
data/
core/
.env.example
requirements.txt
skill.json
```
