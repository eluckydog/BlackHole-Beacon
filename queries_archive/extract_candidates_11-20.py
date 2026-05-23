import json

# 读取v9.0排名文件
with open(r'C:\Users\13918\.qclaw\workspace-math-science\projects\blackhole-beacon\data\classifier_ranking_v9.json', 'r') as f:
    data = json.load(f)

# 按rank排序
data_sorted = sorted(data, key=lambda x: x['rank'])

# 提取#11-#20
print("排名\t锚点\tdesignation\t异常分数\tPM")
print("=" * 80)
for i in range(10, 20):
    if i < len(data_sorted):
        c = data_sorted[i]
        print(f"{c['rank']}\t{c['anchor']}\t{c['designation']}\t{c['anomaly_score']:.6f}\t{c['pm_total']}")
