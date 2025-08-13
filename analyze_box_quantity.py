#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
点位补货数据分析 - 重点分析盒菜数量指标
分析近30天的点位补货情况，重点关注每次补货的盒菜数量
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_and_clean_data(file_path):
    """
    加载并清洗数据
    """
    print("正在加载数据...")
    df = pd.read_csv(file_path)
    
    # 显示基本信息
    print(f"数据总行数: {len(df)}")
    print(f"数据列数: {len(df.columns)}")
    print("\n列名:")
    for i, col in enumerate(df.columns):
        print(f"{i+1}. {col}")
    
    # 检查盒菜数量列的数据质量
    print(f"\n盒菜数量列统计:")
    print(f"数据类型: {df['盒菜数量'].dtype}")
    print(f"缺失值数量: {df['盒菜数量'].isnull().sum()}")
    print(f"唯一值数量: {df['盒菜数量'].nunique()}")
    
    return df

def basic_statistics(df):
    """
    基础统计分析
    """
    print("\n" + "="*50)
    print("盒菜数量基础统计分析")
    print("="*50)
    
    box_quantity = df['盒菜数量']
    
    # 描述性统计
    stats = {
        '总记录数': len(box_quantity),
        '平均值': box_quantity.mean(),
        '中位数': box_quantity.median(),
        '标准差': box_quantity.std(),
        '最小值': box_quantity.min(),
        '最大值': box_quantity.max(),
        '第25百分位': box_quantity.quantile(0.25),
        '第75百分位': box_quantity.quantile(0.75),
        '四分位距(IQR)': box_quantity.quantile(0.75) - box_quantity.quantile(0.25)
    }
    
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")
    
    # 分布特征
    print(f"\n分布特征:")
    print(f"偏度: {box_quantity.skew():.3f}")
    print(f"峰度: {box_quantity.kurtosis():.3f}")
    
    return stats

def quantity_distribution_analysis(df):
    """
    盒菜数量分布分析
    """
    print("\n" + "="*50)
    print("盒菜数量分布分析")
    print("="*50)
    
    box_quantity = df['盒菜数量']
    
    # 按数量区间统计
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, float('inf')]
    labels = ['1-10', '11-20', '21-30', '31-40', '41-50', '51-60', 
             '61-70', '71-80', '81-90', '91-100', '100+']
    
    quantity_groups = pd.cut(box_quantity, bins=bins, labels=labels, right=True)
    distribution = quantity_groups.value_counts().sort_index()
    percentage = (distribution / len(df) * 100).round(2)
    
    print("数量区间分布:")
    for label, count, pct in zip(distribution.index, distribution.values, percentage.values):
        print(f"{label}盒: {count}次 ({pct}%)")
    
    # 常见数量统计
    print(f"\n最常见的补货数量:")
    top_quantities = box_quantity.value_counts().head(10)
    for qty, count in top_quantities.items():
        percentage = (count / len(df) * 100)
        print(f"{qty}盒: {count}次 ({percentage:.1f}%)")
    
    return distribution, top_quantities

def time_analysis(df):
    """
    时间维度分析
    """
    print("\n" + "="*50)
    print("时间维度分析")
    print("="*50)
    
    # 解析时间字段
    df['出发时间_parsed'] = pd.to_datetime(df['出发时间'], format='%Y-%m-%d, %H:%M', errors='coerce')
    
    # 提取时间特征
    df['日期'] = df['出发时间_parsed'].dt.date
    df['小时'] = df['出发时间_parsed'].dt.hour
    df['星期'] = df['出发时间_parsed'].dt.day_name()
    
    # 按日期统计
    daily_stats = df.groupby('日期')['盒菜数量'].agg(['count', 'mean', 'sum']).round(2)
    print("每日补货统计 (前10天):")
    print(daily_stats.head(10))
    
    # 按小时统计
    hourly_stats = df.groupby('小时')['盒菜数量'].agg(['count', 'mean']).round(2)
    print(f"\n按小时统计:")
    print(hourly_stats)
    
    return daily_stats, hourly_stats

def vehicle_analysis(df):
    """
    车辆维度分析
    """
    print("\n" + "="*50)
    print("车辆维度分析")
    print("="*50)
    
    vehicle_stats = df.groupby('car_number')['盒菜数量'].agg([
        'count', 'mean', 'median', 'std', 'min', 'max', 'sum'
    ]).round(2)
    
    # 按补货次数排序
    vehicle_stats_sorted = vehicle_stats.sort_values('count', ascending=False)
    print("车辆补货统计 (按补货次数排序，前10名):")
    print(vehicle_stats_sorted.head(10))
    
    # 按平均盒菜数量排序
    print(f"\n车辆平均盒菜数量排序 (前10名):")
    avg_sorted = vehicle_stats.sort_values('mean', ascending=False)
    print(avg_sorted.head(10)[['count', 'mean', 'sum']])
    
    return vehicle_stats

def location_analysis(df):
    """
    点位维度分析
    """
    print("\n" + "="*50)
    print("点位维度分析")
    print("="*50)
    
    location_stats = df.groupby('当前点位')['盒菜数量'].agg([
        'count', 'mean', 'median', 'std', 'min', 'max', 'sum'
    ]).round(2)
    
    # 按补货次数排序
    location_stats_sorted = location_stats.sort_values('count', ascending=False)
    print("点位补货统计 (按补货次数排序，前15名):")
    print(location_stats_sorted.head(15))
    
    # 按平均盒菜数量排序
    print(f"\n点位平均盒菜数量排序 (前15名):")
    avg_sorted = location_stats.sort_values('mean', ascending=False)
    print(avg_sorted.head(15)[['count', 'mean', 'sum']])
    
    return location_stats

def create_visualizations(df, stats, distribution):
    """
    创建可视化图表
    """
    print("\n正在生成可视化图表...")
    
    # 创建图表
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('点位补货盒菜数量分析报告', fontsize=16, fontweight='bold')
    
    # 1. 盒菜数量分布直方图
    axes[0, 0].hist(df['盒菜数量'], bins=30, alpha=0.7, color='skyblue', edgecolor='black')
    axes[0, 0].axvline(df['盒菜数量'].mean(), color='red', linestyle='--', 
                      label=f'平均值: {df["盒菜数量"].mean():.1f}')
    axes[0, 0].axvline(df['盒菜数量'].median(), color='green', linestyle='--', 
                      label=f'中位数: {df["盒菜数量"].median():.1f}')
    axes[0, 0].set_title('盒菜数量分布直方图')
    axes[0, 0].set_xlabel('盒菜数量')
    axes[0, 0].set_ylabel('频次')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. 盒菜数量箱线图
    axes[0, 1].boxplot(df['盒菜数量'], patch_artist=True, 
                      boxprops=dict(facecolor='lightblue'))
    axes[0, 1].set_title('盒菜数量箱线图')
    axes[0, 1].set_ylabel('盒菜数量')
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. 数量区间分布饼图
    distribution_clean = distribution[distribution > 0]  # 只显示非零的区间
    axes[0, 2].pie(distribution_clean.values, labels=distribution_clean.index, 
                   autopct='%1.1f%%', startangle=90)
    axes[0, 2].set_title('盒菜数量区间分布')
    
    # 4. 按小时的平均盒菜数量
    if '小时' in df.columns:
        hourly_avg = df.groupby('小时')['盒菜数量'].mean()
        axes[1, 0].bar(hourly_avg.index, hourly_avg.values, color='orange', alpha=0.7)
        axes[1, 0].set_title('各时段平均盒菜数量')
        axes[1, 0].set_xlabel('小时')
        axes[1, 0].set_ylabel('平均盒菜数量')
        axes[1, 0].grid(True, alpha=0.3)
    
    # 5. 前10个最常见的盒菜数量
    top_quantities = df['盒菜数量'].value_counts().head(10)
    axes[1, 1].bar(range(len(top_quantities)), top_quantities.values, color='green', alpha=0.7)
    axes[1, 1].set_title('最常见的盒菜数量 (前10)')
    axes[1, 1].set_xlabel('盒菜数量')
    axes[1, 1].set_ylabel('出现次数')
    axes[1, 1].set_xticks(range(len(top_quantities)))
    axes[1, 1].set_xticklabels(top_quantities.index)
    axes[1, 1].grid(True, alpha=0.3)
    
    # 6. 累积分布函数
    sorted_quantities = np.sort(df['盒菜数量'])
    cumulative_prob = np.arange(1, len(sorted_quantities) + 1) / len(sorted_quantities)
    axes[1, 2].plot(sorted_quantities, cumulative_prob, linewidth=2)
    axes[1, 2].set_title('盒菜数量累积分布函数')
    axes[1, 2].set_xlabel('盒菜数量')
    axes[1, 2].set_ylabel('累积概率')
    axes[1, 2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图表
    output_path = '/Users/admin/Code/MyCode/kuhe/box_quantity_analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"图表已保存至: {output_path}")
    
    plt.show()

def generate_insights(df, stats, distribution, daily_stats, vehicle_stats, location_stats):
    """
    生成分析洞察和建议
    """
    print("\n" + "="*50)
    print("分析洞察与建议")
    print("="*50)
    
    insights = []
    
    # 1. 整体数据洞察
    insights.append(f"📊 数据概览:")
    insights.append(f"   • 共分析了 {len(df)} 次补货记录")
    insights.append(f"   • 平均每次补货 {stats['平均值']:.1f} 盒菜")
    insights.append(f"   • 中位数为 {stats['中位数']:.1f} 盒，说明数据{'偏左' if stats['平均值'] > stats['中位数'] else '偏右'}分布")
    
    # 2. 分布特征洞察
    insights.append(f"\n📈 分布特征:")
    if stats['平均值'] > stats['中位数']:
        insights.append(f"   • 数据右偏分布，存在较多大批量补货的情况")
    else:
        insights.append(f"   • 数据左偏分布，大部分补货量相对较小")
    
    insights.append(f"   • 标准差为 {stats['标准差']:.1f}，变异系数为 {(stats['标准差']/stats['平均值']*100):.1f}%")
    
    # 3. 异常值检测
    q1, q3 = stats['第25百分位'], stats['第75百分位']
    iqr = stats['四分位距(IQR)']
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = df[(df['盒菜数量'] < lower_bound) | (df['盒菜数量'] > upper_bound)]
    
    insights.append(f"\n⚠️  异常值分析:")
    insights.append(f"   • 发现 {len(outliers)} 个异常值 ({len(outliers)/len(df)*100:.1f}%)")
    if len(outliers) > 0:
        insights.append(f"   • 异常值范围: {outliers['盒菜数量'].min():.0f} - {outliers['盒菜数量'].max():.0f} 盒")
    
    # 4. 效率分析
    if '分拣效率((分拣时长+上架时长)/盒菜数)' in df.columns:
        efficiency_corr = df['盒菜数量'].corr(df['分拣效率((分拣时长+上架时长)/盒菜数)'])
        insights.append(f"\n⚡ 效率分析:")
        insights.append(f"   • 盒菜数量与分拣效率的相关系数: {efficiency_corr:.3f}")
        if abs(efficiency_corr) > 0.3:
            trend = "负相关" if efficiency_corr < 0 else "正相关"
            insights.append(f"   • 存在明显的{trend}关系，需要优化批量处理策略")
    
    # 5. 车辆分析洞察
    top_vehicle = vehicle_stats.sort_values('count', ascending=False).index[0]
    insights.append(f"\n🚛 车辆分析:")
    insights.append(f"   • 最活跃车辆: {top_vehicle} (补货 {vehicle_stats.loc[top_vehicle, 'count']} 次)")
    insights.append(f"   • 车辆间平均补货量差异较大，最高 {vehicle_stats['mean'].max():.1f} 盒，最低 {vehicle_stats['mean'].min():.1f} 盒")
    
    # 6. 点位分析洞察
    top_location = location_stats.sort_values('count', ascending=False).index[0]
    insights.append(f"\n📍 点位分析:")
    insights.append(f"   • 最频繁补货点位: {top_location} (补货 {location_stats.loc[top_location, 'count']} 次)")
    insights.append(f"   • 点位间需求差异明显，建议按需求分层管理")
    
    # 7. 建议
    insights.append(f"\n💡 优化建议:")
    
    # 基于平均值给出建议
    if stats['平均值'] < 40:
        insights.append(f"   • 当前平均补货量较低，考虑提高单次补货量以降低配送频次")
    elif stats['平均值'] > 70:
        insights.append(f"   • 当前平均补货量较高，注意库存周转和保鲜问题")
    
    # 基于变异系数给出建议
    cv = stats['标准差'] / stats['平均值'] * 100
    if cv > 50:
        insights.append(f"   • 补货量波动较大(变异系数{cv:.1f}%)，建议建立更精准的需求预测模型")
    
    # 基于异常值给出建议
    if len(outliers) / len(df) > 0.05:
        insights.append(f"   • 异常值比例较高，建议检查补货策略的合理性")
    
    insights.append(f"   • 建议建立基于历史数据的智能补货量预测系统")
    insights.append(f"   • 考虑点位分级管理，对高频点位增加补货频次，降低单次补货量")
    
    # 输出所有洞察
    for insight in insights:
        print(insight)
    
    return insights

def main():
    """
    主函数
    """
    print("开始分析点位补货数据中的盒菜数量指标...")
    
    # 数据文件路径
    data_file = '/Users/admin/Code/MyCode/kuhe/data/点位补货.csv'
    
    try:
        # 1. 加载数据
        df = load_and_clean_data(data_file)
        
        # 2. 基础统计分析
        stats = basic_statistics(df)
        
        # 3. 分布分析
        distribution, top_quantities = quantity_distribution_analysis(df)
        
        # 4. 时间维度分析
        daily_stats, hourly_stats = time_analysis(df)
        
        # 5. 车辆维度分析
        vehicle_stats = vehicle_analysis(df)
        
        # 6. 点位维度分析
        location_stats = location_analysis(df)
        
        # 7. 创建可视化
        create_visualizations(df, stats, distribution)
        
        # 8. 生成洞察和建议
        insights = generate_insights(df, stats, distribution, daily_stats, vehicle_stats, location_stats)
        
        print(f"\n✅ 分析完成！共生成 {len(insights)} 条洞察和建议")
        print("详细分析图表已保存为 box_quantity_analysis.png")
        
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
