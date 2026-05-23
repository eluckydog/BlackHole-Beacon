# 2026-05-21 02:33 — 脉冲星目录加入 BlackHole Beacon

## 目标
用户要求"加上脉冲星"，将脉冲星作为时间锚点补充到黑洞空间锚点目录中。

## 完成内容

### 脉冲星目录获取
- 来源：ATNF Pulsar Catalogue v2.8.0，通过 VizieR 镜像 (B/psr) 获取
- 获取方式：VizieR HTML 页面解析（免注册），正则提取结构化数据
- 结果：3,342 个脉冲星，2530 个含精确坐标
- 字段：JName, RA/Dec (deg), P0 (周期秒), DM (色散), S1400 (1.4 GHz通量 mJy), W50 (脉宽 ms)
- 文件：psrcat_catalog.csv (288 KB)

### 技术挑战和解决
1. **ATNF 表单 500 错误**：POST 提交失败，换 VizieR 镜像路径
2. **VizieR 返回 HTML 而非 CSV**：程序化访问触发交互表单，改用 HTML 解析提取
3. **Dec 解析错误**：sign+deg 合并为单 token（如 "+18"、"-72"），修正为 3-token Dec 解析
4. **数据验证**：Crab 脉冲星 P0=0.033s (30Hz) ✓；J0024-7204C Dec=-72.075° ✓

### 最终数据资产 (catalog/)
| 文件 | 内容 | 大小 |
|------|------|------|
| bh_xrb_catalog.csv | 28 恒星级 BH | 2 KB |
| smbh_catalog.csv | 32 SMBH | 2 KB |
| gwtc_bbh_all.csv/json | 83 GWTC 事件 | 165 KB |
| psrcat_catalog.csv | 3,342 脉冲星 | 288 KB |
| **总计** | **3,485 天体** | **~502 KB** |

**2,590 个天体有精确坐标可用作锚点**（60 BH + 2,530 脉冲星）

### 下一步
Phase 1: IRSA TAP 表名映射调试 → 批量查询存档