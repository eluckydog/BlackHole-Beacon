---
name: BlackHole Beacon
description: "多波段频谱锚点引擎：从公开巡天数据（2MASS/WISE/Gaia）中识别黑洞/脉冲星候选体。Phase 1-3规则管道 + Isolation Forest无监督分类器。输出：2455候选体排名 + TOP10观测提案。"
version: 9.0.0
license: MIT
homepage: https://github.com/eluckydog/spectral-anchor-engine
---

# BlackHole Beacon — 频谱锚点引擎

## 项目目标

从 2529 个天文锚点中，用机器学习和多波段光谱分析找出最可能的**黑洞 X 射线双星（BHXB）候选体**或**脉冲星**。最终输出：排名靠前的候选体 + 观测提案。

## 触发词

用户提及以下内容时触发此 skill：
- "黑洞候选体""BHXB""频谱锚点"
- "Isolation Forest""无监督分类""IR 颜色"
- "相红线""红色异常""自行运动≈0"
- "Phase 1-3""2455 候选体"
- "观测提案""TOP 10"
- "blackhole-beacon""spectral-anchor-engine"

**不触发**：
- 黑洞自旋/霍金辐射/热力学（走 blackhole-spin-pi）
- 一般性天体物理问题（不涉及候选体搜索的）
- 食双星分析（走 eclipsing-beats）

## 管道结构

```
输入：2529 锚点（Gaia/2MASS/WISE 交叉匹配）
  │
  ▼
Phase 1：红色异常筛选 ─── 1482 候选体
  │                      （IR 颜色阈值：H-K > 0.3, J-H > 0.5）
  ▼
Phase 2：自行运动/变源分析 ─── 258 候选体（PM>0）
  │                      （PM 最高 230 mas/yr）
  ▼
Phase 3：候选体评分 ─── 2455 候选体完整排名
  │                      （TOP1: J1822-4209, 14.0 分）
  ▼
Isolation Forest v7.0 ─── 异常分数排名（4 IR 颜色）
  │                      （无监督，无过拟合）
  ▼
TOP 10 候选体 ─── 验证（不在任何已知目录）→ 观测提案
```

## 核心文件

| 文件 | 功能 |
|------|------|
| `code/01_phase1_red_filter.py` | Phase 1：红色异常筛选 |
| `code/02_phase2_proper_motion.py` | Phase 2：自行运动分析 |
| `code/03_phase3_scoring.py` | Phase 3：候选体评分 |
| `code/04_classifier_v7_iforest.py` | Isolation Forest v7.0（推荐） |
| `code/05_classifier_v9_split.py` | v9.0 分拆 JHK/WISE（⚠️ 交集=0） |
| `code/06_classifier_v9_supervised.py` | v9.0 监督学习版本 |
| `code/generate_observation_proposal.py` | 生成观测提案 |
| `code/cross_match_top10_v9_fixed.py` | 坐标交叉匹配验证 |
| `code/validate_v9.py` | 验证 TOP 10 是否已知 |

## 关键数据

| 文件 | 说明 |
|------|------|
| `data/phase3_candidates_full.json` | 2455 候选体（Phase 1-3 输出） |
| `data/classifier_ranking_v7.json` | v7.0 Isolation Forest 排名 |
| `data/classifier_ranking_v9.json` | v9.0 分拆排名 |
| `data/blackcat_59_clean.json` | 已知 31 个 BHXB |
| `data/known_pulsars_features.json` | 10 个已知脉冲星特征 |
| `data/observation_proposal_v9_top10.md` | TOP 10 观测提案 |

## 已知局限

1. **v9.x 分拆策略无效**：JHK 和 WISE 组排名不重叠（交集≈0）
2. **推荐用 v7.0**：Isolation Forest 4 特征无监督，无过拟合
3. **TOP 10 验证不足**：只做了名称查询，未做 10 arcsec 坐标交叉匹配
4. **P1 阻塞**：无法稳定采集真实负样本（Simbad TAP 404）
5. **BlackCAT 缺 IR 星等**：无法用作监督学习正样本

## 运行方式

```bash
# 全量管道（重新跑 Phase 1-3）
python code/01_phase1_red_filter.py —candidates anchors.json
python code/02_phase2_proper_motion.py
python code/03_phase3_scoring.py

# 分类器
python code/04_classifier_v7_iforest.py  # 推荐

# 验证
python code/validate_v9.py
python code/cross_match_top10_v9_fixed.py

# 提案
python code/generate_observation_proposal.py
```

## 重启指南

见 `PROJECT_STATUS.md` 第 6 节（4 个重启选项）。
