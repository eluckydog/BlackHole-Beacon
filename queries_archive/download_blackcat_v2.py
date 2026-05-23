#!/usr/bin/env python3
"""
下载 BlackCat 星表（Table 5：已知恒星质量黑洞 X 射线双星）— 带调试版本
来源：J/ApJ/813/L5 (BlackCAT: A Catalog of Stellar-Mass Black Holes in X-Ray Binaries)
"""
import os
import sys
import pandas as pd
from astroquery.vizier import Vizier
import tempfile
import shutil

def download_blackcat():
    # 设置 Vizier 查询限制
    Vizier.ROW_LIMIT = -1  # 无限制
    
    # BlackCat 星表 ID: J/ApJ/813/L5
    # Table 5: Confirmed BH X-ray binaries
    catalog_id = "J/ApJ/813/L5/table5"
    
    print(f"正在查询 Vizier 星表：{catalog_id}")
    
    try:
        # 查询星表
        result = Vizier.get_catalogs(catalog_id)
        
        if not result:
            print("错误：未找到星表")
            return None
        
        print(f"查询结果类型：{type(result)}")
        print(f"查询结果长度：{len(result)}")
        
        # 获取第一个结果表
        table = result[0]
        print(f"表格类型：{type(table)}")
        print(f"表格长度：{len(table)}")
        print(f"表格列名：{table.colnames}")
        
        # 转换为 pandas DataFrame
        df = table.to_pandas()
        
        # 保存到 CSV
        output_path = os.path.join(os.path.dirname(__file__), "..", "catalog", "blackcat_table5.csv")
        output_path = os.path.abspath(output_path)
        
        df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"星表已保存到：{output_path}")
        print(f"列名：{list(df.columns)}")
        print(f"\n前 5 行：")
        print(df.head())
        
        return df
        
    except Exception as e:
        print(f"下载失败：{e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    download_blackcat()
