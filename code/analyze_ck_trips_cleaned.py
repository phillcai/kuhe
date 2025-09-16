#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆回CK时间分析脚本 - 数据清理版本
分析CSV数据，提取每个车辆每次回CK的完整时间序列
去掉在CK停留时长最大和最小的10%，计算80分位数据
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

def clean_data_and_calculate_stats(csv_file, output_file='ck_trips_analysis_cleaned.csv'):
    """
    清理数据并计算统计信息
    
    Args:
        csv_file: 输入CSV文件路径
        output_file: 输出CSV文件名
    """
    # 读取CSV数据
    df = pd.read_csv(csv_file)
    
    # 过滤掉停留时长为N/A的记录
    df_clean = df[df['在CK停留时长(分钟)'] != 'N/A'].copy()
    df_clean['在CK停留时长(分钟)'] = pd.to_numeric(df_clean['在CK停留时长(分钟)'])
    
    print(f"原始数据记录数: {len(df)}")
    print(f"有效数据记录数: {len(df_clean)}")
    
    # 计算80分位数据（去掉最大和最小的10%）
    total_records = len(df_clean)
    remove_count = int(total_records * 0.1)  # 去掉10%
    
    if remove_count > 0:
        # 按停留时长排序
        df_sorted = df_clean.sort_values('在CK停留时长(分钟)')
        
        # 去掉最小的10%和最大的10%
        df_80_percentile = df_sorted.iloc[remove_count:total_records-remove_count].copy()
        
        print(f"去掉最小10%记录数: {remove_count}")
        print(f"去掉最大10%记录数: {remove_count}")
        print(f"80分位数据记录数: {len(df_80_percentile)}")
    else:
        df_80_percentile = df_clean.copy()
        print("数据量较少，未进行80分位处理")
    
    # 按车辆ID分组计算平均值
    stats_by_car = df_80_percentile.groupby('车辆ID')['在CK停留时长(分钟)'].agg([
        'count',  # 记录数
        'mean',   # 平均值
        'std',    # 标准差
        'min',    # 最小值
        'max'     # 最大值
    ]).round(2)
    
    # 计算总体平均值
    overall_mean = df_80_percentile['在CK停留时长(分钟)'].mean()
    overall_count = len(df_80_percentile)
    
    print(f"\n各车辆在CK停留时长统计（80分位数据）:")
    print("=" * 60)
    print(f"{'车辆ID':<8} {'记录数':<8} {'平均时长(分钟)':<15} {'标准差':<10} {'最小值':<8} {'最大值':<8}")
    print("-" * 60)
    
    for car_id, row in stats_by_car.iterrows():
        print(f"{car_id:<8} {row['count']:<8} {row['mean']:<15} {row['std']:<10} {row['min']:<8} {row['max']:<8}")
    
    print("-" * 60)
    print(f"{'总计':<8} {overall_count:<8} {overall_mean:<15.2f}")
    
    # 保存清理后的数据
    df_80_percentile.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n清理后的数据已保存到: {output_file}")
    
    # 保存统计结果
    stats_file = 'ck_trips_stats_summary.csv'
    stats_summary = stats_by_car.copy()
    stats_summary.loc['总计'] = [overall_count, overall_mean, df_80_percentile['在CK停留时长(分钟)'].std(), 
                                df_80_percentile['在CK停留时长(分钟)'].min(), 
                                df_80_percentile['在CK停留时长(分钟)'].max()]
    
    stats_summary.to_csv(stats_file, encoding='utf-8-sig')
    print(f"统计结果已保存到: {stats_file}")
    
    return df_80_percentile, stats_by_car, overall_mean

def main():
    """主函数"""
    csv_file = 'ck_trips_analysis.csv'
    
    try:
        df_cleaned, stats, overall_mean = clean_data_and_calculate_stats(csv_file)
        
        print(f"\n数据清理完成！")
        print(f"总体平均在CK停留时长: {overall_mean:.2f} 分钟")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
