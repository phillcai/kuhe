#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用IQR排除异常数据，分析分拣和上架效率目标线
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def remove_outliers_with_iqr(df, metrics):
    """
    使用IQR方法排除异常数据
    """
    print("=" * 60)
    print("🔍 IQR异常值排除分析")
    print("=" * 60)
    
    df_clean = df.copy()
    outlier_counts = {}
    
    for metric in metrics:
        print(f"\n📊 {metric}异常值排除:")
        
        # 计算IQR
        Q1 = df[metric].quantile(0.25)
        Q3 = df[metric].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # 找出异常值
        outliers = df[(df[metric] < lower_bound) | (df[metric] > upper_bound)]
        outlier_count = len(outliers)
        outlier_counts[metric] = outlier_count
        
        print(f"   异常值标准: < {lower_bound:.4f} 或 > {upper_bound:.4f}")
        print(f"   异常值数量: {outlier_count}条 ({outlier_count/len(df)*100:.1f}%)")
        print(f"   保留数据: {len(df) - outlier_count}条")
        
        # 排除异常值
        df_clean = df_clean[(df_clean[metric] >= lower_bound) & (df_clean[metric] <= upper_bound)]
    
    print(f"\n📈 数据清理总结:")
    print(f"   原始数据: {len(df)}条")
    print(f"   清理后数据: {len(df_clean)}条")
    print(f"   排除异常值: {len(df) - len(df_clean)}条 ({(len(df) - len(df_clean))/len(df)*100:.1f}%)")
    
    return df_clean, outlier_counts

def analyze_efficiency_targets(df_clean, metrics):
    """
    分析效率目标线
    """
    print("\n" + "=" * 60)
    print("🎯 效率目标线分析")
    print("=" * 60)
    
    target_analysis = {}
    
    for metric in metrics:
        print(f"\n📊 {metric}目标线分析:")
        
        # 计算各种统计指标
        mean_val = df_clean[metric].mean()
        median_val = df_clean[metric].median()
        std_val = df_clean[metric].std()
        
        # 分位数
        q25 = df_clean[metric].quantile(0.25)
        q75 = df_clean[metric].quantile(0.75)
        q90 = df_clean[metric].quantile(0.90)
        q95 = df_clean[metric].quantile(0.95)
        
        # 计算目标线
        conservative_target = q75  # 75分位数作为保守目标
        moderate_target = q90      # 90分位数作为中等目标
        aggressive_target = q95    # 95分位数作为激进目标
        
        print(f"   基本统计:")
        print(f"     均值: {mean_val:.4f}")
        print(f"     中位数: {median_val:.4f}")
        print(f"     标准差: {std_val:.4f}")
        print(f"     25分位数: {q25:.4f}")
        print(f"     75分位数: {q75:.4f}")
        print(f"     90分位数: {q90:.4f}")
        print(f"     95分位数: {q95:.4f}")
        
        print(f"   目标线建议:")
        print(f"     保守目标 (Q75): {conservative_target:.4f}")
        print(f"     中等目标 (Q90): {moderate_target:.4f}")
        print(f"     激进目标 (Q95): {aggressive_target:.4f}")
        
        target_analysis[metric] = {
            'mean': mean_val,
            'median': median_val,
            'std': std_val,
            'q25': q25,
            'q75': q75,
            'q90': q90,
            'q95': q95,
            'conservative': conservative_target,
            'moderate': moderate_target,
            'aggressive': aggressive_target
        }
    
    return target_analysis

def compare_box_vs_total_efficiency(df_clean):
    """
    比较盒菜效率与总效率的差异
    """
    print("\n" + "=" * 60)
    print("📦 盒菜效率 vs 总效率对比分析")
    print("=" * 60)
    
    # 计算相关性
    box_sort_corr = df_clean['盒菜分拣效率'].corr(df_clean['总分拣效率'])
    box_shelf_corr = df_clean['盒菜上架效率'].corr(df_clean['总上架效率'])
    
    print(f"\n📊 效率指标相关性:")
    print(f"   盒菜分拣效率 ↔ 总分拣效率: {box_sort_corr:.3f}")
    print(f"   盒菜上架效率 ↔ 总上架效率: {box_shelf_corr:.3f}")
    
    # 计算盒菜占比
    df_clean['盒菜占比'] = df_clean['盒菜数量'] / df_clean['总分拣数']
    avg_box_ratio = df_clean['盒菜占比'].mean()
    
    print(f"\n📊 盒菜占比分析:")
    print(f"   平均盒菜占比: {avg_box_ratio:.2%}")
    print(f"   盒菜占比范围: {df_clean['盒菜占比'].min():.2%} - {df_clean['盒菜占比'].max():.2%}")
    
    # 分析盒菜占比与效率的关系
    box_ratio_sort_corr = df_clean['盒菜占比'].corr(df_clean['盒菜分拣效率'])
    box_ratio_total_sort_corr = df_clean['盒菜占比'].corr(df_clean['总分拣效率'])
    box_ratio_shelf_corr = df_clean['盒菜占比'].corr(df_clean['盒菜上架效率'])
    box_ratio_total_shelf_corr = df_clean['盒菜占比'].corr(df_clean['总上架效率'])
    
    print(f"\n📊 盒菜占比与效率关系:")
    print(f"   盒菜占比 ↔ 盒菜分拣效率: {box_ratio_sort_corr:.3f}")
    print(f"   盒菜占比 ↔ 总分拣效率: {box_ratio_total_sort_corr:.3f}")
    print(f"   盒菜占比 ↔ 盒菜上架效率: {box_ratio_shelf_corr:.3f}")
    print(f"   盒菜占比 ↔ 总上架效率: {box_ratio_total_shelf_corr:.3f}")
    
    # 分析不同盒菜占比区间的效率
    print(f"\n📊 不同盒菜占比区间的效率分析:")
    df_clean['盒菜占比区间'] = pd.cut(df_clean['盒菜占比'], 
                                   bins=[0, 0.5, 0.7, 0.9, 1.0], 
                                   labels=['低盒菜占比(<50%)', '中低盒菜占比(50-70%)', '中高盒菜占比(70-90%)', '高盒菜占比(>90%)'])
    
    for interval in df_clean['盒菜占比区间'].unique():
        if pd.notna(interval):
            interval_data = df_clean[df_clean['盒菜占比区间'] == interval]
            if len(interval_data) > 0:
                print(f"   {interval}:")
                print(f"     数据量: {len(interval_data)}条")
                print(f"     盒菜分拣效率: {interval_data['盒菜分拣效率'].mean():.4f}")
                print(f"     总分拣效率: {interval_data['总分拣效率'].mean():.4f}")
                print(f"     盒菜上架效率: {interval_data['盒菜上架效率'].mean():.4f}")
                print(f"     总上架效率: {interval_data['总上架效率'].mean():.4f}")

def recommend_target_metrics(target_analysis, df_clean):
    """
    推荐目标指标
    """
    print("\n" + "=" * 60)
    print("💡 目标指标推荐")
    print("=" * 60)
    
    # 计算盒菜占比
    avg_box_ratio = df_clean['盒菜数量'].sum() / df_clean['总分拣数'].sum()
    
    print(f"\n📊 业务背景分析:")
    print(f"   盒菜占比: {avg_box_ratio:.2%}")
    print(f"   业务特点: 点位补货以盒菜为主，附带补饮料甜品")
    print(f"   数据限制: 无分三个商品类型的时长数据")
    
    print(f"\n💡 目标指标推荐:")
    
    # 分析盒菜效率与总效率的相关性
    box_sort_corr = df_clean['盒菜分拣效率'].corr(df_clean['总分拣效率'])
    box_shelf_corr = df_clean['盒菜上架效率'].corr(df_clean['总上架效率'])
    
    print(f"\n📦 分拣阶段目标指标:")
    if box_sort_corr > 0.7:
        print(f"   ✅ 推荐使用'盒菜分拣效率'作为目标指标")
        print(f"   理由: 盒菜占比高({avg_box_ratio:.1%})，盒菜与总分拣效率强相关({box_sort_corr:.3f})")
        print(f"   保守目标: {target_analysis['盒菜分拣效率']['conservative']:.4f}")
        print(f"   中等目标: {target_analysis['盒菜分拣效率']['moderate']:.4f}")
        print(f"   激进目标: {target_analysis['盒菜分拣效率']['aggressive']:.4f}")
    else:
        print(f"   ⚠️ 建议同时关注'盒菜分拣效率'和'总分拣效率'")
        print(f"   理由: 盒菜与总分拣效率相关性中等({box_sort_corr:.3f})")
        print(f"   盒菜分拣效率目标: {target_analysis['盒菜分拣效率']['moderate']:.4f}")
        print(f"   总分拣效率目标: {target_analysis['总分拣效率']['moderate']:.4f}")
    
    print(f"\n📋 上架阶段目标指标:")
    if box_shelf_corr > 0.7:
        print(f"   ✅ 推荐使用'盒菜上架效率'作为目标指标")
        print(f"   理由: 盒菜占比高({avg_box_ratio:.1%})，盒菜与总上架效率强相关({box_shelf_corr:.3f})")
        print(f"   保守目标: {target_analysis['盒菜上架效率']['conservative']:.4f}")
        print(f"   中等目标: {target_analysis['盒菜上架效率']['moderate']:.4f}")
        print(f"   激进目标: {target_analysis['盒菜上架效率']['aggressive']:.4f}")
    else:
        print(f"   ⚠️ 建议同时关注'盒菜上架效率'和'总上架效率'")
        print(f"   理由: 盒菜与总上架效率相关性中等({box_shelf_corr:.3f})")
        print(f"   盒菜上架效率目标: {target_analysis['盒菜上架效率']['moderate']:.4f}")
        print(f"   总上架效率目标: {target_analysis['总上架效率']['moderate']:.4f}")

def save_target_analysis_results(df_clean, target_analysis, file_path):
    """
    保存目标分析结果
    """
    print("\n" + "=" * 60)
    print("💾 保存目标分析结果")
    print("=" * 60)
    
    # 创建结果文件名
    result_path = file_path.replace('.xlsx', '_efficiency_targets.xlsx')
    
    try:
        # 创建目标分析结果DataFrame
        target_df = pd.DataFrame(target_analysis).T
        target_df.index.name = '效率指标'
        
        # 保存清理后的数据和目标分析结果
        with pd.ExcelWriter(result_path) as writer:
            df_clean.to_excel(writer, sheet_name='清理后数据', index=False)
            target_df.to_excel(writer, sheet_name='效率目标线')
        
        print(f"✅ 成功保存效率目标分析结果到: {result_path}")
        print(f"📊 清理后数据形状: {df_clean.shape}")
        
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
        
        # 效率指标
        efficiency_metrics = ['盒菜分拣效率', '总分拣效率', '盒菜上架效率', '总上架效率']
        
        # 处理缺失值
        df = df.dropna(subset=['point_id'] + efficiency_metrics)
        print(f"📈 处理后数据形状: {df.shape}")
        
        # 使用IQR排除异常数据
        df_clean, outlier_counts = remove_outliers_with_iqr(df, efficiency_metrics)
        
        # 分析效率目标线
        target_analysis = analyze_efficiency_targets(df_clean, efficiency_metrics)
        
        # 比较盒菜效率与总效率
        compare_box_vs_total_efficiency(df_clean)
        
        # 推荐目标指标
        recommend_target_metrics(target_analysis, df_clean)
        
        # 保存分析结果
        result_path = save_target_analysis_results(df_clean, target_analysis, file_path)
        
        if result_path:
            print("\n" + "=" * 60)
            print("🎯 总结")
            print("=" * 60)
            print("效率目标线分析完成:")
            print("1. 使用IQR方法排除了异常数据")
            print("2. 分析了分拣和上架两个阶段的效率目标线")
            print("3. 比较了盒菜效率与总效率的差异")
            print("4. 基于业务特点推荐了目标指标")
            print("5. 提供了保守、中等、激进三个目标级别")
            print("6. 保存了详细的分析结果")
        
    except Exception as e:
        print(f"❌ 处理数据时出错: {e}")

if __name__ == "__main__":
    main()
