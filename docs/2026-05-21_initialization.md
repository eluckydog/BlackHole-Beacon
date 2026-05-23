# 2026-05-21 02:23 — BlackHole Beacon 项目初始化

## 目的
用户决定做黑洞信标项目：用已确认黑洞坐标做固定锚点，回溯历史存档原始数据，交叉比对信号，拟合发现算法。

## 完成内容

### 1. 项目工作区建立
`projects/blackhole-beacon/` — catalog / queries / data / algorithms / results

### 2. 黑洞锚点目录获取（214 KB，远低于200MB限制）
- **恒星级 BH X 射线双星**: 28 个，含精确 RA/Dec/质量/距离/参考文献（bh_xrb_catalog.csv）
- **SMBH**: 32 个，含精确 RA/Dec/质量/测质方法/红移（smbh_catalog.csv）
- **GWTC 并合事件**: 83 个，含质量/自旋/红移/SNR（gwtc_bbh_all.csv + gwtc_all_bbh.json）
- **总计**: 143 个黑洞，其中 60 个有精确坐标

### 3. 数据来源
- LIGO/Virgo GWOSC API：免注册，直接 HTTP GET 拉取 GWTC 1/2.1/3 全部事件
- 手动编译：从发表的动力学质量测量文献整理坐标和质量
- BlackCAT VizieR 存档：获取但需后续解析

### 4. 存档访问验证
- IRSA (2MASS/IRAS/WISE/ZTF): API 可通，表名需修正
- HEASARC (ROSAT): 接口可访问
- DASCH（哈佛底片，1885-1993）: 网络不通
- VizieR: SSL 证书问题

### 5. 关键技术细节
- GWTC API JSON 结构：events 为扁平 dict，key=eventName-v1, value=54字段直接值
- PowerShell 编码限制：-c 参数中文/引号转义问题严重，需用脚本文件替代
- IRSA TAP endpoint 返回 XML VOTABLE 格式，需用 FORMAT=json 参数

### 下一步
- Phase 1: IRSA TAP 表名映射调试 → 批量查询 60 锚点 × 5 存档
- 实施计划存于: projects/blackhole-beacon/IMPLEMENTATION.md