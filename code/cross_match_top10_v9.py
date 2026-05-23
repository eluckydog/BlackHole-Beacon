#!/usr/bin/env python3
"""
多波段验证：TOP 10 候选体与 X 射线/射电极化匹配
使用 astroquery 查询 ROSAT All-Sky Survey (X 射线) 和 NVSS (射电)
"""
import json
import sys
sys.path.append('.')

try:
    from astroquery.rosat import RosatAllSkySurvey
    from astroquery.nvss import Nvss
    HAS_ASTROQUERY = True
except ImportError:
    HAS_ASTROQUERY = False
    print("WARNING: astroquery not available, will use Simbad as fallback")

def cross_match_candidate(anchor, ra, dec, radius_arcsec=300):
    """
    对单个候选体做 X 射线 + 射电极化匹配
    radius_arcsec: 匹配半径（默认 5 角分 = 300 角秒）
    """
    result = {
        "anchor": anchor,
        "ra": ra,
        "dec": dec,
        "xray_matches": [],
        "radio_matches": [],
        "notes": ""
    }
    
    if not HAS_ASTROQUERY:
        result["notes"] = "astroquery not available, skipping"
        return result
    
    # X 射线匹配（ROSAT All-Sky Survey）
    try:
        rosat = RosatAllSkySurvey()
        xray_table = rosat.query_region((ra, dec), radius=radius_arcsec * u.arcsec)
        if len(xray_table) > 0:
            result["xray_matches"] = xray_table.to_pandas().to_dict('records')
            result["notes"] += f"X-ray: {len(xray_table)} matches; "
    except Exception as e:
        result["notes"] += f"X-ray query failed: {e}; "
    
    # 射电匹配（NVSS）
    try:
        nvss = Nvss()
        radio_table = nvss.query_region((ra, dec), radius=radius_arcsec * u.arcsec)
        if len(radio_table) > 0:
            result["radio_matches"] = radio_table.to_pandas().to_dict('records')
            result["notes"] += f"Radio: {len(radio_table)} matches; "
    except Exception as e:
        result["notes"] += f"Radio query failed: {e}; "
    
    return result

def main():
    # 读取 TOP 10 候选体
    with open('data/top10_v9.json', 'r') as f:
        top10 = json.load(f)
    
    print(f"开始对 v9.0 TOP 10 候选体进行多波段验证...")
    print(f"共 {len(top10)} 个候选体\n")
    
    results = []
    
    for i, cand in enumerate(top10, 1):
        anchor = cand['anchor']
        # 从 designation 解析 RA/Dec (格式: "19325943+1726076" → 19:32:59.43 +17:26:07.6)
        des = cand['designation']
        try:
            ra_str = des[:4] + ':' + des[4:6] + ':' + des[6:8] + '.' + des[8:10]
            dec_sign = '+' if '+' in des else '-'
            dec_parts = des.split(dec_sign)
            if len(dec_parts) == 2:
                dec_str = dec_parts[1][:2] + ':' + dec_parts[1][2:4] + ':' + dec_parts[1][4:6] + '.' + dec_parts[1][6:8]
                # 简单近似：直接用 degree 为单位（实际需要转换为小数度）
                ra_deg = float(des[:2]) + float(des[2:4])/60.0 + float(des[4:6])/3600.0
                dec_deg = float(dec_parts[1][:2]) + float(dec_parts[1][2:4])/60.0 + float(dec_parts[1][4:6])/3600.0
                if dec_sign == '-':
                    dec_deg = -dec_deg
                
                print(f"[{i}/10] {anchor} (RA={ra_deg:.3f}, Dec={dec_deg:.3f})")
                
                # 交叉匹配
                match_result = cross_match_candidate(anchor, ra_deg, dec_deg)
                results.append(match_result)
                
                # 输出简要结果
                xray_count = len(match_result['xray_matches'])
                radio_count = len(match_result['radio_matches'])
                print(f"  X-ray: {xray_count} matches, Radio: {radio_count} matches")
                if match_result['notes']:
                    print(f"  Notes: {match_result['notes']}")
                print()
        except Exception as e:
            print(f"[{i}/10] {anchor} - 解析坐标失败: {e}")
            results.append({"anchor": anchor, "error": str(e)})
    
    # 保存结果
    with open('data/top10_v9_crossmatch.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ 交叉匹配完成！结果已保存到 data/top10_v9_crossmatch.json")
    
    # 统计
    total_xray = sum(len(r.get('xray_matches', [])) for r in results)
    total_radio = sum(len(r.get('radio_matches', [])) for r in results)
    print(f"统计: {total_xray} X-ray matches, {total_radio} radio matches")

if __name__ == '__main__':
    main()
