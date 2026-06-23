# Runtime Data

`data/` 用于本地赔率快照、比赛附件解析结果、SQLite 复盘库和训练产物。除下列稳定配置外，内容默认不进入 Git：

- `calibration/decision_iteration_rules.json`
- `calibration/multi_source_weight_policy.json`

世界杯训练产物可在本机生成：

```bash
python3 train_worldcup_model.py \
  --data-dir /path/to/football-historical-data \
  --output data/trained/worldcup_model.json
```

这些文件可能包含第三方数据、个人绝对路径或大体积结果，不应直接提交到公共仓库。

