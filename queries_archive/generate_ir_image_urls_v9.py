#!/usr/bin/env python3
"""
为 TOP 10 候选体生成 IR 图像查看链接
支持：2MASS (J, H, Ks)、WISE (W1, W2, W3, W4)、DSS (Optical)
"""
import json
import urllib.parse

def generate_ir_image_urls(anchor, ra, dec):
    """
    生成 IR 图像查看 URL
    anchor: 锚点名称（如 "J1933+1726"）
    ra, dec: 坐标（度）
    """
    urls = {}
    
    # 2MASS 图像查看器（需要 RA/Dec 字符串）
    ra_hms = deg_to_hms(ra)
    dec_dms = deg_to_dms(dec)
    
    # URL encode 坐标
    coord_str = f"{ra_hms} {dec_dms}"
    encoded_coord = urllib.parse.quote(coord_str)
    
    # 2MASS 图像查看器
    urls['2mass_viewer'] = f"https://irsa.ipac.caltech.edu/applications/2MASS/IM/viewer/getImage?ra={ra:.6f}&dec={dec:.6f}&size=300"
    
    # WISE 图像查看器
    urls['wise_viewer'] = f"https://irsa.ipac.caltech.edu/applications/WISE/IM/viewer/getImage?ra={ra:.6f}&dec={dec:.6f}&size=300"
    
    # Simbad 信息页面
    urls['simbad'] = f"https://simbad.u-strasbg.fr/simbad/sim-coo?Coord={ra:.6f}+{dec:.6f}&Radius=5&Radius.unit=arcmin"
    
    # Aladin Lite（交互式天空浏览器）
    urls['aladin'] = f"https://aladin.u-strasbg.fr/AladinLite/?target={ra:.6f}+{dec:.6f}&fov=0.1"
    
    return urls

def deg_to_hms(ra_deg):
    """将赤经从度数转换为时分秒字符串"""
    ra_h = int(ra_deg / 15.0)
    ra_m = int((ra_deg / 15.0 - ra_h) * 60)
    ra_s = ((ra_deg / 15.0 - ra_h) * 60 - ra_m) * 60
    return f"{ra_h:02d}:{ra_m:02d}:{ra_s:05.2f}"

def deg_to_dms(dec_deg):
    """将赤纬从度数转换为度分秒字符串"""
    sign = '+' if dec_deg >= 0 else '-'
    dec_abs = abs(dec_deg)
    dec_d = int(dec_abs)
    dec_m = int((dec_abs - dec_d) * 60)
    dec_s = ((dec_abs - dec_d) * 60 - dec_m) * 60
    return f"{sign}{dec_d:02d}:{dec_m:02d}:{dec_s:05.2f}"

def parse_designation(des):
    """
    从 designation 解析 RA/Dec（简单近似）
    格式: "19325943+1726076" → RA=19:32:59.43, Dec=+17:26:07.6
    """
    # 找到 + 或 - 符号位置
    for i, c in enumerate(des):
        if c in '+-':
            split_idx = i
            break
    
    ra_str = des[:split_idx]
    dec_str = des[split_idx:]
    
    # RA: HHMMSS.ss → 转换为度数
    if len(ra_str) >= 8:
        ra_h = float(ra_str[:2])
        ra_m = float(ra_str[2:4])
        ra_s = float(ra_str[4:6]) + float(ra_str[6:8]) / 100.0
        ra_deg = (ra_h + ra_m / 60.0 + ra_s / 3600.0) * 15.0  # RA 是时分秒，需要 ×15 转为度数
    else:
        ra_deg = 0.0
    
    # Dec: DDMMSS.ss → 转换为度数
    sign = -1 if dec_str[0] == '-' else 1
    dec_abs = dec_str[1:]
    if len(dec_abs) >= 8:
        dec_d = float(dec_abs[:2])
        dec_m = float(dec_abs[2:4])
        dec_s = float(dec_abs[4:6]) + float(dec_abs[6:8]) / 100.0
        dec_deg = sign * (dec_d + dec_m / 60.0 + dec_s / 3600.0)
    else:
        dec_deg = 0.0
    
    return ra_deg, dec_deg

def main():
    # 读取 TOP 10 候选体
    with open('data/top10_v9.json', 'r') as f:
        top10 = json.load(f)
    
    print("为 v9.0 TOP 10 候选体生成 IR 图像查看链接...\n")
    
    ir_urls = []
    
    for i, cand in enumerate(top10, 1):
        anchor = cand['anchor']
        des = cand['designation']
        
        try:
            ra_deg, dec_deg = parse_designation(des)
            
            # 生成 URL
            urls = generate_ir_image_urls(anchor, ra_deg, dec_deg)
            urls['anchor'] = anchor
            urls['ra'] = ra_deg
            urls['dec'] = dec_deg
            ir_urls.append(urls)
            
            print(f"[{i}/10] {anchor} (RA={ra_deg:.3f}, Dec={dec_deg:.3f})")
            print(f"  2MASS: {urls['2mass_viewer']}")
            print(f"  WISE:  {urls['wise_viewer']}")
            print(f"  Simbad: {urls['simbad']}")
            print(f"  Aladin: {urls['aladin']}")
            print()
            
        except Exception as e:
            print(f"[{i}/10] {anchor} - 解析失败: {e}")
            ir_urls.append({"anchor": anchor, "error": str(e)})
    
    # 保存为 JSON
    with open('data/top10_v9_ir_urls.json', 'w') as f:
        json.dump(ir_urls, f, indent=2)
    
    # 同时生成 HTML 查看页面（方便人工检查）
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>v9.0 TOP 10 IR 图像查看器</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>v9.0 TOP 10 候选体 IR 图像查看器</h1>
    <p>点击链接在新标签页打开 IR 图像查看器。检查图像形态：<b>点源</b> = 可能是脉冲星/黑洞，<b>延展结构</b> = 可能是星系（AGN）或 YSO。</p>
    <table>
        <tr>
            <th>排名</th>
            <th>锚点</th>
            <th>RA (度)</th>
            <th>Dec (度)</th>
            <th>2MASS 图像</th>
            <th>WISE 图像</th>
            <th>Simbad</th>
            <th>Aladin Lite</th>
        </tr>
"""
    
    for i, item in enumerate(ir_urls, 1):
        if 'error' in item:
            html_content += f"""
        <tr>
            <td>{i}</td>
            <td>{item['anchor']}</td>
            <td colspan="6">解析失败: {item['error']}</td>
        </tr>
"""
        else:
            html_content += f"""
        <tr>
            <td>{i}</td>
            <td>{item['anchor']}</td>
            <td>{item['ra']:.3f}</td>
            <td>{item['dec']:.3f}</td>
            <td><a href="{item['2mass_viewer']}" target="_blank">查看 2MASS</a></td>
            <td><a href="{item['wise_viewer']}" target="_blank">查看 WISE</a></td>
            <td><a href="{item['simbad']}" target="_blank">Simbad</a></td>
            <td><a href="{item['aladin']}" target="_blank">Aladin</a></td>
        </tr>
"""
    
    html_content += """    </table>
</body>
</html>"""
    
    with open('data/top10_v9_ir_images.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ IR 图像链接已保存到 data/top10_v9_ir_urls.json")
    print(f"✅ HTML 查看页面已保存到 data/top10_v9_ir_images.html")
    print(f"\n请用浏览器打开 HTML 文件进行人工检查。")

if __name__ == '__main__':
    main()
