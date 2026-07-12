<div align="center">

# Football Analyst Skill

### 可审计、可复盘的足球赛前概率分析系统

以中国竞彩市场为入口，融合数学模型、赔率结构、比赛情报与多源市场证据，输出赛果、让球、总进球和比分概率。

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2F855A)](LICENSE)
[![CI](https://github.com/tszming1021/football-analyst-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/tszming1021/football-analyst-skill/actions/workflows/ci.yml)
[![Repository](https://img.shields.io/badge/Repository-Private-24292F?logo=github)](https://github.com/tszming1021/football-analyst-skill)

**数据采集 · 概率建模 · 市场融合 · 风险控制 · 联网复核 · 赛后校准**

[快速开始](#快速开始) · [分析架构](#分析架构) · [模型体系](#模型体系) · [项目文档](#项目文档)

</div>

---

## 项目定位

Football Analyst Skill 是一套面向中国竞彩、世界杯及主要足球赛事的赛前研究工作流。它不依赖单一模型直接下结论，而是分别回答四个问题：

| 分析层 | 核心问题 | 主要输出 |
|---|---|---|
| 赛果 | 双方在常规时间内谁更可能取胜 | 胜、平、负概率 |
| 让球 | 热门方的优势是否足以覆盖当前让球 | 让胜、让平、让负概率 |
| 总球 | 比赛节奏与进球期望落在哪个区间 | 0 至 7+ 球概率 |
| 比分 | 哪些比分是主线，哪些是风险尾部 | Top 3、上沿与冷门比分 |

> 核心原则：赛果、让球、总球和比分必须分别建模。强队胜面高，不等于具备赢深条件。

## 核心能力

| 模块 | 能力 |
|---|---|
| 市场数据 | 500竞彩主表、欧赔、亚盘、大小盘、让球指数、比分指数与赔率变化 |
| 基本面 | 排名、近期状态、主客拆分、交锋、赛程、首发、伤停与战意 |
| 外部补源 | API-Football、Open-Meteo、Opta Analyst、Polymarket、OddsPortal及其他可选数据源 |
| 临场补源 | Flashscore首发/阵型/事件/技术统计，AiScore即时比分/射门/危险进攻/角球/部分赔率 |
| 数学模型 | proxy xG、Poisson、Dixon-Coles、Elo、凯利、EV与贝叶斯融合 |
| 深度判断 | LEG让球深度、比赛语境、比分矩阵约束与一致性检查 |
| 风险控制 | 数据完整度、偏差保护、串关相关性、赛前防泄漏与降级机制 |
| 复核闭环 | GPT联网事实核验、结构化报告、Brier Score、Log Loss与错误归因 |

## 分析架构

```mermaid
flowchart LR
    A["比赛与附件"] --> B["数据采集"]
    B --> C["事实与市场层"]
    C --> D["xG / Poisson / Dixon-Coles"]
    C --> E["500 / OddsPortal / Opta / Polymarket"]
    C --> L["Flashscore / AiScore"]
    D --> F["多源概率融合"]
    E --> F
    L --> G
    F --> G["赛果 / 让球 / 总球 / 比分"]
    G --> H["LEG与决策迭代"]
    H --> I["一致性与风险检查"]
    I --> J["GPT联网复核"]
    J --> K["报告与赛后校准"]
```

每次正式分析都保留数据截点、来源质量、有效权重、触发规则以及调整前后概率，便于复查而不是只保留最终结论。

## 模型体系

### 多源赛果融合

严格赛果模型将 Poisson、500市场、Opta模拟和 Polymarket 放在同一层一次性融合，避免先后顺序改变结果。基础权重会根据以下因素动态折扣并重新归一化：

- 数据新鲜度与样本完整度。
- 市场流动性、价差和成交质量。
- 不同市场之间的相关性，防止重复计票。
- 模型与市场的偏差幅度。
- 阵容、赛事阶段和比赛语境的可确认程度。

### 独立玩法模型

| 玩法 | 主要依据 |
|---|---|
| 赛果 | 预期进球、Poisson、去水市场概率、Opta与Polymarket |
| 让球 | 让球三向市场、LEG深度、净胜球矩阵与赢盘路径 |
| 总球 | 总进球分布、大小盘、天气、节奏与阵容结构 |
| 比分 | Dixon-Coles矩阵、赛果后验、总球约束与比分市场温和校正 |

GPT 联网复核和奇门辅助的直接概率权重均为 **0%**。它们用于核验事实、发现冲突和触发重算，不能直接覆盖数学模型。

完整权重、公式和动态折扣规则见 [PROJECT_INTRODUCTION.md](PROJECT_INTRODUCTION.md)。强制分析约束见 [PROJECT_IRON_RULES.md](PROJECT_IRON_RULES.md)。

## 快速开始

### 1. 获取项目

```bash
git clone git@github.com:tszming1021/football-analyst-skill.git
cd football-analyst-skill
```

### 2. 创建环境

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
cp .env.example .env
```

在 `.env` 中填写所需数据源密钥。所有数据源均为可选，但数据缺失会降低报告完整度和推荐等级。

### 3. 运行分析

单场分析：

```bash
python3 new_main.py --match "荷兰 vs 瑞典"
```

多场分析：

```bash
python3 new_main.py \
  --matches "荷兰 vs 瑞典,德国 vs 科特迪瓦,突尼斯 vs 日本"
```

安装后也可使用命令行入口：

```bash
football-analyst --match "荷兰 vs 瑞典"
football-review summary
football-worldcup Argentina France --season 2026
```

## 世界杯离线模型

历史比赛只在训练阶段读取，运行时加载紧凑 JSON 产物，降低上下文和磁盘开销。

```bash
python3 train_worldcup_model.py \
  --data-dir /path/to/football-historical-data \
  --output data/trained/worldcup_model.json \
  --cutoff-date 2026-06-01
```

训练产物包含国家队 Elo、攻防强度、近期表现、赛事权重、射手集中度和点球大战倾向。`--cutoff-date` 用于阻止目标日期之后的数据进入训练样本。

## 报告输出

标准报告包含：

- 数据来源、时间截点和完整度审计。
- 胜平负概率、核心方向与市场偏差。
- 让球三向概率、LEG深度与卡线风险。
- 精确总进球分布和大小球判断。
- 比分 Top 3、强队上沿路径和冷门保护。
- 数据冲突、阵容风险、天气影响与串关限制。
- GPT联网复核结论及需要重新计算的事实变化。

报告模板位于 [report_template_jingcai_multi_match.md](report_template_jingcai_multi_match.md)、[report_template_jingcai_qimen.md](report_template_jingcai_qimen.md) 和 [report_template_standard.md](report_template_standard.md)。多场竞彩报告优先使用 `report_template_jingcai_multi_match.md`。

## 项目结构

```text
football-analyst-skill/
├── core/                         # 采集、模型、融合、决策与报告核心
│   └── data_sources/            # 外部数据源适配器
├── data/
│   └── calibration/             # 稳定权重策略与决策迭代规则
├── scripts/                      # 日期批次采集、分析与报告脚本
├── tests/                        # 单元测试
├── new_main.py                   # 主分析入口
├── review_cli.py                 # 赛后复盘入口
├── worldcup_predictor.py         # 世界杯预测入口
├── train_worldcup_model.py       # 离线模型训练入口
├── PROJECT_IRON_RULES.md         # 不可绕过的分析铁律
└── PROJECT_INTRODUCTION.md       # 完整流程、权重与治理说明
```

更细的模块说明见 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)。

## 数据与安全

仓库默认排除以下本地内容：

- `.env` 与所有真实 API 密钥。
- PDF、XLS/XLSX、CSV及其他原始附件。
- SQLite、赔率快照、比赛批次数据与训练产物。
- 生成报告、音视频、缓存和本地上下文快照。

公开仓库只保留核心代码、模板、稳定策略和可复现说明。安全报告方式见 [SECURITY.md](SECURITY.md)。

## 测试

```bash
python3 -m compileall -q core new_main.py review_cli.py worldcup_predictor.py
python3 -m unittest discover -s tests -v
```

GitHub Actions 会在 Python 3.9 和 3.12 上执行相同检查。

## 项目文档

| 文档 | 内容 |
|---|---|
| [PROJECT_INTRODUCTION.md](PROJECT_INTRODUCTION.md) | 完整分析流程、分层权重和优化路线 |
| [PROJECT_IRON_RULES.md](PROJECT_IRON_RULES.md) | 正式分析必须遵守的铁律 |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 文件结构、模块职责和本地数据说明 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 开发、测试和提交约定 |
| [SECURITY.md](SECURITY.md) | 密钥管理与安全问题报告 |

## 免责声明

本项目仅用于数据研究、概率建模和赛后复盘，不构成投注建议，也不保证任何预测结果。使用者应自行判断风险，并遵守所在地法律法规。

---

<div align="center">

**让每个结论都能追溯到数据、权重和规则。**

</div>
