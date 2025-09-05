#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
司机效率分析脚本
排除行驶时间，只分析点位内的操作效率
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def analyze_driver_efficiency(df):
    """
    分析司机效率，排除行驶时间
    """
    print("=" * 60)
    print("👨‍💼 司机效率分析 (排除行驶时间)")
    print("=" * 60)
    
    # 司机列名
    driver_columns = [col for col in df.columns if '司机' in col or 'driver' in col.lower()]
    if not driver_columns:
        print("⚠️ 未找到司机相关列")
        return
    
    driver_col = driver_columns[0]
    print(f"✅ 找到司机列: {driver_col}")
    
    # 计算效率指标 (如果不存在则计算)
    # 使用正确的列名
    df['分拣时间'] = df['分拣时长(完成分拣时间-开始分拣时间)']
    df['上架时间'] = df['点位上架时长(点位完成上架时间-点位开始上架时间)']
    
    
    
    # 司机基本信息
    print(f"\n📊 司机基本信息:")
    print(f"   司机总数: {df[driver_col].nunique()}")
    print(f"   司机列表: {list(df[driver_col].unique())}")
    
    # 司机效率统计
    driver_stats = df.groupby(driver_col).agg({
        'point_id': 'count',  # 处理点位数量
        '点位耗时': ['mean', 'median', 'min', 'max'],
        '分拣时间': ['mean', 'median'],
        '上架时间': ['mean', 'median'],
        '盒菜数量': ['sum', 'mean'],
        '饮料数量': ['sum', 'mean'],
        '甜品数量': ['sum', 'mean'],
        '总分拣数': ['sum', 'mean'],
        '盒菜分拣效率': ['mean', 'median'],
        '总分拣效率': ['mean', 'median'],
        '盒菜上架效率': ['mean', 'median'],
        '总上架效率': ['mean', 'median']
    }).round(4)
    
    print(f"\n📈 司机效率统计:")
    print(driver_stats)
    
    return df, driver_stats

def rank_driver_efficiency(driver_stats):
    """
    司机效率排名
    """
    print("\n" + "=" * 60)
    print("🏆 司机效率排名")
    print("=" * 60)
    
    # 点位耗时排名 (越低越好)
    print("\n⏱️ 点位耗时排名 (平均耗时，越低越好):")
    avg_point_time = driver_stats[('点位耗时', 'mean')].sort_values()
    for i, (driver, time) in enumerate(avg_point_time.items(), 1):
        print(f"   {i}. {driver}: {time:.4f}分钟")
    
    # 分拣效率排名 (越高越好)
    print("\n📦 分拣效率排名 (平均总分拣效率，越高越好):")
    avg_sort_efficiency = driver_stats[('总分拣效率', 'mean')].sort_values(ascending=False)
    for i, (driver, efficiency) in enumerate(avg_sort_efficiency.items(), 1):
        print(f"   {i}. {driver}: {efficiency:.4f}件/分钟")
    
    # 上架效率排名 (越高越好)
    print("\n📋 上架效率排名 (平均总上架效率，越高越好):")
    avg_shelf_efficiency = driver_stats[('总上架效率', 'mean')].sort_values(ascending=False)
    for i, (driver, efficiency) in enumerate(avg_shelf_efficiency.items(), 1):
        print(f"   {i}. {driver}: {efficiency:.4f}件/分钟")
    
    # 盒菜分拣效率排名
    print("\n🥘 盒菜分拣效率排名 (平均盒菜分拣效率，越高越好):")
    avg_box_sort_efficiency = driver_stats[('盒菜分拣效率', 'mean')].sort_values(ascending=False)
    for i, (driver, efficiency) in enumerate(avg_box_sort_efficiency.items(), 1):
        print(f"   {i}. {driver}: {efficiency:.4f}盒/分钟")
    
    # 盒菜上架效率排名
    print("\n🥘 盒菜上架效率排名 (平均盒菜上架效率，越高越好):")
    avg_box_shelf_efficiency = driver_stats[('盒菜上架效率', 'mean')].sort_values(ascending=False)
    for i, (driver, efficiency) in enumerate(avg_box_shelf_efficiency.items(), 1):
        print(f"   {i}. {driver}: {efficiency:.4f}盒/分钟")

def analyze_driver_outliers(df, driver_col):
    """
    分析司机异常值
    """
    print("\n" + "=" * 60)
    print("🚨 司机异常值分析")
    print("=" * 60)
    
    # 计算各指标的异常值
    metrics = ['点位耗时', '分拣时长(完成分拣时间-开始分拣时间)', '点位上架时长(点位完成上架时间-点位开始上架时间)', '盒菜分拣效率', '总分拣效率', '盒菜上架效率', '总上架效率']
    
    for metric in metrics:
        if metric in df.columns:
            print(f"\n📊 {metric}异常值分析:")
            
            # 计算IQR
            Q1 = df[metric].quantile(0.25)
            Q3 = df[metric].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            # 按司机统计异常值
            outliers_by_driver = df[(df[metric] < lower_bound) | (df[metric] > upper_bound)].groupby(driver_col).size()
            
            if len(outliers_by_driver) > 0:
                print(f"   异常值标准: < {lower_bound:.4f} 或 > {upper_bound:.4f}")
                for driver, count in outliers_by_driver.items():
                    print(f"   {driver}: {count}条异常记录")
            else:
                print("   无异常值")

def analyze_driver_workload_distribution(driver_stats):
    """
    分析司机工作量分布
    """
    print("\n" + "=" * 60)
    print("📊 司机工作量分布")
    print("=" * 60)
    
    # 处理点位数量分布
    point_counts = driver_stats[('point_id', 'count')].sort_values(ascending=False)
    print("\n📍 处理点位数量排名:")
    for i, (driver, count) in enumerate(point_counts.items(), 1):
        print(f"   {i}. {driver}: {count}个点位")
    
    # 总分拣数分布
    total_sort_counts = driver_stats[('总分拣数', 'sum')].sort_values(ascending=False)
    print("\n📦 总分拣数排名:")
    for i, (driver, count) in enumerate(total_sort_counts.items(), 1):
        print(f"   {i}. {driver}: {count:.4f}件")
    
    # 平均单点位货物量
    avg_cargo_per_point = driver_stats[('总分拣数', 'mean')].sort_values(ascending=False)
    print("\n📦 平均单点位货物量排名:")
    for i, (driver, avg) in enumerate(avg_cargo_per_point.items(), 1):
        print(f"   {i}. {driver}: {avg:.4f}件/点位")

def analyze_driver_efficiency_factors(df, driver_col):
    """
    分析影响司机效率的因素
    """
    print("\n" + "=" * 60)
    print("🔍 司机效率影响因素分析")
    print("=" * 60)
    
    # 货物数量与效率的关系
    print("\n📊 货物数量与效率关系:")
    for driver in df[driver_col].unique():
        driver_data = df[df[driver_col] == driver]
        if len(driver_data) > 10:  # 只分析有足够数据的司机
            correlation = driver_data['总分拣数'].corr(driver_data['点位耗时'])
            print(f"   {driver}: 货物数量与点位耗时相关系数 = {correlation:.4f}")
    
    # 分拣时间与上架时间比例
    print("\n⏱️ 分拣时间与上架时间比例:")
    for driver in df[driver_col].unique():
        driver_data = df[df[driver_col] == driver]
        if len(driver_data) > 0:
            avg_sort_time = driver_data['分拣时间'].mean()
            avg_shelf_time = driver_data['上架时间'].mean()
            ratio = avg_sort_time / avg_shelf_time if avg_shelf_time > 0 else 0
            print(f"   {driver}: 分拣/上架时间比例 = {ratio:.4f}")

def propose_driver_optimization(driver_stats):
    """
    提出司机优化建议
    """
    print("\n" + "=" * 60)
    print("💡 司机优化建议")
    print("=" * 60)
    
    # 找出各维度的最佳和最差司机
    best_point_time = driver_stats[('点位耗时', 'mean')].idxmin()
    worst_point_time = driver_stats[('点位耗时', 'mean')].idxmax()
    
    best_sort_efficiency = driver_stats[('总分拣效率', 'mean')].idxmax()
    worst_sort_efficiency = driver_stats[('总分拣效率', 'mean')].idxmin()
    
    best_shelf_efficiency = driver_stats[('总上架效率', 'mean')].idxmax()
    worst_shelf_efficiency = driver_stats[('总上架效率', 'mean')].idxmin()
    
    print(f"\n🏆 各维度最佳司机:")
    print(f"   点位耗时最短: {best_point_time}")
    print(f"   分拣效率最高: {best_sort_efficiency}")
    print(f"   上架效率最高: {best_shelf_efficiency}")
    
    print(f"\n⚠️ 各维度需要改进的司机:")
    print(f"   点位耗时最长: {worst_point_time}")
    print(f"   分拣效率最低: {worst_sort_efficiency}")
    print(f"   上架效率最低: {worst_shelf_efficiency}")
    
    # 计算效率差异
    point_time_diff = driver_stats[('点位耗时', 'mean')].max() - driver_stats[('点位耗时', 'mean')].min()
    sort_efficiency_diff = driver_stats[('总分拣效率', 'mean')].max() - driver_stats[('总分拣效率', 'mean')].min()
    shelf_efficiency_diff = driver_stats[('总上架效率', 'mean')].max() - driver_stats[('总上架效率', 'mean')].min()
    
    print(f"\n📈 效率差异分析:")
    print(f"   点位耗时差异: {point_time_diff:.4f}分钟")
    print(f"   分拣效率差异: {sort_efficiency_diff:.4f}件/分钟")
    print(f"   上架效率差异: {shelf_efficiency_diff:.4f}件/分钟")

def save_driver_analysis_results(df, driver_stats, file_path):
    """
    保存司机分析结果
    """
    print("\n" + "=" * 60)
    print("💾 保存司机分析结果")
    print("=" * 60)
    
    # 创建结果文件名
    result_path = file_path.replace('.xlsx', '_driver_efficiency_analysis.xlsx')
    
    try:
        # 保存更新后的数据
        df.to_excel(result_path, index=False)
        print(f"✅ 成功保存司机效率分析结果到: {result_path}")
        print(f"📊 数据形状: {df.shape}")
        print(f"📋 新增效率指标: 盒菜分拣效率, 总分拣效率, 盒菜上架效率, 总上架效率")
        
        return result_path
        
    except Exception as e:
        print(f"❌ 保存数据时出错: {e}")
        return None

def main():
    """
    主函数
    """
    # 文件路径
    file_path = "data/点位耗时_with_shifts.xlsx"
    
    # 检查文件是否存在
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        return
    
    try:
        # 读取Excel文件
        print("📖 读取数据...")
        df = pd.read_excel(file_path)
        print(f"✅ 成功读取数据: {df.shape}")
        
        # 处理缺失值
        df = df.dropna(subset=['car_number', '点位耗时', '分拣时长(完成分拣时间-开始分拣时间)', '点位上架时长(点位完成上架时间-点位开始上架时间)', '盒菜数量', '总分拣数'])
        print(f"📈 处理后数据形状: {df.shape}")
        
        # 分析司机效率
        df, driver_stats = analyze_driver_efficiency(df)
        
        # 司机效率排名
        rank_driver_efficiency(driver_stats)
        
        # 分析司机异常值
        driver_col = [col for col in df.columns if '司机' in col or 'driver' in col.lower()][0]
        analyze_driver_outliers(df, driver_col)
        
        # 分析工作量分布
        analyze_driver_workload_distribution(driver_stats)
        
        # 分析效率影响因素
        analyze_driver_efficiency_factors(df, driver_col)
        
        # 提出优化建议
        propose_driver_optimization(driver_stats)
        
        # 保存分析结果
        result_path = save_driver_analysis_results(df, driver_stats, file_path)
        
        if result_path:
            print("\n" + "=" * 60)
            print("🎯 总结")
            print("=" * 60)
            print("司机效率分析完成:")
            print("1. 成功计算各维度效率指标")
            print("2. 分析了司机效率排名和差异")
            print("3. 识别了异常值和影响因素")
            print("4. 提出了针对性的优化建议")
            print("5. 保存了详细的分析结果")
        
    except Exception as e:
        print(f"❌ 处理数据时出错: {e}")

if __name__ == "__main__":
    main()
