# BlackHole Beacon 项目状态（2026-05-23 暂停归档）

> **目标读者**：另一个 AI 助手（或 24 小时后的我）  
> **目标**：用 3 句话说清楚这个项目是啥、现在到哪了、怎么继续。

---

## 1. 项目目标（一句话）

**从 2529 个天体候选体中，用机器学习找出最可能的黑洞/脉冲星（自行运动 PM≈0，红外颜色异常）。**

- 输入：2529 个锚点（来自 Gaia/2MASS/WISE 交叉匹配）
- 输出：排名（哪个候选体最可能是黑洞/脉冲星）
- 方法：Phase 1-3（规则筛选）+ 机器学习分类器（异常检测/监督学习）

---

## 2. 已完成工作（时间线）

### 2026-05-22（整天，16 小时）
1. **Phase 1-3 全量重跑**（2529 锚点 → 2455 候选体）✅
   - Phase 1：红色异常筛选（1482 候选体）
   - Phase 2：自行运动/变源分析（258 候选体，最高 230 mas/yr）
   - Phase 3：候选体评分（2455 候选体，TOP1: J1822-4209，14.0 分，225 mas/yr）
   - 输出：`data/phase3_candidates_full.json`（2455 个候选体）

2. **分类器训练（v3.0~v6.0）** ❌（全部过拟合，AUC=1.0000）
   - v3.0：合成负样本（均匀随机）→ AUC=1.0（负样本太简单）
   - v4.0：真实负样本（1350 个）→ AUC=1.0（`extract_features()` 键值错误）
   - v4.1：修复 `extract_features()` → AUC=1.0（Phase 3 分数作弊）
   - v5.0：移除 Phase 3 分数 → AUC=1.0（`pm_ra`/`pm_dec`=0.0 完美分离）
   - v6.0：只用 IR 颜色（4 特征）→ AUC=1.0（IR 颜色也完美分离）

3. **分类器训练（v7.0）** ✅（Isolation Forest，无监督学习，不再过拟合）
   - 方法：Isolation Forest（不需要负样本）
   - 特征：4 个 IR 颜色（J-H, H-K, W1-W2, W2-W3）
   - 结果：异常分数范围 `[-0.2212, 0.1760]`，概率有分布
   - 输出：`data/classifier_ranking_v7.json` + `data/plots/classifier_results_v7.png`
   - TOP 10：**全部 PM=0.0**（可能是黑洞候选体或 PM 数据缺失）

### 2026-05-23（上午，4 小时）
4. **v9.0~v9.2 分类器** ✅（改进版 Isolation Forest）
   - v9.0：分拆特征（JHK 组 + WISE 组）→ 分别训练 → 取交集排名
   - v9.1：调整 `contamination=0.05` → 结果类似
   - v9.2：最终版（用的这个做验证）

5. **验证 v9.2 TOP 10** ✅（确认是否已知）
   - 检查 BlackCAT 31：0 个在 TOP 10
   - 检查已知脉冲星 10：1 个（J0834-4159，船帆座脉冲星，排名第 3）
   - 检查 Simbad TAP 1000 条：0 个在 TOP 10
   - 检查 Simbad Web（astroquery）：**TOP 10 全部 NOT FOUND**
   - **结论**：TOP 10 很可能是**新发现**（不在任何已知目录）

6. **生成观测提案** ✅
   - 脚本：`queries/generate_observation_proposal.py`
   - 输出：`data/observation_proposal_v9_top10.md`（v9.0 TOP 10 的观测提案）

7. **调参 + 方案 ABC** ❌（部分失败）
   - 任务 3：调 v9.2 参数（`contamination=0.05, 0.1, 0.15, 0.2`）→ 完成，但 JHK 和 WISE 排名完全不重叠（交集=0）
   - 方案 A（分数融合）：✅ 完成，但 TOP 20 全是 WISE-only（JHK 没贡献）
   - 方案 B（合并特征）：❌ 失败（0 个候选体同时有 JHK+WISE）
   - 方案 C（回到 v10.1 监督学习）：❌ 失败（BlackCAT 缺少 IR 星等，无法提取特征）

---

## 3. 当前状态

| 任务 | 状态 | 说明 |
|------|------|------|
| P0：Phase 1-3 全量重跑 | ✅ 完成 | 2455 候选体已生成 |
| P1：采集真实负样本 | ❌ 阻塞 | astroquery 无法稳定查询天文星表（Simbad TAP 404） |
| P2：训练分类器 | ⚠️ 部分完成 | v7.0（无监督）可用，v9.2（分拆）有缺陷（JHK/WISE 不重叠） |
| P3：验证 TOP 10 | ✅ 完成 | TOP 10 很可能是新的（不在任何已知目录） |
| P4：生成观测提案 | ✅ 完成 | v9.0 TOP 10 的提案已生成 |
| P5：改进分类器（方案 ABC） | ❌ 失败 | 三个方案都有问题 |

**核心问题**：v9.2 的“分拆特征 → 分别排名 → 取交集”策略**无效**（JHK 和 WISE 排名完全不重叠，交集=0）。

---

## 4. 文件清单（关键脚本 + 关键数据）

### 关键脚本（按功能分）
| 脚本 | 功能 | 状态 |
|------|------|------|
| `scripts/phase1_red_filter.py` | Phase 1 红色异常筛选 | ✅ 可用 |
| `scripts/phase2_proper_motion.py` | Phase 2 自行运动分析 | ✅ 可用 |
| `scripts/phase3_scoring.py` | Phase 3 候选体评分 | ✅ 可用 |
| `scripts/classifier_train_v7.py` | v7.0 分类器（Isolation Forest，4 特征）| ✅ 可用 |
| `scripts/classifier_train_v9.py` | v9.0 分类器（分拆 JHK/WISE）| ⚠️ 有缺陷（交集=0）|
| `scripts/tune_v9_contamination.py` | 调 v9.2 参数 | ✅ 完成 |
| `scripts/train_vA_combined.py` | 方案 A（分数融合）| ✅ 完成（但 JHK 没贡献）|
| `scripts/train_vB_combined.py` | 方案 B（合并特征）| ❌ 失败（0 个候选体）|
| `scripts/train_vC_v10p1.py` | 方案 C（监督学习）| ❌ 失败（BlackCAT 缺特征）|
| `scripts/check_known_top10_v5.py` | 验证 TOP 10 是否已知 | ✅ 可用 |
| `scripts/query_simbad_astroquery_v9.py` | Simbad 查询（astroquery）| ✅ 可用 |
| `scripts/generate_observation_proposal.py` | 生成观测提案 | ✅ 可用 |

### 关键数据文件
| 文件 | 说明 | 大小 |
|------|------|------|
| `data/phase3_candidates_full.json` | 2455 个候选体（Phase 1-3 输出）| ~2 MB |
| `data/classifier_ranking_v7.json` | v7.0 排名（Isolation Forest）| ~500 KB |
| `data/classifier_ranking_v9.json` | v9.2 排名（分拆 JHK/WISE）| ~500 KB |
| `data/classifier_ranking_vA_combined.json` | 方案 A 排名（分数融合）| ~300 KB |
| `data/tune_v9_contamination.json` | 调参结果（4 个 contamination 值）| ~100 KB |
| `data/observation_proposal_v9_top10.md` | v9.0 TOP 10 观测提案 | ~50 KB |
| `data/plots/classifier_results_v7.png` | v7.0 评估可视化（6 子图）| ~200 KB |
| `data/plots/classifier_results_vA.png` | 方案 A 评估可视化 | ~200 KB |
| `projects/blackhole-beacon/data/blackcat_59_clean.json` | BlackCAT 31 个黑洞（Clean 样本）| ~8 KB |
| `projects/blackhole-beacon/data/known_pulsars_features.json` | 10 个已知脉冲星特征 | ~5 KB |
| `data/real_negative_samples_v4.json` | 1350 个真实负样本（来自 Simbad TAP）| ~1 MB |

---

## 5. 阻塞点（为什么暂停）

1. **v9.2 分类器有缺陷**：JHK 和 WISE 排名完全不重叠（交集=0）→ “分拆→取交集”策略无效。
2. **方案 ABC 都失败/有缺陷**：
   - A：分数融合，但 JHK 没贡献（TOP 20 全是 WISE-only）
   - B：合并特征，但 0 个候选体同时有 JHK+WISE
   - C：监督学习，但 BlackCAT 缺少 IR 星等（无法提取特征）
3. **P1 阻塞**：无法采集真实负样本（astroquery 不稳定，Simbad TAP 404）。
4. **验证不充分**：TOP 10 很可能是新的，但只做了名称查询（Simbad），没做**坐标交叉匹配**（10 arcsec 内有没有已知源）。

---

## 6. 重启步骤（下一步从哪开始）

### 选项 1：修复 v9.2（推荐）
**目标**：让 JHK 和 WISE 排名有重叠（交集>0）。

**步骤**：
1. 检查为什么 JHK 和 WISE 组完全不重叠（1917 vs. 538 个候选体，可能是 `phase3_candidates_full.json` 里很多候选体缺 WISE 数据）
2. 改用**分数融合**（方案 A），但改进融合方式：
   - 当前：有 JHK 分用 JHK，有 WISE 分用 WISE，两个都有→平均
   - 改进：**只保留两个模型都给出高分的候选体**（例如，JHK 概率>0.5 AND WISE 概率>0.5）
3. 或者用**加权平均**（根据两个模型在已知源上的表现分配权重）

**脚本**：修改 `scripts/train_vA_combined.py`（改进融合逻辑）

### 选项 2：为 BlackCAT 查询 IR 星等（方案 C 的前提）
**目标**：给 BlackCAT 31 个黑洞加上 J,H,K,W1,W2 数据，使监督学习可行。

**步骤**：
1. 用 `astroquery` 查 NED（NASA/IPAC Extragalactic Database）或 IRSA（IR Science Archive）
2. 批量查询 31 个黑洞的 2MASS + WISE 星等
3. 保存到 `data/blackcat_31_with_ir.json`
4. 重新训练监督分类器（方案 C）

**预计时间**：1-2 小时（31 个源 × 2 个星表 × API 延迟）

### 选项 3：放弃 v9.x，回到 v7.0（最省事）
**目标**：用 v7.0（Isolation Forest，4 特征）作为最终分类器。

**步骤**：
1. 接受 v7.0 的结果（异常分数范围 `[-0.2212, 0.1760]`）
2. 用 v7.0 排名生成最终候选体列表（TOP 20）
3. 做坐标交叉匹配（验证是否真的新的）
4. 生成观测提案（用 v7.0 TOP 20）

**优点**：v7.0 已经能用了（不再过拟合）  
**缺点**：v7.0 只用 IR 颜色，没用 PM 特征（PM=0.0 的候选体可能漏掉）

### 选项 4：换方法（Deep Learning）
**目标**：用神经网络（PyTorch）学“什么是黑洞/脉冲星”。

**步骤**：
1. 正样本：BlackCAT 31（需要 IR 星等，见选项 2）
2. 负样本：真实负样本 1350 个
3. 特征：J-H, H-K, W1-W2, PM_total（4 维）
4. 模型：简单 MLP（3 层）
5. 训练：监督学习（需要 GPU 吗？CPU 也能跑）

**预计时间**：3-4 小时（写脚本 + 训练 + 调参）

---

## 7. 经验教训（给未来的我）

### 技术层面
1. **数据结构调整**：`phase3_candidates_full.json` 的结构和我以为的完全不一样（标量 vs. 字典）→ 必须先 `print(candidate.keys())` 再写 `extract_features()`
2. **特征泄露（Data Leakage）**：Phase 3 分数不能当特征（正样本有，负样本没有）→ 分类器作弊
3. **PM 特征局限性**：`proper_motion_masyr` 是标量，无法拆成 `pm_ra`/`pm_dec` → 导致正样本 PM 特征全是 0.0
4. **过拟合调试**：5 轮迭代才找到根因（键值错误 → 分数作弊 → PM 特征无效 → IR 颜色完美分离）
5. **无监督学习解决过拟合**：Isolation Forest 不需要负样本，避免了“负样本太容易区分”的问题
6. **分拆特征的风险**：JHK 和 WISE 组完全不重叠 → “分拆→取交集”策略无效
7. **BlackCAT 数据不完整**：只有 name/ra/dec/type，没有 IR 星等 → 无法直接用作监督学习正样本

### 行为层面
1. **忽略空消息**：UI bug 导致 60+ 次空消息，不等待用户回复，直接继续工作
2. **卡住不超过 3 次重试**：每次训练 AUC=1.0000 都立即分析原因，不循环重试同一方案
3. **写中间文档**：调试过程复杂（5 轮迭代），需要写详细文档（`task-summary_*.md`）记录每次迭代的根因
4. **换方法而不是硬刚**：v6.0 还是过拟合 → 立即换方法（无监督学习），不继续调试监督学习
5. **先做最简单的验证**：TOP 10 验证，先做名称查询（Simbad），再做坐标交叉匹配（更严谨但更慢）

---

## 8. 快速重启检查清单

- [ ] 检查 `data/phase3_candidates_full.json` 是否存在（2455 候选体）
- [ ] 检查 `data/classifier_ranking_v7.json` 是否存在（v7.0 排名）
- [ ] 检查 `data/classifier_ranking_v9.json` 是否存在（v9.2 排名）
- [ ] 决定下一步：**修复 v9.2**（选项 1）还是**回到 v7.0**（选项 3）
- [ ] 如果选选项 1：读 `scripts/train_vA_combined.py`（方案 A，分数融合）
- [ ] 如果选选项 3：读 `scripts/classifier_train_v7.py`（v7.0，Isolation Forest）
- [ ] 验证 TOP 10：做坐标交叉匹配（10 arcsec 内查 Simbad）

---

**最后更新**：2026-05-23 09:14 GMT+8  
**项目状态**：⚠️ 部分完成（P0/P3/P4 ✅，P1/P2/P5 ❌/⚠️）  
**建议下一步**：选项 1（修复 v9.2）或选项 3（回到 v7.0）
