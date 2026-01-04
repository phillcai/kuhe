#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆回CK时间分析脚本 - 数据清理版本（修复版）
分析CSV数据，提取每个车辆每次回CK的完整时间序列
去掉在CK停留时长最大和最小的10%，计算80分位数据
使用标准库csv模块避免pandas兼容性问题
"""

import csv
import statistics
from datetime import datetime
import sys
import os
from collections import defaultdict

def read_csv_data(csv_file):
    """
    读取CSV数据
    
    Args:
        csv_file: CSV文件路径
    
    Returns:
        list: 数据行列表
    """
    data = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

def clean_data_and_calculate_stats(csv_file, output_file=None):
    """
    清理数据并计算统计信息
    
    Args:
        csv_file: 输入CSV文件路径
        output_file: 输出CSV文件名，如果为None则使用默认路径
    """
    # 如果未指定输出文件，使用脚本所在目录
    if output_file is None:
        script_dir = os.path.dirname(os.path.abspath(csv_file))
        output_file = os.path.join(script_dir, 'ck_trips_analysis_cleaned.csv')
    # 读取CSV数据
    data = read_csv_data(csv_file)
    
    # 过滤掉停留时长为N/A的记录并转换为数字
    clean_data = []
    for row in data:
        stay_time = row['在CK停留时长(分钟)']
        if stay_time != 'N/A' and stay_time.strip():
            try:
                stay_time_num = float(stay_time)
                row['在CK停留时长(分钟)'] = stay_time_num
                clean_data.append(row)
            except ValueError:
                continue
    
    print(f"原始数据记录数: {len(data)}")
    print(f"有效数据记录数: {len(clean_data)}")
    
    if len(clean_data) == 0:
        print("没有有效数据可处理")
        return [], {}, 0
    
    # 计算80分位数据（去掉最大和最小的10%）
    total_records = len(clean_data)
    remove_count = int(total_records * 0.1)  # 去掉10%
    
    if remove_count > 0 and total_records > 20:  # 确保有足够的数据
        # 按停留时长排序
        clean_data.sort(key=lambda x: x['在CK停留时长(分钟)'])
        
        # 去掉最小的10%和最大的10%
        percentile_80_data = clean_data[remove_count:total_records-remove_count]
        
        print(f"去掉最小10%记录数: {remove_count}")
        print(f"去掉最大10%记录数: {remove_count}")
        print(f"80分位数据记录数: {len(percentile_80_data)}")
    else:
        percentile_80_data = clean_data
        print("数据量较少，未进行80分位处理")
    
    # 按车辆ID分组计算统计信息
    car_stats = defaultdict(list)
    for row in percentile_80_data:
        car_id = int(row['车辆ID'])
        stay_time = row['在CK停留时长(分钟)']
        car_stats[car_id].append(stay_time)
    
    # 计算各车辆统计信息
    stats_by_car = {}
    for car_id, times in car_stats.items():
        if times:
            stats_by_car[car_id] = {
                'count': len(times),
                'mean': statistics.mean(times),
                'std': statistics.stdev(times) if len(times) > 1 else 0,
                'min': min(times),
                'max': max(times)
            }
    
    # 计算总体平均值
    all_times = [row['在CK停留时长(分钟)'] for row in percentile_80_data]
    overall_mean = statistics.mean(all_times)
    overall_count = len(percentile_80_data)
    
    print(f"\n各车辆在CK停留时长统计（80分位数据）:")
    print("=" * 60)
    print(f"{'车辆ID':<8} {'记录数':<8} {'平均时长(分钟)':<15} {'标准差':<10} {'最小值':<8} {'最大值':<8}")
    print("-" * 60)
    
    for car_id, stats in sorted(stats_by_car.items()):
        print(f"{car_id:<8} {stats['count']:<8} {stats['mean']:<15.2f} {stats['std']:<10.2f} {stats['min']:<8.0f} {stats['max']:<8.0f}")
    
    print("-" * 60)
    print(f"{'总计':<8} {overall_count:<8} {overall_mean:<15.2f}")
    
    # 保存清理后的数据
    if percentile_80_data:
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = percentile_80_data[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(percentile_80_data)
        print(f"\n清理后的数据已保存到: {output_file}")
    
    # 保存统计结果
    script_dir = os.path.dirname(os.path.abspath(output_file))
    stats_file = os.path.join(script_dir, 'ck_trips_stats_summary.csv')
    with open(stats_file, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['车辆ID', '记录数', '平均时长(分钟)', '标准差', '最小值', '最大值']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for car_id, stats in sorted(stats_by_car.items()):
            writer.writerow({
                '车辆ID': car_id,
                '记录数': stats['count'],
                '平均时长(分钟)': round(stats['mean'], 2),
                '标准差': round(stats['std'], 2),
                '最小值': stats['min'],
                '最大值': stats['max']
            })
        
        # 添加总计行
        overall_std = statistics.stdev(all_times) if len(all_times) > 1 else 0
        writer.writerow({
            '车辆ID': '总计',
            '记录数': overall_count,
            '平均时长(分钟)': round(overall_mean, 2),
            '标准差': round(overall_std, 2),
            '最小值': min(all_times),
            '最大值': max(all_times)
        })
    
    print(f"统计结果已保存到: {stats_file}")
    
    return percentile_80_data, stats_by_car, overall_mean

def main():
    """主函数"""
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(script_dir, 'ck_trips_analysis.csv')
    
    try:
        df_cleaned, stats, overall_mean = clean_data_and_calculate_stats(csv_file)
        
        print(f"\n数据清理完成！")
        print(f"总体平均在CK停留时长: {overall_mean:.2f} 分钟")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

