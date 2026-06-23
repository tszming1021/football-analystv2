# Contributing

感谢你改进这个项目。提交改动前，请遵循以下约定。

## 开发环境

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

## 提交要求

- 不提交 `.env`、API 密钥、浏览器会话或个人路径。
- 不提交原始 PDF/XLS、赔率快照、SQLite、生成报告和音视频。
- 新增模型逻辑时补充最小可复现测试。
- 概率调整必须能够说明输入、权重、触发规则和调整前后结果。
- 正式分析不得混入目标比赛开赛后的信息。

## Pull Request

PR 请说明问题、实现方式、验证命令和对模型输出的影响。涉及权重变化时，请附带样本外验证或赛后复盘依据。

