# Odds Movement Optimization Plan

Last updated: 2026-07-02

## Purpose

新增 OddsPortal、Flashscore、AiScore 后，赔率变化不直接覆盖现有模型。第一版必须以影子模式运行：只输出信心、风险标签、报告审计和复盘归因，等复盘样本达标后再进入概率微调。

## Phase Gate

项目以 `data/calibration/odds_movement_phase_gate.json` 为准。

### Phase 1: Shadow Mode

- 允许：盘口变化标签、信心说明、风险警报、报告审计、赛后复盘特征。
- 禁止：直接修改胜平负、让球、总球均值、比分概率。
- 报告必须写明：赔率变化层当前为 `phase1_shadow_mode`。

### Phase 2: Limited Probability Delta

只有满足以下条件才能进入：

- 已复盘至少30场。
- 至少覆盖5个不同比赛批次。
- 已统计赔率变化标签命中率、误报率、Brier变化、让球方向变化、总球方向变化。
- Brier或让球方向不能变差。
- 必须人工确认并更新 `odds_movement_phase_gate.json`。

### Phase 3: Full Model Integration

只有满足以下条件才能进入：

- 已复盘至少100场。
- 至少覆盖15个不同比赛批次。
- Brier有稳定正向改善。
- 不同赛事类型下表现稳定。
- 必须更新规则库和报告审计模板。

## Required Implementation Steps

1. 新增统一赔率快照格式：`core/odds_snapshot.py`。
2. 新增赔率历史库：`data/odds_history/{match_key}/snapshots.jsonl`。
3. 扩展500抓取器，每次正式分析自动追加快照。
4. 新增OddsPortal适配器，输出成功/失败审计。
5. 新增AiScore赔率字段适配，临场只作为补源。
6. 新增 `core/odds_movement_features.py`。
7. 新增 `core/market_intent_classifier.py`。
8. 新增 `core/odds_movement_model.py`。
9. 第一版接入报告和复盘，不接入最终概率。
10. 复盘样本达标后，再按phase gate决定是否允许概率微调。

## Report Requirement

正式报告必须输出：

- 500赔率变化状态。
- OddsPortal赔率变化状态。
- AiScore临场赔率状态。
- 快照数量和最新快照时间。
- 跨市场一致性。
- 公司分歧。
- 当前phase gate结论。

## Non-Negotiable Rule

不要因为聊天上下文里说过“以后再做”就自动升级模型。只有 `odds_movement_phase_gate.json` 的 `current_phase` 允许，且复盘指标达标，才可以进入下一阶段。
