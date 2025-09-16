#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
点位分拣耗时数据分析 - 分布图生成
分析点位分拣效率的分布情况，包括效率分布直方图、箱线图和目标线对比
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_data():
    """加载点位耗时数据"""
    try:
        # 读取Excel文件
        df = pd.read_excel('data/点位耗时.xlsx')
        print(f"数据加载成功，共 {len(df)} 条记录")
        print(f"列名: {list(df.columns)}")
        print("\n数据预览:")
        print(df.head())
        return df
    except Exception as e:
        print(f"数据加载失败: {e}")
        return None

def analyze_efficiency_distribution(df):
    """分析效率分布"""
    # 假设效率列名为 '效率' 或 'efficiency' 或 '盒/分钟'
    efficiency_col = None
    for col in df.columns:
        if '效率' in col or 'efficiency' in col.lower() or '盒/分钟' in col:
            efficiency_col = col
            break
    
    if efficiency_col is None:
        # 如果没有找到效率列，尝试计算效率
        if '分拣数量' in df.columns and '分拣耗时' in df.columns:
            df['效率_盒/分钟'] = df['分拣数量'] / df['分拣耗时']
            efficiency_col = '效率_盒/分钟'
        elif '数量' in df.columns and '耗时' in df.columns:
            df['效率_盒/分钟'] = df['数量'] / df['耗时']
            efficiency_col = '效率_盒/分钟'
        else:
            print("未找到效率相关列，请检查数据格式")
            return None
    
    # 移除异常值（效率为0或负数的记录）
    df_clean = df[df[efficiency_col] > 0].copy()
    print(f"\n清理后数据: {len(df_clean)} 条记录")
    
    # 计算统计信息
    stats = df_clean[efficiency_col].describe()
    print(f"\n效率统计信息:")
    print(stats)
    
    # 计算分位数
    q75 = df_clean[efficiency_col].quantile(0.75)
    q90 = df_clean[efficiency_col].quantile(0.90)
    q95 = df_clean[efficiency_col].quantile(0.95)
    
    print(f"\n目标线:")
    print(f"保守目标 (Q75): {q75:.4f} 盒/分钟")
    print(f"中等目标 (Q90): {q90:.4f} 盒/分钟")
    print(f"激进目标 (Q95): {q95:.4f} 盒/分钟")
    
    return df_clean, efficiency_col, stats, (q75, q90, q95)

def create_distribution_plots(df, efficiency_col, stats, targets):
    """创建分布图"""
    q75, q90, q95 = targets
    
    # 创建图形
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('点位分拣效率分布分析', fontsize=16, fontweight='bold')
    
    # 1. 效率分布直方图
    ax1 = axes[0, 0]
    sns.histplot(data=df, x=efficiency_col, bins=30, kde=True, ax=ax1)
    ax1.axvline(q75, color='orange', linestyle='--', linewidth=2, label=f'Q75: {q75:.4f}')
    ax1.axvline(q90, color='red', linestyle='--', linewidth=2, label=f'Q90: {q90:.4f}')
    ax1.axvline(q95, color='purple', linestyle='--', linewidth=2, label=f'Q95: {q95:.4f}')
    ax1.set_title('效率分布直方图')
    ax1.set_xlabel('效率 (盒/分钟)')
    ax1.set_ylabel('频次')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 箱线图
    ax2 = axes[0, 1]
    sns.boxplot(data=df, y=efficiency_col, ax=ax2)
    ax2.axhline(q75, color='orange', linestyle='--', linewidth=2, label=f'Q75: {q75:.4f}')
    ax2.axhline(q90, color='red', linestyle='--', linewidth=2, label=f'Q90: {q90:.4f}')
    ax2.axhline(q95, color='purple', linestyle='--', linewidth=2, label=f'Q95: {q95:.4f}')
    ax2.set_title('效率箱线图')
    ax2.set_ylabel('效率 (盒/分钟)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 累积分布图
    ax3 = axes[1, 0]
    sorted_efficiency = np.sort(df[efficiency_col])
    cumulative_prob = np.arange(1, len(sorted_efficiency) + 1) / len(sorted_efficiency)
    ax3.plot(sorted_efficiency, cumulative_prob, linewidth=2)
    ax3.axvline(q75, color='orange', linestyle='--', linewidth=2, label=f'Q75: {q75:.4f}')
    ax3.axvline(q90, color='red', linestyle='--', linewidth=2, label=f'Q90: {q90:.4f}')
    ax3.axvline(q95, color='purple', linestyle='--', linewidth=2, label=f'Q95: {q95:.4f}')
    ax3.set_title('累积分布图')
    ax3.set_xlabel('效率 (盒/分钟)')
    ax3.set_ylabel('累积概率')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 统计信息表格
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')
    
    # 创建统计信息表格
    table_data = [
        ['统计指标', '数值'],
        ['样本数量', f"{len(df):,}"],
        ['平均值', f"{stats['mean']:.4f}"],
        ['中位数', f"{stats['50%']:.4f}"],
        ['标准差', f"{stats['std']:.4f}"],
        ['最小值', f"{stats['min']:.4f}"],
        ['最大值', f"{stats['max']:.4f}"],
        ['Q25', f"{stats['25%']:.4f}"],
        ['Q75', f"{q75:.4f}"],
        ['Q90', f"{q90:.4f}"],
        ['Q95', f"{q95:.4f}"]
    ]
    
    table = ax4.table(cellText=table_data, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)
    
    # 设置表格样式
    for i in range(len(table_data)):
        for j in range(len(table_data[0])):
            if i == 0:  # 表头
                table[(i, j)].set_facecolor('#4CAF50')
                table[(i, j)].set_text_props(weight='bold', color='white')
            else:
                table[(i, j)].set_facecolor('#f0f0f0' if i % 2 == 0 else 'white')
    
    ax4.set_title('统计信息汇总', fontsize=12, fontweight='bold', pad=20)
    
    plt.tight_layout()
    return fig

def create_target_analysis(df, efficiency_col, targets):
    """创建目标分析图"""
    q75, q90, q95 = targets
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('目标达成情况分析', fontsize=16, fontweight='bold')
    
    # 1. 目标达成比例
    ax1 = axes[0]
    targets_data = {
        'Q75目标': (df[efficiency_col] >= q75).sum(),
        'Q90目标': (df[efficiency_col] >= q90).sum(),
        'Q95目标': (df[efficiency_col] >= q95).sum()
    }
    
    total = len(df)
    percentages = {k: v/total*100 for k, v in targets_data.items()}
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    bars = ax1.bar(percentages.keys(), percentages.values(), color=colors)
    
    # 添加数值标签
    for bar, (key, value) in zip(bars, percentages.items()):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{value:.1f}%\n({targets_data[key]}/{total})',
                ha='center', va='bottom', fontweight='bold')
    
    ax1.set_title('各目标达成比例')
    ax1.set_ylabel('达成比例 (%)')
    ax1.set_ylim(0, max(percentages.values()) * 1.1)
    ax1.grid(True, alpha=0.3)
    
    # 2. 效率区间分布
    ax2 = axes[1]
    
    # 定义效率区间
    bins = [0, q75, q90, q95, df[efficiency_col].max()]
    labels = [f'<{q75:.3f}', f'{q75:.3f}-{q90:.3f}', f'{q90:.3f}-{q95:.3f}', f'>{q95:.3f}']
    
    df['效率区间'] = pd.cut(df[efficiency_col], bins=bins, labels=labels, include_lowest=True)
    interval_counts = df['效率区间'].value_counts().sort_index()
    
    colors = ['#FF9999', '#FFCC99', '#99CCFF', '#99FF99']
    bars2 = ax2.bar(interval_counts.index, interval_counts.values, color=colors)
    
    # 添加数值标签
    for bar, value in zip(bars2, interval_counts.values):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{value}\n({value/total*100:.1f}%)',
                ha='center', va='bottom', fontweight='bold')
    
    ax2.set_title('效率区间分布')
    ax2.set_ylabel('点位数量')
    ax2.set_ylim(0, max(interval_counts.values) * 1.1)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def main():
    """主函数"""
    print("=== 点位分拣耗时数据分析 ===")
    
    # 加载数据
    df = load_data()
    if df is None:
        return
    
    # 分析效率分布
    result = analyze_efficiency_distribution(df)
    if result is None:
        return
    
    df_clean, efficiency_col, stats, targets = result
    
    # 创建输出目录
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    # 生成分布图
    print("\n生成分布图...")
    fig1 = create_distribution_plots(df_clean, efficiency_col, stats, targets)
    fig1.savefig(output_dir / '点位分拣效率分布图.png', dpi=300, bbox_inches='tight')
    print("分布图已保存到: output/点位分拣效率分布图.png")
    
    # 生成目标分析图
    print("生成目标分析图...")
    fig2 = create_target_analysis(df_clean, efficiency_col, targets)
    fig2.savefig(output_dir / '目标达成情况分析.png', dpi=300, bbox_inches='tight')
    print("目标分析图已保存到: output/目标达成情况分析.png")
    
    # 显示图形
    plt.show()
    
    print("\n=== 分析完成 ===")

if __name__ == "__main__":
    main()
