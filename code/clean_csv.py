#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理CSV文件脚本
"""

import csv
import sys

def clean_csv(input_file, output_file):
    """
    清理CSV文件中的特殊字符和格式问题
    """
    try:
        with open(input_file, 'r', encoding='utf-8-sig') as infile:
            reader = csv.reader(infile)
            
            # 读取所有数据
            rows = []
            for row in reader:
                # 清理每个单元格
                clean_row = []
                for cell in row:
                    # 转换为字符串并清理
                    cell_str = str(cell).strip()
                    clean_row.append(cell_str)
                rows.append(clean_row)
        
        print(f"✅ 成功读取 {len(rows)} 行数据（包括表头）")
        
        # 写入清理后的数据
        with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(rows)
        
        print(f"✅ 成功写入清理后的数据到: {output_file}")
        print(f"📋 列数: {len(rows[0]) if rows else 0}")
        print(f"📊 数据行数: {len(rows) - 1}")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理文件时出错: {e}")
        return False

if __name__ == "__main__":
    input_file = "data/点位耗时_1.csv"
    output_file = "data/点位耗时_cleaned.csv"
    
    print("=" * 60)
    print("🧹 开始清理CSV文件")
    print("=" * 60)
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print()
    
    if clean_csv(input_file, output_file):
        print("\n" + "=" * 60)
        print("✅ CSV文件清理完成")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ CSV文件清理失败")
        print("=" * 60)
        sys.exit(1)

