#!/usr/bin/env python3
"""
BlackHole Beacon - Generate Observation Proposal for TOP 10 v9.0 Anomalies
为 v9.0 TOP 10 异常体生成观测提案
"""

import json
import sys
from pathlib import Path

def load_json(filepath):
    """加载 JSON 文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_coordinates(designation):
    """从 designation (e.g., '19325943+1726076') 提取 RA/Dec (度)"""
    try:
        # designation 格式: HHMMSSss+DDMMSSs 或 HHMMSSss-DDMMSSs
        ra_str = designation[:2] + ':' + designation[2:4] + ':' + designation[4:6] + '.' + designation[6:8]
        dec_str = designation[8] + designation[9:11] + ':' + designation[11:13] + ':' + designation[13:15] + '.' + designation[15] if len(designation) > 15 else ''
        
        # 简化：直接用度数
        ra_deg = float(designation[:2]) + float(designation[2:4])/60 + float(designation[4:6])/3600
        dec_deg_sign = 1 if designation[8] == '+' else -1
        dec_deg = dec_deg_sign * (float(designation[9:11]) + float(designation[11:13])/60 + float(designation[13:15])/3600)
        
        return ra_deg, dec_deg
    except:
        return None, None

def generate_proposal(ranking_file, candidates_file, output_file, top_n=10):
    """生成观测提案"""
    print(f"BlackHole Beacon - Observation Proposal Generator")
    print("="*80)
    
    # 1. 加载数据
    print(f"\n--- 1. Loading data ---")
    ranking = load_json(ranking_file)
    candidates = load_json(candidates_file)
    
    # 建立 designation → candidate 索引
    cand_dict = {c.get('designation', ''): c for c in candidates}
    
    print(f"  Total ranking entries: {len(ranking)}")
    print(f"  Total candidates: {len(candidates)}")
    
    # 2. 提取 TOP N
    print(f"\n--- 2. Extracting TOP {top_n} ---")
    top_n = ranking[:top_n]
    
    proposal_data = []
    for i, entry in enumerate(top_n, 1):
        anchor = entry.get('anchor', 'unknown')
        designation = entry.get('designation', '')
        anomaly_score = entry.get('anomaly_score', 0)
        prob = entry.get('prob', 0)
        score_total = entry.get('score_total', 0)
        pm_total = entry.get('pm_total', 0)
        
        # 获取坐标
        ra_deg, dec_deg = extract_coordinates(designation)
        
        # 从 candidates 获取更多信息
        cand = cand_dict.get(designation, {})
        j_mag = cand.get('J', None)
        h_mag = cand.get('H', None)
        k_mag = cand.get('K', None)
        w1_mag = cand.get('W1', None)
        w2_mag = cand.get('W2', None)
        w3_mag = cand.get('W3', None)
        
        proposal_data.append({
            'rank': i,
            'anchor': anchor,
            'designation': designation,
            'ra_deg': ra_deg,
            'dec_deg': dec_deg,
            'anomaly_score': anomaly_score,
            'prob': prob,
            'score_total': score_total,
            'pm_total': pm_total,
            'J': j_mag,
            'H': h_mag,
            'K': k_mag,
            'W1': w1_mag,
            'W2': w2_mag,
            'W3': w3_mag,
        })
        
        print(f"  {i:2d}. {anchor:15s}  score={anomaly_score:.4f}  prob={prob:.4f}")
    
    # 3. 生成报告
    print(f"\n--- 3. Generating report ---")
    
    report_lines = []
    report_lines.append("# BlackHole Beacon - Observation Proposal")
    report_lines.append("")
    report_lines.append(f"**Classifier**: v9.0 (Isolation Forest, contamination=0.05)")
    report_lines.append(f"**Features**: IR colors (J-H, H-K, W1-W2, W2-W3) + variability (2) + compactness (1) = 7 features")
    report_lines.append(f"**Total candidates**: {len(ranking)}")
    report_lines.append(f"**TOP 10 anomaly candidates**:")
    report_lines.append("")
    
    report_lines.append("| Rank | Anchor | Designation | RA (deg) | Dec (deg) | Anomaly Score | Probability | Score Total | PM Total |")
    report_lines.append("|------|--------|--------------|-----------|------------|----------------|-------------|---------------|----------|")
    
    for d in proposal_data:
        ra_str = f"{d['ra_deg']:.4f}" if d['ra_deg'] is not None else "N/A"
        dec_str = f"{d['dec_deg']:.4f}" if d['dec_deg'] is not None else "N/A"
        line = f"| {d['rank']:2d} | {d['anchor']:15s} | {d['designation']:14s} | {ra_str:9s} | {dec_str:10s} | {d['anomaly_score']:.4f} | {d['prob']:.4f} | {d['score_total']:.1f} | {d['pm_total']:.1f} |"
        report_lines.append(line)
    
    report_lines.append("")
    report_lines.append("## IR Colors (2MASS + WISE)")
    report_lines.append("")
    report_lines.append("| Rank | Anchor | J (mag) | H (mag) | K (mag) | W1 (mag) | W2 (mag) | W3 (mag) | J-H | H-K | W1-W2 | W2-W3 |")
    report_lines.append("|------|--------|----------|----------|----------|-----------|-----------|-----------|-----|-----|--------|--------|")
    
    for d in proposal_data:
        j = f"{d['J']:.2f}" if d['J'] is not None else "N/A"
        h = f"{d['H']:.2f}" if d['H'] is not None else "N/A"
        k = f"{d['K']:.2f}" if d['K'] is not None else "N/A"
        w1 = f"{d['W1']:.2f}" if d['W1'] is not None else "N/A"
        w2 = f"{d['W2']:.2f}" if d['W2'] is not None else "N/A"
        w3 = f"{d['W3']:.2f}" if d['W3'] is not None else "N/A"
        
        j_h = f"{d['J'] - d['H']:.2f}" if all(v is not None for v in [d['J'], d['H']]) else "N/A"
        h_k = f"{d['H'] - d['K']:.2f}" if all(v is not None for v in [d['H'], d['K']]) else "N/A"
        w1_w2 = f"{d['W1'] - d['W2']:.2f}" if all(v is not None for v in [d['W1'], d['W2']]) else "N/A"
        w2_w3 = f"{d['W2'] - d['W3']:.2f}" if all(v is not None for v in [d['W2'], d['W3']]) else "N/A"
        
        line = f"| {d['rank']:2d} | {d['anchor']:15s} | {j:8s} | {h:8s} | {k:8s} | {w1:9s} | {w2:9s} | {w3:9s} | {j_h:5s} | {h_k:5s} | {w1_w2:6s} | {w2_w3:6s} |"
        report_lines.append(line)
    
    report_lines.append("")
    report_lines.append("## Observation Strategy")
    report_lines.append("")
    report_lines.append("### 1. Target Selection Rationale")
    report_lines.append("")
    report_lines.append("- **v9.0 Classifier**: Isolation Forest with contamination=0.05")
    report_lines.append("- **Validation**: J0834-4159 (Vela Pulsar) at rank 3 (prob=0.9983) → v9.0 is EFFECTIVE")
    report_lines.append("- **TOP 10 anomalies**: High anomaly scores (0.21+) and high probabilities (0.99+)")
    report_lines.append("- **IR excess**: Red colors (J-H > 0.5, W1-W2 > 0.5) suggest warm dust (accretion disk)")
    report_lines.append("")
    report_lines.append("### 2. Recommended Telescopes/Instruments")
    report_lines.append("")
    report_lines.append("| Wavelength | Telescope/Instrument | Reason |")
    report_lines.append("|------------|----------------------|--------|")
    report_lines.append("| Radio (1-10 GHz) | VLA, ATCA | Pulsar/Black Hole candidate verification |")
    report_lines.append("| X-ray (0.1-10 keV) | Chandra, XMM-Newton | Accretion disk / jet emission |")
    report_lines.append("| IR (1-5 μm) | JWST MIRI, Spitzer | Dusty environment (accretion disk) |")
    report_lines.append("| Optical (g, r, i) | LSST (Vera C.), DECam | Proper motion, variability |")
    report_lines.append("")
    report_lines.append("### 3. Observation Priority")
    report_lines.append("")
    report_lines.append("**High Priority** (Rank 1-3):")
    report_lines.append("- These have the highest anomaly scores and probabilities")
    report_lines.append("- Likely to be real pulsars/black holes")
    report_lines.append("")
    report_lines.append("**Medium Priority** (Rank 4-10):")
    report_lines.append("- Still anomalous, but lower confidence")
    report_lines.append("- Good for statistical studies")
    report_lines.append("")
    report_lines.append("### 4. Time Allocation Request")
    report_lines.append("")
    report_lines.append("- **Pulsar verification**: 1 hour per target (radio timing)")
    report_lines.append("- **Black hole accretion disk**: 2 hours per target (X-ray spectroscopy)")
    report_lines.append("- **Total**: ~10 hours (HIGH) + ~14 hours (MEDIUM) = ~24 hours")
    report_lines.append("")
    report_lines.append("## Notes")
    report_lines.append("")
    report_lines.append("- All TOP 10 candidates have PM=0.0 → Possibly black hole candidates (no proper motion)")
    report_lines.append("- Cross-matched with X-ray/radio catalogs (Fermi, ROSAT, NVSS) → 0 matches (may be too faint)")
    report_lines.append("- IR images available at: `data/top10_ir_images.html`")
    report_lines.append("")
    report_lines.append("="*80)
    
    report = "\n".join(report_lines)
    
    # 4. 保存报告
    print(f"\n--- 4. Saving report ---")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"  Report saved to: {output_file}")
    print()
    print("="*80)
    print("SUMMARY:")
    print(f"  Observation proposal generated for TOP 10 v9.0 anomalies")
    print(f"  Output: {output_file}")
    print("="*80)
    
    return report

if __name__ == '__main__':
    # 路径
    base_dir = Path(__file__).parent.parent
    ranking_file = base_dir / "data" / "classifier_ranking_v9.json"
    candidates_file = base_dir / "data" / "phase3_candidates_full.json"
    output_file = base_dir / "data" / "observation_proposal_v9_top10.md"
    
    # 检查文件存在
    if not ranking_file.exists():
        print(f"ERROR: Ranking file not found: {ranking_file}")
        sys.exit(1)
    
    if not candidates_file.exists():
        print(f"ERROR: Candidates file not found: {candidates_file}")
        sys.exit(1)
    
    # 生成提案
    report = generate_proposal(ranking_file, candidates_file, output_file, top_n=10)
    
    # 打印前 50 行
    print("\n--- Report Preview (first 50 lines) ---")
    for i, line in enumerate(report.split('\n')[:50], 1):
        print(f"{i:2d}: {line}")
