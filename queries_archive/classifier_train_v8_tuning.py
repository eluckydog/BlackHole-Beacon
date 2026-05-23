"""
classifier_train_v8_tuning.py - v8.0 参数调优（contamination 搜索）
"""

import json
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "plots"
OUTPUT_DIR.mkdir(exist_ok=True)

KNOWN_PULSARS = [
    "J0534+2200", "J0835-4510", "J0633+1746", "J0007+7303",
    "J0205+6449", "J1048-5832", "J1418-6058", "J2021+4026",
    "J0229+5867", "J1826-1480", "J1509-5850", "J1616-5085", "J1702-4128",
]

def load_phase3_candidates():
    with open(DATA_DIR / "phase3_candidates_full.json", 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_features(candidates):
    features = []
    valid = []
    for c in candidates:
        j = c.get('J')
        h = c.get('H')
        k = c.get('K')
        if j is None or h is None or k is None:
            continue
        try:
            j_h = float(j) - float(h)
            h_k = float(h) - float(k)
            w1 = c.get('W1')
            w2 = c.get('W2')
            if w1 is not None and w2 is not None:
                w1_w2 = float(w1) - float(w2)
            else:
                w1_w2 = 0.0
            w2_w3 = 0.0
            
            pm_total = c.get('proper_motion_masyr', 0.0)
            pm_ra = c.get('pm_ra', 0.0)
            pm_dec = c.get('pm_dec', 0.0)
            variability_mean = c.get('variability_mean', 0.0)
            variability_std = c.get('variability_std', 0.0)
            compactness = c.get('compactness', 0.0)
            
            fv = [j_h, h_k, w1_w2, w2_w3, pm_total, pm_ra, pm_dec, variability_mean, variability_std, compactness]
            features.append(fv)
            valid.append(c)
        except (ValueError, TypeError):
            continue
    return np.array(features), valid

def train_if(X, contamination):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    model = IsolationForest(n_estimators=200, max_samples='auto',
                            contamination=contamination, random_state=42, n_jobs=-1)
    model.fit(Xs)
    scores = model.decision_function(Xs)
    probs = 1 / (1 + np.exp(-scores * 5))
    return model, scaler, scores, probs

def evaluate(X, candidates, c_values):
    results = {}
    for c in c_values:
        print(f"\n训练 Isolation Forest (contamination={c})...")
        model, scaler, scores, probs = train_if(X, c)
        ranking = list(zip(candidates, scores, probs))
        ranking.sort(key=lambda x: x[1], reverse=True)
        
        top50 = top100 = top200 = 0
        for i, (cand, s, p) in enumerate(ranking):
            aid = cand.get('anchor_id', '')
            for ks in KNOWN_PULSARS:
                if ks in aid:
                    if i < 50: top50 += 1
                    if i < 100: top100 += 1
                    if i < 200: top200 += 1
                    break
        
        results[c] = {'top50': top50, 'top100': top100, 'top200': top200,
                       'model': model, 'scaler': scaler, 'scores': scores,
                       'probs': probs, 'ranking': ranking}
        print(f"  TOP 50: {top50}, TOP 100: {top100}, TOP 200: {top200}")
    return results

def plot_results(results, output_file):
    cs = list(results.keys())
    top50 = [results[c]['top50'] for c in cs]
    top100 = [results[c]['top100'] for c in cs]
    top200 = [results[c]['top200'] for c in cs]
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    x = np.arange(len(cs))
    w = 0.25
    ax.bar(x - w, top50, w, label='TOP 50', color='red')
    ax.bar(x, top100, w, label='TOP 100', color='orange')
    ax.bar(x + w, top200, w, label='TOP 200', color='green')
    ax.set_xlabel('Contamination')
    ax.set_ylabel('Known Pulsars')
    ax.set_title('Contamination Tuning')
    ax.set_xticks(x)
    ax.set_xticklabels([str(c) for c in cs])
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    print(f"\n评估图已保存：{output_file}")

def main():
    print("=" * 60)
    print("v8.0 参数调优（contamination 搜索）")
    print("=" * 60)
    
    candidates = load_phase3_candidates()
    print(f"\n候选体数量：{len(candidates)}")
    
    X, valid = extract_features(candidates)
    print(f"\n有效候选体：{len(X)}")
    if len(X) == 0:
        print("错误：没有有效候选体，退出")
        return
    print(f"特征维度：{X.shape[1]}")
    
    c_values = [0.05, 0.10, 0.15, 0.20]
    print(f"\n评估 contamination 参数：{c_values}")
    results = evaluate(X, valid, c_values)
    
    best_c = max(results.keys(), key=lambda c: results[c]['top50'])
    print(f"\n最佳 contamination：{best_c}")
    print(f"  TOP 50 已知源：{results[best_c]['top50']}")
    
    best = results[best_c]
    ranking = best['ranking']
    output_ranking = []
    for i, (cand, score, prob) in enumerate(ranking):
        output_ranking.append({
            'rank': i + 1,
            'anchor_id': cand.get('anchor_id', ''),
            'anomaly_score': float(score),
            'probability': float(prob),
            'proper_motion_masyr': cand.get('proper_motion_masyr', 0.0)
        })
    
    out_file = DATA_DIR / f"classifier_ranking_v8_contamination_{best_c}.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({'contamination': best_c, 'candidates': output_ranking}, f, indent=2, ensure_ascii=False)
    print(f"\n最佳排名已保存：{out_file}")
    
    plot_file = OUTPUT_DIR / "contamination_tuning_results.png"
    plot_results(results, plot_file)
    
    print("\n" + "=" * 60)
    print("参数调优完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
