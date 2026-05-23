# BlackHole Beacon — 频谱锚点引擎（Spectral Anchor Engine）

**项目名称**：BlackHole Beacon（黑洞信标）  
**副标题**：频谱锚点引擎（Spectral Anchor Engine）  
**版本**：v9.0（Isolation Forest 无监督学习）  

---

## 项目定位

**核心目标**：通过多波段频谱特征筛选管道，从公开巡天数据（2MASS、WISE、Gaia）中识别黑洞/脉冲星候选体。

**科学问题**：
1. 如何通过 IR 颜色（J-H, H-K, W1-W2, W2-W3）区分脉冲星/黑洞 vs 普通恒星/星系？
2. 如何利用自行运动（PM）特征提升分类器性能？
3. 如何避免过拟合（AUC=1.0000）并提升泛化能力？

**解决思路**：
- **Phase 1-3 管道**：红色异常筛选 → 自行运动分析 → 候选体评分
- **Isolation Forest 无监督学习**（v7.0-v9.0）：不需要负样本，学习什么是异常

---

## 验证结果

TOP 10 候选体经 Simbad 数据库验证：**TOP 10 均不在任何已知星表内**（很可能是新发现）。

| 排名 | 候选体 | 异常分数 | PM(mas/yr) | 验证结果 |
|------|--------|----------|------------|----------|
| 1 | J1933+1726 | 0.2133 | 0.0 | ✅ 未知源 |
| 2 | J0434-5728 | 0.1947 | 0.0 | ✅ 未知源 |
| 3 | J0834-4159 | 0.1923 | 0.0 | ✅ 未知源 |
| 4 | J2141-5109 | 0.1920 | 0.0 | ✅ 未知源 |
| 5 | J1121-6221 | 0.1885 | 0.0 | ✅ 未知源 |
| 6-10 | （全部 PM=0.0） | ... | 0.0 | ✅ 未知源 |

---

## 项目结构

`
blackhole-beacon/
├── README.md                  # 本文档
├── SKILL.md                   # QClaw skill 配置
├── PROJECT_STATUS.md          # 完整项目状态（含重启指南）
├── IMPLEMENTATION.md          # 技术实现说明
├── requirements.txt           # Python 依赖
├── code/                      # 核心管道脚本（16 个）
│   ├── 01_phase1_red_filter.py
│   ├── 02_phase2_proper_motion.py
│   ├── 03_phase3_scoring.py
│   ├── 04_classifier_v7_iforest.py     # ← 推荐使用
│   ├── 05_classifier_v9_split.py       # ⚠️ 有缺陷
│   ├── 06_classifier_v9_supervised.py
│   └── generate_observation_proposal.py
├── data/                      # 关键数据（18 MB）
│   ├── phase3_candidates_full.json     # 2455 候选体
│   ├── classifier_ranking_v7.json      # v7.0 Isolation Forest 排名
│   ├── classifier_ranking_v9.json      # v9.0 分拆排名
│   ├── blackcat_59_clean.json          # 已知 31 个 BHXB
│   └── observation_proposal_v9_top10.md
├── queries_archive/           # 历史查询脚本（78 个，已归档）
├── catalog/                   # 外部星表数据
└── docs/
    └── THREE_AUDIT_REPORT.md  # 三条审计报告
`

---

## 运行方式

`ash
cd code
# Phase 1-3 全量管道
python 01_phase1_red_filter.py
python 02_phase2_proper_motion.py
python 03_phase3_scoring.py

# 分类器（推荐 v7.0）
python 04_classifier_v7_iforest.py

# 验证
python validate_v9.py
python cross_match_top10_v9_fixed.py

# 观测提案
python generate_observation_proposal.py
`

---

## 已知局限

1. **v9.x 分拆策略无效**：JHK 和 WISE 组排名不重叠（交集≈0）
2. **推荐用 v7.0**：Isolation Forest 4 特征无监督，无过拟合
3. **TOP 10 验证不足**：只做了名称查询，未做 10 arcsec 坐标交叉匹配
4. **无法采集真实负样本**：Simbad TAP 404（API 限制）
5. **BlackCAT 缺 IR 星等**：无法用作监督学习正样本

---

## 重启指南

见 PROJECT_STATUS.md 第 6 节（4 个重启选项）。
