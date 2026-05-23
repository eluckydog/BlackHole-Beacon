# 三条审计报告 — blackhole-beacon

> 2026-05-23 18:45 | 审计方式：门下省 + 红队(T2) + 工程化AI(T2)

---

## 一、门下省 — 范围与规范性审计

**判决：附条件准奏（评分 5.5/10）**

### ✅ 通过
- 项目目标和范围清晰（检索 BHXB 候选体）
- PROJECT_STATUS.md 完整记录了所有迭代和阻塞点
- 已知局限全部标注

### ⚠️ 问题

**P1 — 项目名不一致**
- README 自称 `spectral-anchor-engine`，但目录是 `blackhole-beacon`
- GitHub 仓库名可能冲突

**P2 — 代码不可复现**
- Phase 1-3 依赖 `data/` 下的特定中间文件，没有独立输入/输出接口
- `extract_features()` 函数散落在多个脚本中

**P3 — 数据依赖不明确**
- 没有 `requirements.txt`，依赖 `astroquery`, `scikit-learn`, `numpy`, `scipy`, `matplotlib`
- 没有说明哪些数据是生成的、哪些是从外部下载的

### 建议
- 统一项目名
- 加 `requirements.txt`
- Phase 1-3 脚本加 CLI 参数（输入/输出路径）

---

## 二、红队 — 安全审计（T2）

**判决：低风险，T2 通过**

### 安全问题

**低风险 — 裸 except 在多处出现**
- `download_blackcat_v2.py`: `except:` 无异常绑定
- `multi_archive_v2.py`: 批量查询处 `except:` 吞超时

**信息 — 大量脚本未使用**
- `queries_archive/` 中有 ~78 个脚本，很多是草稿或单次调试用的
- 新接手者可能误用旧版脚本

**信息 — 数据隐私**
- `data/` 下的 JSON 包含天球坐标（RA/Dec），这不属于个人隐私，但需注意公开使用时的数据协议（2MASS/WISE/Gaia 都是公开数据）

### 触发测试（5条）

| # | 输入 | 触发 | 结案 |
|---|------|------|------|
| 1 | "找黑洞候选体" | ✅ | Phase 1-3 |
| 2 | "红外颜色异常" | ✅ | Phase 1 |
| 3 | "Isolation Forest 分类" | ✅ | v7 分类器 |
| 4 | "验证 TOP 10" | ✅ | 交叉匹配 |
| 5 | "食双星相位折叠" | ❌ **不触发** | eclipsing-beats |

---

## 三、工程化AI — 代码审计（T2）

**判决：评分 5.0/10**

### 通过
- 管道逻辑完整（Phase 1→2→3→分类器→验证→提案）
- v7 Isolation Forest 方法学合理
- 文档详尽（PROJECT_STATUS.md 是好的交接文档）

### 问题

**P1 — 无类型注解**
- ~150 个函数，全部无类型提示

**P2 — 无 pytest**
- 零自动化测试

**P3 — 无 requirements.txt**
- 依赖：scikit-learn, numpy, scipy, matplotlib, astroquery

**P4 — 重复代码**
- `extract_features()` 有多个版本（v1-v4），重复实现
- `query_all_known_bh` 有 3 个版本

**P5 — 脚本名混乱**
- `classifier_train_v7`, `train_bh_classifier_v3`, `classifier_train_v8`：功能重叠
- 新接手者很难区分哪个是 "最终版"

### 建议
1. 加 `requirements.txt`
2. 至少给 `code/` 中的 16 个脚本加类型注解
3. `queries_archive/` 中的重复版本文档化（哪个是最终版）

---

## 综合优先级

| 优先级 | 问题 | 修复难度 |
|--------|------|----------|
| **P1** | 项目名不一致（README vs 目录） | 1 行 |
| **P1** | 无 `requirements.txt` | 5 行 |
| **P2** | 无类型注解 | 大（~150 函数） |
| **P2** | 无 pytest | 需设计 |
| **P3** | 代码不可复现（输入/输出硬编码） | 中 |
| **P3** | 重复代码 | 中 |
