#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
点位分拣耗时数据分析 - 基础版本
直接使用文档中的目标线数据进行分析
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def create_distribution_analysis():
    """基于文档中的目标线创建分布分析"""
    
    # 从文档中获取的目标线数据
    q75 = 0.2526  # 保守目标
    q90 = 0.3119  # 中等目标  
    q95 = 0.3498  # 激进目标
    
    # 修正：模拟效率分布数据
    # 假设Q75是75%分位数，那么均值应该低于Q75
    # 根据正态分布特性，Q75 ≈ 均值 + 0.67*标准差
    # 设均值 = Q75 - 0.67*标准差
    std_efficiency = (q95 - q75) / 1.5  # 调整标准差
    mean_efficiency = q75 - 0.67 * std_efficiency  # 均值低于Q75
    
    # 生成模拟数据
    np.random.seed(42)  # 固定随机种子
    n_samples = 1000
    efficiency_data = np.random.normal(mean_efficiency, std_efficiency, n_samples)
    efficiency_data = np.abs(efficiency_data)  # 确保效率为正数
    
    # 验证生成的数据是否符合预期
    actual_q75 = np.percentile(efficiency_data, 75)
    actual_q90 = np.percentile(efficiency_data, 90)
    actual_q95 = np.percentile(efficiency_data, 95)
    
    print(f"目标Q75: {q75:.4f}, 实际Q75: {actual_q75:.4f}")
    print(f"目标Q90: {q90:.4f}, 实际Q90: {actual_q90:.4f}")
    print(f"目标Q95: {q95:.4f}, 实际Q95: {actual_q95:.4f}")
    
    # 创建图形
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('点位分拣效率分布分析', fontsize=16, fontweight='bold')
    
    # 1. 效率分布直方图
    ax1 = axes[0, 0]
    ax1.hist(efficiency_data, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
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
    ax2.boxplot(efficiency_data, vert=True)
    ax2.axhline(q75, color='orange', linestyle='--', linewidth=2, label=f'Q75: {q75:.4f}')
    ax2.axhline(q90, color='red', linestyle='--', linewidth=2, label=f'Q90: {q90:.4f}')
    ax2.axhline(q95, color='purple', linestyle='--', linewidth=2, label=f'Q95: {q95:.4f}')
    ax2.set_title('效率箱线图')
    ax2.set_ylabel('效率 (盒/分钟)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 累积分布图
    ax3 = axes[1, 0]
    sorted_efficiency = np.sort(efficiency_data)
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
    
    # 计算统计信息
    stats = {
        'mean': np.mean(efficiency_data),
        'median': np.median(efficiency_data),
        'std': np.std(efficiency_data),
        'min': np.min(efficiency_data),
        'max': np.max(efficiency_data),
        'q25': np.percentile(efficiency_data, 25),
        'q75': actual_q75,  # 使用实际计算的Q75
        'q90': actual_q90,  # 使用实际计算的Q90
        'q95': actual_q95   # 使用实际计算的Q95
    }
    
    table_data = [
        ['统计指标', '数值'],
        ['样本数量', f"{len(efficiency_data):,}"],
        ['平均值', f"{stats['mean']:.4f}"],
        ['中位数', f"{stats['median']:.4f}"],
        ['标准差', f"{stats['std']:.4f}"],
        ['最小值', f"{stats['min']:.4f}"],
        ['最大值', f"{stats['max']:.4f}"],
        ['Q25', f"{stats['q25']:.4f}"],
        ['Q75', f"{actual_q75:.4f}"],
        ['Q90', f"{actual_q90:.4f}"],
        ['Q95', f"{actual_q95:.4f}"]
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

def create_target_analysis():
    """创建目标分析图"""
    
    # 目标线数据
    q75 = 0.2526
    q90 = 0.3119
    q95 = 0.3498
    
    # 模拟数据
    np.random.seed(42)
    n_samples = 1000
    mean_efficiency = q75
    std_efficiency = (q95 - q75) / 2
    efficiency_data = np.abs(np.random.normal(mean_efficiency, std_efficiency, n_samples))
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('目标达成情况分析', fontsize=16, fontweight='bold')
    
    # 1. 目标达成比例
    ax1 = axes[0]
    targets_data = {
        'Q75目标': (efficiency_data >= q75).sum(),
        'Q90目标': (efficiency_data >= q90).sum(),
        'Q95目标': (efficiency_data >= q95).sum()
    }
    
    total = len(efficiency_data)
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
    max_val = efficiency_data.max()
    bins = [0, q75, q90, q95, max_val]
    labels = [f'<{q75:.3f}', f'{q75:.3f}-{q90:.3f}', f'{q90:.3f}-{q95:.3f}', f'>{q95:.3f}']
    
    # 计算区间分布
    interval_counts = []
    for i in range(len(bins) - 1):
        count = ((efficiency_data >= bins[i]) & (efficiency_data < bins[i+1])).sum()
        if i == len(bins) - 2:  # 最后一个区间包含最大值
            count = (efficiency_data >= bins[i]).sum()
        interval_counts.append(count)
    
    colors = ['#FF9999', '#FFCC99', '#99CCFF', '#99FF99']
    bars2 = ax2.bar(labels, interval_counts, color=colors)
    
    # 添加数值标签
    for bar, value in zip(bars2, interval_counts):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{value}\n({value/total*100:.1f}%)',
                ha='center', va='bottom', fontweight='bold')
    
    ax2.set_title('效率区间分布')
    ax2.set_ylabel('点位数量')
    ax2.set_ylim(0, max(interval_counts) * 1.1)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def create_comparison_with_targets():
    """创建与目标线的对比分析"""
    
    # 目标线数据
    q75 = 0.2526
    q90 = 0.3119
    q95 = 0.3498
    
    # 模拟实际数据分布
    np.random.seed(42)
    n_samples = 1000
    
    # 模拟不同场景的数据
    scenarios = {
        '当前状况': np.abs(np.random.normal(0.20, 0.05, n_samples)),
        '改进后': np.abs(np.random.normal(0.28, 0.06, n_samples)),
        '目标达成': np.abs(np.random.normal(0.35, 0.07, n_samples))
    }
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('不同场景下的效率分布对比', fontsize=16, fontweight='bold')
    
    colors = ['orange', 'red', 'purple']
    target_labels = [f'Q75: {q75:.4f}', f'Q90: {q90:.4f}', f'Q95: {q95:.4f}']
    
    for i, (scenario, data) in enumerate(scenarios.items()):
        ax = axes[i]
        
        # 绘制直方图
        ax.hist(data, bins=20, alpha=0.7, color='lightblue', edgecolor='black')
        
        # 添加目标线
        for j, (target, color, label) in enumerate(zip([q75, q90, q95], colors, target_labels)):
            ax.axvline(target, color=color, linestyle='--', linewidth=2, label=label)
        
        # 计算达成比例
        q75_count = (data >= q75).sum()
        q90_count = (data >= q90).sum()
        q95_count = (data >= q95).sum()
        
        ax.set_title(f'{scenario}\nQ75达成: {q75_count}/{n_samples} ({q75_count/n_samples*100:.1f}%)\n'
                    f'Q90达成: {q90_count}/{n_samples} ({q90_count/n_samples*100:.1f}%)\n'
                    f'Q95达成: {q95_count}/{n_samples} ({q95_count/n_samples*100:.1f}%)')
        ax.set_xlabel('效率 (盒/分钟)')
        ax.set_ylabel('频次')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def main():
    """主函数"""
    print("=== 点位分拣效率分布分析 ===")
    print("基于文档中的目标线数据进行分析")
    
    # 创建输出目录
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    # 生成分布图
    print("\n生成分布图...")
    fig1 = create_distribution_analysis()
    fig1.savefig(output_dir / '点位分拣效率分布图.png', dpi=300, bbox_inches='tight')
    print("分布图已保存到: output/点位分拣效率分布图.png")
    
    # 生成目标分析图
    print("生成目标分析图...")
    fig2 = create_target_analysis()
    fig2.savefig(output_dir / '目标达成情况分析.png', dpi=300, bbox_inches='tight')
    print("目标分析图已保存到: output/目标达成情况分析.png")
    
    # 生成对比分析图
    print("生成对比分析图...")
    fig3 = create_comparison_with_targets()
    fig3.savefig(output_dir / '不同场景效率对比.png', dpi=300, bbox_inches='tight')
    print("对比分析图已保存到: output/不同场景效率对比.png")
    
    # 显示图形
    plt.show()
    
    print("\n=== 分析完成 ===")
    print("\n目标线总结:")
    print(f"保守目标 (Q75): {0.2526:.4f} 盒/分钟")
    print(f"中等目标 (Q90): {0.3119:.4f} 盒/分钟")
    print(f"激进目标 (Q95): {0.3498:.4f} 盒/分钟")

if __name__ == "__main__":
    main()
