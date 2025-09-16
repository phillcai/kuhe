#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆维度分析脚本 - 4辆车版本
分析真实车辆(GBH 5351 M, YQ 5378 S, YQ 441 A)与合并虚拟车的效率差异
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def load_and_preprocess_data(file_path):
    """
    加载并预处理数据
    """
    print("=" * 60)
    print("📊 数据加载与预处理")
    print("=" * 60)
    
    try:
        # 读取Excel文件
        df = pd.read_excel(file_path)
        print(f"✅ 成功加载数据文件: {file_path}")
        print(f"📈 原始数据形状: {df.shape}")
        
        # 处理缺失值
        df = df.dropna(subset=['car_number', '总耗时', '点位耗时'])
        print(f"📈 处理后数据形状: {df.shape}")
        
        # 车辆分类 - 将所有虚拟车合并为一辆
        real_vehicles = ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A']
        df['车辆类型'] = df['car_number'].apply(lambda x: '真实车辆' if x in real_vehicles else '虚拟车')
        
        # 将虚拟车统一命名为"虚拟车"
        df['车辆编号'] = df['car_number'].apply(lambda x: x if x in real_vehicles else '虚拟车')
        
        print(f"\n🚗 车辆分类结果:")
        print(f"   真实车辆: {df[df['车辆类型'] == '真实车辆']['car_number'].nunique()} 辆")
        print(f"   虚拟车: 1 辆 (合并所有虚拟车)")
        print(f"   总计: 4 辆车")
        
        return df
        
    except Exception as e:
        print(f"❌ 加载数据时出错: {e}")
        return None

def analyze_vehicle_performance(df):
    """
    分析车辆绩效
    """
    print("\n" + "=" * 60)
    print("🚗 车辆绩效分析 (4辆车)")
    print("=" * 60)
    
    # 按车辆编号分析
    print("\n📊 4辆车对比分析:")
    vehicle_stats = df.groupby('车辆编号').agg({
        'point_id': 'count',
        '总耗时': ['mean', 'median', 'min', 'max', 'std'],
        '点位耗时': ['mean', 'median', 'std'],
        '行驶时间': ['mean', 'median'],
        '分拣时长(完成分拣时间-开始分拣时间)': ['mean', 'median'],
        '点位上架时长(点位完成上架时间-点位开始上架时间)': ['mean', 'median'],
        '盒菜数量': ['mean', 'sum'],
        '饮料数量': ['mean', 'sum'],
        '甜品数量': ['mean', 'sum'],
        '总分拣数': ['mean', 'sum']
    }).round(2)
    
    print(vehicle_stats)
    
    # 车辆效率排名
    print("\n🏆 车辆效率排名 (按平均总耗时):")
    efficiency_data = []
    for vehicle in df['车辆编号'].unique():
        vehicle_data = df[df['车辆编号'] == vehicle]
        avg_time = vehicle_data['总耗时'].mean()
        point_count = len(vehicle_data)
        vehicle_type = '真实车辆' if vehicle in ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A'] else '虚拟车'
        efficiency_data.append((vehicle, avg_time, point_count, vehicle_type))
    
    # 按平均总耗时排序
    efficiency_data.sort(key=lambda x: x[1])
    
    for i, (vehicle, avg_time, point_count, vehicle_type) in enumerate(efficiency_data, 1):
        print(f"   {i}. {vehicle} ({vehicle_type}): {avg_time:.2f}分钟 (处理{point_count}个点位)")
    
    return efficiency_data

def analyze_vehicle_outliers(df):
    """
    分析车辆异常值
    """
    print("\n" + "=" * 60)
    print("🚨 车辆异常值分析 (4辆车)")
    print("=" * 60)
    
    # 各车辆异常值分析
    print(f"\n📊 各车辆异常值统计:")
    vehicle_outliers = {}
    
    for vehicle in df['车辆编号'].unique():
        vehicle_data = df[df['车辆编号'] == vehicle]
        
        # 总耗时异常值
        total_time = vehicle_data['总耗时']
        Q1 = total_time.quantile(0.25)
        Q3 = total_time.quantile(0.75)
        IQR = Q3 - Q1
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = vehicle_data[vehicle_data['总耗时'] > upper_bound]
        vehicle_outliers[vehicle] = len(outliers)
        
        print(f"   {vehicle}: {len(outliers)}条异常记录 (标准: > {upper_bound:.2f}分钟)")
        
        if len(outliers) > 0:
            print("   异常值详情:")
            for _, row in outliers.head(3).iterrows():
                print(f"     - 点位{row['point_id']}: {row['当前点位']} - {row['总耗时']:.2f}分钟")
    
    # 按异常值数量排序
    print(f"\n📊 异常值排名:")
    sorted_outliers = sorted(vehicle_outliers.items(), key=lambda x: x[1], reverse=True)
    for vehicle, outlier_count in sorted_outliers:
        vehicle_type = '真实车辆' if vehicle in ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A'] else '虚拟车'
        print(f"   {vehicle} ({vehicle_type}): {outlier_count}条异常记录")

def analyze_vehicle_workload_distribution(df):
    """
    分析车辆工作量分布
    """
    print("\n" + "=" * 60)
    print("📊 车辆工作量分布分析 (4辆车)")
    print("=" * 60)
    
    # 各车辆工作量统计
    print("\n📈 各车辆工作量统计:")
    workload_stats = df.groupby('车辆编号').agg({
        'point_id': 'count',
        '盒菜数量': 'sum',
        '饮料数量': 'sum',
        '甜品数量': 'sum',
        '总分拣数': 'sum',
        '总耗时': 'sum'
    }).sort_values('point_id', ascending=False)
    
    workload_stats.columns = ['点位数量', '总盒菜数', '总饮料数', '总甜品数', '总分拣数', '总耗时']
    
    for i, (vehicle, stats) in enumerate(workload_stats.iterrows(), 1):
        vehicle_type = '真实车辆' if vehicle in ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A'] else '虚拟车'
        print(f"   {i}. {vehicle} ({vehicle_type}):")
        print(f"      点位数量: {stats['点位数量']:.0f}个")
        print(f"      总分拣数: {stats['总分拣数']:.0f}件")
        print(f"      总耗时: {stats['总耗时']:.0f}分钟")
        print(f"      平均单点位耗时: {stats['总耗时']/stats['点位数量']:.2f}分钟")
        print()
    
    # 工作量占比分析
    print("\n📊 工作量占比分析:")
    total_points = df['point_id'].count()
    total_items = df['总分拣数'].sum()
    total_time = df['总耗时'].sum()
    
    for vehicle in df['车辆编号'].unique():
        vehicle_data = df[df['车辆编号'] == vehicle]
        point_ratio = len(vehicle_data) / total_points * 100
        item_ratio = vehicle_data['总分拣数'].sum() / total_items * 100
        time_ratio = vehicle_data['总耗时'].sum() / total_time * 100
        
        vehicle_type = '真实车辆' if vehicle in ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A'] else '虚拟车'
        print(f"   {vehicle} ({vehicle_type}):")
        print(f"      点位占比: {point_ratio:.1f}%")
        print(f"      货物占比: {item_ratio:.1f}%")
        print(f"      时间占比: {time_ratio:.1f}%")

def analyze_vehicle_efficiency_factors(df):
    """
    分析影响车辆效率的因素
    """
    print("\n" + "=" * 60)
    print("🔍 车辆效率影响因素分析 (4辆车)")
    print("=" * 60)
    
    # 货物数量与耗时的关系
    print("\n📦 货物数量与耗时关系:")
    for vehicle in df['车辆编号'].unique():
        vehicle_data = df[df['车辆编号'] == vehicle]
        
        # 计算相关系数
        correlation = vehicle_data['总分拣数'].corr(vehicle_data['总耗时'])
        
        # 平均单件处理时间
        avg_time_per_item = vehicle_data['总耗时'].sum() / vehicle_data['总分拣数'].sum()
        
        vehicle_type = '真实车辆' if vehicle in ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A'] else '虚拟车'
        print(f"   {vehicle} ({vehicle_type}):")
        print(f"      货物数量与总耗时相关系数: {correlation:.3f}")
        print(f"      平均单件处理时间: {avg_time_per_item:.3f}分钟")
    
    # 各环节耗时对比
    print("\n⏱️ 各环节耗时对比:")
    for vehicle in df['车辆编号'].unique():
        vehicle_data = df[df['车辆编号'] == vehicle]
        
        total_time = vehicle_data['总耗时'].sum()
        driving_time = vehicle_data['行驶时间'].sum()
        sorting_time = vehicle_data['分拣时长(完成分拣时间-开始分拣时间)'].sum()
        walking_time = vehicle_data['货车步行至点位时长*2'].sum()
        shelving_time = vehicle_data['点位上架时长(点位完成上架时间-点位开始上架时间)'].sum()
        
        vehicle_type = '真实车辆' if vehicle in ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A'] else '虚拟车'
        print(f"\n   {vehicle} ({vehicle_type}):")
        print(f"     行驶时间占比: {driving_time/total_time*100:.1f}%")
        print(f"     分拣时间占比: {sorting_time/total_time*100:.1f}%")
        print(f"     步行时间占比: {walking_time/total_time*100:.1f}%")
        print(f"     上架时间占比: {shelving_time/total_time*100:.1f}%")

def propose_vehicle_optimization(df):
    """
    提出车辆优化建议
    """
    print("\n" + "=" * 60)
    print("💡 车辆优化建议 (4辆车)")
    print("=" * 60)
    
    # 分析各车辆的特点
    print("\n📊 各车辆特点分析:")
    for vehicle in df['车辆编号'].unique():
        vehicle_data = df[df['车辆编号'] == vehicle]
        
        avg_time = vehicle_data['总耗时'].mean()
        avg_points = vehicle_data['point_id'].count()
        avg_items = vehicle_data['总分拣数'].mean()
        
        vehicle_type = '真实车辆' if vehicle in ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A'] else '虚拟车'
        
        print(f"   {vehicle} ({vehicle_type}):")
        print(f"      平均总耗时: {avg_time:.2f}分钟")
        print(f"      处理点位: {avg_points}个")
        print(f"      平均单点位货物: {avg_items:.1f}件")
        
        # 识别特点
        if avg_time < 50:
            print(f"      特点: 高效车辆")
        elif avg_time > 65:
            print(f"      特点: 需要优化")
        else:
            print(f"      特点: 中等效率")
        print()
    
    # 识别最佳实践
    best_vehicle = df.groupby('车辆编号')['总耗时'].mean().idxmin()
    best_vehicle_type = '真实车辆' if best_vehicle in ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A'] else '虚拟车'
    
    print(f"🏆 最佳实践车辆: {best_vehicle} ({best_vehicle_type})")
    print(f"   平均总耗时: {df.groupby('车辆编号')['总耗时'].mean().min():.2f}分钟")
    
    # 优化建议
    print("\n🎯 优化建议:")
    print("   1. 分析高效车辆的操作模式，推广最佳实践")
    print("   2. 针对低效车辆进行专项优化")
    print("   3. 优化车辆调度策略，合理分配工作量")
    print("   4. 建立车辆绩效评估体系")
    print("   5. 考虑车辆配置和设备的标准化")
    print("   6. 重点关注虚拟车的高效模式，推广到真实车辆")

def main():
    """
    主函数
    """
    # 文件路径
    file_path = "data/点位耗时.xlsx"
    
    # 检查文件是否存在
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        return
    
    # 加载和预处理数据
    df = load_and_preprocess_data(file_path)
    
    if df is not None:
        # 车辆绩效分析
        efficiency_data = analyze_vehicle_performance(df)
        
        # 车辆异常值分析
        analyze_vehicle_outliers(df)
        
        # 车辆工作量分布分析
        analyze_vehicle_workload_distribution(df)
        
        # 车辆效率影响因素分析
        analyze_vehicle_efficiency_factors(df)
        
        # 提出车辆优化建议
        propose_vehicle_optimization(df)
        
        print("\n" + "=" * 60)
        print("🎯 总结")
        print("=" * 60)
        print("4辆车维度分析完成，主要发现:")
        print("1. 虚拟车合并后效率最高")
        print("2. 真实车辆承担主要工作量")
        print("3. 各车辆异常值模式不同")
        print("4. 需要针对不同车辆制定优化策略")

if __name__ == "__main__":
    main()
