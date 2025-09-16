#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
点位效率差异性分析脚本
分析点位之间的效率差异
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def analyze_point_efficiency_variance(df):
    """
    分析点位之间的效率差异性
    """
    print("=" * 60)
    print("📍 点位效率差异性分析")
    print("=" * 60)
    
    # 效率指标列表
    efficiency_metrics = ['盒菜分拣效率', '总分拣效率', '盒菜上架效率', '总上架效率']
    
    # 检查效率指标是否存在
    available_metrics = [metric for metric in efficiency_metrics if metric in df.columns]
    if not available_metrics:
        print("⚠️ 未找到效率指标列")
        return
    
    print(f"✅ 找到效率指标: {available_metrics}")
    
    # 按点位分组分析效率
    point_stats = df.groupby('point_id')[available_metrics].agg([
        'count', 'mean', 'median', 'std', 'min', 'max'
    ]).round(4)
    
    print(f"\n📊 点位效率统计概览:")
    print(f"   总点位数量: {df['point_id'].nunique()}")
    print(f"   有效数据点位: {len(point_stats)}")
    
    return point_stats, available_metrics

def analyze_efficiency_distribution(point_stats, metrics):
    """
    分析效率分布情况
    """
    print("\n" + "=" * 60)
    print("📈 效率分布分析")
    print("=" * 60)
    
    for metric in metrics:
        print(f"\n📊 {metric}分布分析:")
        
        # 计算整体统计
        overall_stats = point_stats[metric]
        mean_val = overall_stats['mean'].mean()
        median_val = overall_stats['median'].median()
        std_val = overall_stats['std'].mean()
        min_val = overall_stats['min'].min()
        max_val = overall_stats['max'].max()
        
        print(f"   整体均值: {mean_val:.4f}")
        print(f"   整体中位数: {median_val:.4f}")
        print(f"   整体标准差: {std_val:.4f}")
        print(f"   最小值: {min_val:.4f}")
        print(f"   最大值: {max_val:.4f}")
        print(f"   变异系数: {(std_val/mean_val*100):.2f}%")
        
        # 计算分位数
        q25 = overall_stats['mean'].quantile(0.25)
        q75 = overall_stats['mean'].quantile(0.75)
        iqr = q75 - q25
        print(f"   25分位数: {q25:.4f}")
        print(f"   75分位数: {q75:.4f}")
        print(f"   四分位距: {iqr:.4f}")

def rank_points_by_efficiency(point_stats, metrics):
    """
    按效率指标对点位进行排名
    """
    print("\n" + "=" * 60)
    print("🏆 点位效率排名")
    print("=" * 60)
    
    for metric in metrics:
        print(f"\n📈 {metric}排名 (前10名):")
        
        # 按平均效率排序
        sorted_points = point_stats[metric]['mean'].sort_values(ascending=False)
        
        print(f"   排名  点位ID    平均效率    中位数    标准差    数据量")
        print(f"   " + "-" * 60)
        
        for i, (point_id, efficiency) in enumerate(sorted_points.head(10).items(), 1):
            point_data = point_stats.loc[point_id, metric]
            print(f"   {i:2d}.  {str(point_id):8s}  {efficiency:.4f}    {point_data['median']:.4f}    {point_data['std']:.4f}    {point_data['count']:3.0f}")
        
        print(f"\n📉 {metric}排名 (后10名):")
        print(f"   排名  点位ID    平均效率    中位数    标准差    数据量")
        print(f"   " + "-" * 60)
        
        for i, (point_id, efficiency) in enumerate(sorted_points.tail(10).items(), 1):
            point_data = point_stats.loc[point_id, metric]
            print(f"   {i:2d}.  {str(point_id):8s}  {efficiency:.4f}    {point_data['median']:.4f}    {point_data['std']:.4f}    {point_data['count']:3.0f}")

def analyze_efficiency_variance(point_stats, metrics):
    """
    分析效率差异性
    """
    print("\n" + "=" * 60)
    print("🔍 效率差异性分析")
    print("=" * 60)
    
    for metric in metrics:
        print(f"\n📊 {metric}差异性分析:")
        
        # 计算差异性指标
        mean_values = point_stats[metric]['mean']
        median_values = point_stats[metric]['median']
        
        # 基本统计
        overall_mean = mean_values.mean()
        overall_std = mean_values.std()
        overall_min = mean_values.min()
        overall_max = mean_values.max()
        overall_range = overall_max - overall_min
        
        # 变异系数
        cv = (overall_std / overall_mean) * 100 if overall_mean != 0 else 0
        
        # 四分位距
        q25 = mean_values.quantile(0.25)
        q75 = mean_values.quantile(0.75)
        iqr = q75 - q25
        
        print(f"   点位数量: {len(mean_values)}")
        print(f"   平均效率: {overall_mean:.4f}")
        print(f"   标准差: {overall_std:.4f}")
        print(f"   变异系数: {cv:.2f}%")
        print(f"   最小值: {overall_min:.4f}")
        print(f"   最大值: {overall_max:.4f}")
        print(f"   极差: {overall_range:.4f}")
        print(f"   25分位数: {q25:.4f}")
        print(f"   75分位数: {q75:.4f}")
        print(f"   四分位距: {iqr:.4f}")
        
        # 效率差异倍数
        if overall_min > 0:
            max_min_ratio = overall_max / overall_min
            print(f"   最高/最低效率比: {max_min_ratio:.2f}倍")
        
        # 效率分布区间
        print(f"   效率分布区间:")
        print(f"     低效率 (<Q25): {len(mean_values[mean_values < q25])}个点位 ({len(mean_values[mean_values < q25])/len(mean_values)*100:.1f}%)")
        print(f"     中等效率 (Q25-Q75): {len(mean_values[(mean_values >= q25) & (mean_values <= q75)])}个点位 ({len(mean_values[(mean_values >= q25) & (mean_values <= q75)])/len(mean_values)*100:.1f}%)")
        print(f"     高效率 (>Q75): {len(mean_values[mean_values > q75])}个点位 ({len(mean_values[mean_values > q75])/len(mean_values)*100:.1f}%)")

def identify_outlier_points(point_stats, metrics):
    """
    识别异常点位
    """
    print("\n" + "=" * 60)
    print("🚨 异常点位识别")
    print("=" * 60)
    
    for metric in metrics:
        print(f"\n📊 {metric}异常点位:")
        
        mean_values = point_stats[metric]['mean']
        
        # 使用IQR方法识别异常值
        Q1 = mean_values.quantile(0.25)
        Q3 = mean_values.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # 找出异常值
        outliers_low = mean_values[mean_values < lower_bound]
        outliers_high = mean_values[mean_values > upper_bound]
        
        print(f"   异常值标准: < {lower_bound:.4f} 或 > {upper_bound:.4f}")
        print(f"   低效率异常点位: {len(outliers_low)}个")
        if len(outliers_low) > 0:
            print(f"     最低效率点位: {outliers_low.index[0]} ({outliers_low.iloc[0]:.4f})")
        
        print(f"   高效率异常点位: {len(outliers_high)}个")
        if len(outliers_high) > 0:
            print(f"     最高效率点位: {outliers_high.index[-1]} ({outliers_high.iloc[-1]:.4f})")

def analyze_efficiency_correlation(point_stats, metrics):
    """
    分析效率指标之间的相关性
    """
    print("\n" + "=" * 60)
    print("🔗 效率指标相关性分析")
    print("=" * 60)
    
    # 提取平均效率值
    efficiency_data = pd.DataFrame()
    for metric in metrics:
        efficiency_data[metric] = point_stats[metric]['mean']
    
    # 计算相关性矩阵
    correlation_matrix = efficiency_data.corr()
    
    print(f"\n📊 效率指标相关性矩阵:")
    print(correlation_matrix.round(3))
    
    # 分析强相关关系
    print(f"\n💡 强相关关系 (|r| > 0.7):")
    for i in range(len(metrics)):
        for j in range(i+1, len(metrics)):
            corr_value = correlation_matrix.iloc[i, j]
            if abs(corr_value) > 0.7:
                relationship = "正相关" if corr_value > 0 else "负相关"
                print(f"   {metrics[i]} ↔ {metrics[j]}: {corr_value:.3f} ({relationship})")

def save_point_analysis_results(point_stats, file_path):
    """
    保存点位分析结果
    """
    print("\n" + "=" * 60)
    print("💾 保存点位分析结果")
    print("=" * 60)
    
    # 创建结果文件名
    result_path = file_path.replace('.xlsx', '_point_efficiency_analysis.xlsx')
    
    try:
        # 保存点位统计结果
        point_stats.to_excel(result_path)
        print(f"✅ 成功保存点位效率分析结果到: {result_path}")
        print(f"📊 数据形状: {point_stats.shape}")
        
        return result_path
        
    except Exception as e:
        print(f"❌ 保存数据时出错: {e}")
        return None

def main():
    """
    主函数
    """
    # 文件路径
    file_path = "data/点位耗时_with_shifts_driver_efficiency_analysis.xlsx"
    
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
        efficiency_metrics = ['盒菜分拣效率', '总分拣效率', '盒菜上架效率', '总上架效率']
        df = df.dropna(subset=['point_id'] + efficiency_metrics)
        print(f"📈 处理后数据形状: {df.shape}")
        
        # 分析点位效率差异性
        point_stats, available_metrics = analyze_point_efficiency_variance(df)
        
        # 分析效率分布
        analyze_efficiency_distribution(point_stats, available_metrics)
        
        # 点位效率排名
        rank_points_by_efficiency(point_stats, available_metrics)
        
        # 分析效率差异性
        analyze_efficiency_variance(point_stats, available_metrics)
        
        # 识别异常点位
        identify_outlier_points(point_stats, available_metrics)
        
        # 分析效率相关性
        analyze_efficiency_correlation(point_stats, available_metrics)
        
        # 保存分析结果
        result_path = save_point_analysis_results(point_stats, file_path)
        
        if result_path:
            print("\n" + "=" * 60)
            print("🎯 总结")
            print("=" * 60)
            print("点位效率差异性分析完成:")
            print("1. 分析了各效率指标的分布情况")
            print("2. 识别了高效和低效点位")
            print("3. 计算了效率差异性指标")
            print("4. 发现了异常点位")
            print("5. 分析了效率指标间的相关性")
            print("6. 保存了详细的分析结果")
        
    except Exception as e:
        print(f"❌ 处理数据时出错: {e}")

if __name__ == "__main__":
    main()
