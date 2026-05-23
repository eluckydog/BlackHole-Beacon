#!/usr/bin/env python3
"""
多波段验证：TOP 10 候选体与 X 射线/射电极化匹配 (修复版)
使用 astroquery.vizier 查询 ROSAT All-Sky Survey (X 射线) 和 NVSS (射电)
"""
import json
import sys
sys.path.append('.')

try:
    from astroquery.vizier import Vizier
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    HAS_ASTROQUERY = True
    print("✅ astroquery available, using Vizier for cross-match")
except ImportError as e:
    HAS_ASTROQUERY = False
    print(f"WARNING: astroquery not available: {e}")
    sys.exit(1)

# 启用大结果集
Vizier.ROW_LIMIT = -1

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
    
    coord = SkyCoord(ra=ra*u.deg, dec=dec*u.deg, frame='icrs')
    radius = radius_arcsec * u.arcsec
    
    # X 射线匹配（ROSAT All-Sky Survey - VizieR catalog IX/29）
    try:
        # ROSAT All-Sky Survey Bright Source Catalog (Voges et al. 1999)
        # Catalog ID: IX/29A (1RXS)
        xray_tables = Vizier.query_region(coord, radius=radius, catalog="IX/29A")
        if xray_tables and len(xray_tables) > 0:
            xray_table = xray_tables[0]
            # Convert astropy table rows to JSON-serializable dict
            result["xray_matches"] = []
            for row in xray_table:
                row_dict = {}
                for col in xray_table.colnames:
                    val = row[col]
                    # Convert numpy types to native Python types
                    if hasattr(val, 'item'):
                        val = val.item()
                    row_dict[col] = val
                result["xray_matches"].append(row_dict)
            result["notes"] += f"X-ray: {len(xray_table)} matches; "
            print(f"    ✅ X-ray: {len(xray_table)} match(es) found")
        else:
            print(f"    ⚪ X-ray: 0 matches")
    except Exception as e:
        result["notes"] += f"X-ray query failed: {e}; "
        print(f"    ❌ X-ray query failed: {e}")
    
    # 射电匹配（NVSS - VizieR catalog VIII/65）
    try:
        # NVSS catalog (Condon et al. 1998)
        # Catalog ID: VIII/65
        radio_tables = Vizier.query_region(coord, radius=radius, catalog="VIII/65")
        if radio_tables and len(radio_tables) > 0:
            radio_table = radio_tables[0]
            # Convert astropy table rows to JSON-serializable dict
            result["radio_matches"] = []
            for row in radio_table:
                row_dict = {}
                for col in radio_table.colnames:
                    val = row[col]
                    # Convert numpy types to native Python types
                    if hasattr(val, 'item'):
                        val = val.item()
                    row_dict[col] = val
                result["radio_matches"].append(row_dict)
            result["notes"] += f"Radio: {len(radio_table)} matches; "
            print(f"    ✅ Radio: {len(radio_table)} match(es) found")
        else:
            print(f"    ⚪ Radio: 0 matches")
    except Exception as e:
        result["notes"] += f"Radio query failed: {e}; "
        print(f"    ❌ Radio query failed: {e}")
    
    return result

def parse_designation(des):
    """
    从 designation 解析 RA/Dec (格式: "19325943+1726076" → RA/Dec in degrees)
    """
    # 找到 + 或 - 符号的位置
    import re
    match = re.search(r'(\d{8})([+-])(\d{7})', des)
    if not match:
        raise ValueError(f"Cannot parse designation: {des}")
    
    ra_str = match.group(1)
    dec_sign = match.group(2)
    dec_str = match.group(3)
    
    # RA: HHMMSS.ss → degrees
    ra_h = float(ra_str[:2])
    ra_m = float(ra_str[2:4])
    ra_s = float(ra_str[4:6] + '.' + ra_str[6:8])
    ra_deg = (ra_h + ra_m/60.0 + ra_s/3600.0) * 15.0  # HH → degrees
    
    # Dec: DDMMSS.s → degrees
    dec_d = float(dec_str[:2])
    dec_m = float(dec_str[2:4])
    dec_s = float(dec_str[4:6] + '.' + dec_str[6:7])
    dec_deg = dec_d + dec_m/60.0 + dec_s/3600.0
    if dec_sign == '-':
        dec_deg = -dec_deg
    
    return ra_deg, dec_deg

def main():
    # 读取 TOP 10 候选体
    with open('data/top10_v9.json', 'r') as f:
        top10 = json.load(f)
    
    print(f"\n🔭 开始对 v9.0 TOP 10 候选体进行多波段验证...")
    print(f"共 {len(top10)} 个候选体\n")
    
    results = []
    
    for i, cand in enumerate(top10, 1):
        anchor = cand['anchor']
        des = cand['designation']
        
        try:
            ra_deg, dec_deg = parse_designation(des)
            
            print(f"[{i}/10] {anchor} (RA={ra_deg:.3f}°, Dec={dec_deg:.3f}°)")
            
            # 交叉匹配
            match_result = cross_match_candidate(anchor, ra_deg, dec_deg)
            results.append(match_result)
            
            # 输出简要结果
            xray_count = len(match_result['xray_matches'])
            radio_count = len(match_result['radio_matches'])
            
            if match_result['notes']:
                print(f"    Notes: {match_result['notes']}")
            print()
            
        except Exception as e:
            print(f"[{i}/10] {anchor} - 解析坐标失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({"anchor": anchor, "error": str(e)})
    
    # 保存结果
    output_file = 'data/top10_v9_crossmatch.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 交叉匹配完成！结果已保存到 {output_file}\n")
    
    # 统计
    total_xray = sum(len(r.get('xray_matches', [])) for r in results if 'xray_matches' in r)
    total_radio = sum(len(r.get('radio_matches', [])) for r in results if 'radio_matches' in r)
    print(f"📊 统计: {total_xray} X-ray matches, {total_radio} radio matches")
    
    # 详细结果
    print(f"\n📋 详细结果:")
    for r in results:
        if 'error' in r:
            print(f"  {r['anchor']}: ❌ {r['error']}")
        else:
            xray_count = len(r.get('xray_matches', []))
            radio_count = len(r.get('radio_matches', []))
            print(f"  {r['anchor']}: X-ray={xray_count}, Radio={radio_count}")

if __name__ == '__main__':
    main()
