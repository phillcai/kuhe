#!/usr/bin/env python3
"""
合并 data 目录下的所有 multi_all_path_*.csv 文件
将合并后的数据保存为 multi_all_path.csv
"""

import pandas as pd
import glob
import os
from pathlib import Path

def merge_multi_path_csv():
    """合并所有 multi_all_path_*.csv 文件"""
    
    # 设置数据目录路径 (相对于项目根目录)
    # 使用绝对路径指定数据目录
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    
    # 查找所有匹配的CSV文件
    pattern = str(data_dir / "multi_all_path_*.csv")
    csv_files = glob.glob(pattern)
    
    if not csv_files:
        print("❌ 未找到任何 multi_all_path_*.csv 文件")
        return
    
    print(f"📁 找到 {len(csv_files)} 个文件:")
    for file in csv_files:
        file_size = os.path.getsize(file) / (1024 * 1024)  # MB
        print(f"  - {file} ({file_size:.1f} MB)")
    
    # 存储所有数据框
    dataframes = []
    total_rows = 0
    
    # 逐个读取文件
    for file_path in csv_files:
        print(f"\n📖 正在读取: {file_path}")
        try:
            # 读取CSV文件
            df = pd.read_csv(file_path)
            rows = len(df)
            print(f"  ✅ 成功读取 {rows:,} 行数据")
            
            # 显示列信息
            print(f"  📊 列名: {list(df.columns)}")
            
            dataframes.append(df)
            total_rows += rows
            
        except Exception as e:
            print(f"  ❌ 读取失败: {e}")
            continue
    
    if not dataframes:
        print("❌ 没有成功读取任何文件")
        return
    
    # 合并所有数据框
    print(f"\n🔄 正在合并 {len(dataframes)} 个数据框...")
    merged_df = pd.concat(dataframes, ignore_index=True)
    
    print(f"✅ 合并完成!")
    print(f"📈 总行数: {len(merged_df):,}")
    print(f"📊 列数: {len(merged_df.columns)}")
    print(f"📋 列名: {list(merged_df.columns)}")
    
    # 显示基本统计信息
    print(f"\n📋 数据概览:")
    print(f"  - 唯一请求ID数量: {merged_df['req_id'].nunique():,}")
    print(f"  - 平均路径时长: {merged_df['path_duration'].str.replace(',', '').astype(int).mean():.1f}")
    print(f"  - 平均销售损失: {merged_df['path_sale_loss'].mean():.2f}")
    print(f"  - 平均补货率: {merged_df['补货率'].mean():.3f}")
    
    # 保存合并后的文件
    output_file = data_dir / "multi_all_path.csv"
    print(f"\n💾 正在保存到: {output_file}")
    
    try:
        merged_df.to_csv(output_file, index=False)
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
        print(f"✅ 保存成功! 文件大小: {file_size:.1f} MB")
        print(f"📁 输出文件: {output_file}")
        
        # 验证保存的文件
        print(f"\n🔍 验证保存的文件...")
        verification_df = pd.read_csv(output_file)
        if len(verification_df) == len(merged_df):
            print(f"✅ 验证通过! 保存的文件包含 {len(verification_df):,} 行数据")
        else:
            print(f"⚠️  验证失败! 期望 {len(merged_df):,} 行，实际 {len(verification_df):,} 行")
            
    except Exception as e:
        print(f"❌ 保存失败: {e}")

if __name__ == "__main__":
    print("🚀 开始合并 multi_all_path_*.csv 文件...")
    merge_multi_path_csv()
    print("\n🎉 合并完成!") 