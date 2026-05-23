#!/usr/bin/env python3
import json
import operator

# 读取 v9.0 排名文件
with open('data/classifier_ranking_v9.json', 'r') as f:
    rankings = json.load(f)

# 按异常分数降序排序（越高越异常）
sorted_rankings = sorted(rankings, key=lambda x: x['anomaly_score'], reverse=True)

# 输出 TOP 10
print("v9.0 TOP 10 异常体（按异常分数降序）:")
print("| 排名 | 锚点 | 异常分数 | 概率 | PM |")
print("|------|------|----------|------|-----|")
for i, cand in enumerate(sorted_rankings[:10], 1):
    print(f"| {i} | {cand['anchor']} | {cand['anomaly_score']:.4f} | {cand['prob']:.4f} | {cand['pm_total']} |")

# 同时保存到文件
with open('data/top10_v9.json', 'w') as f:
    json.dump(sorted_rankings[:10], f, indent=2)

print("\nTOP 10 已保存到 data/top10_v9.json")
