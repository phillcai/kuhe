import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import json

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def load_and_analyze_data():
    """加载并分析优先级数据"""
    
    # 读取数据
    df = pd.read_csv('data/priority.csv')
    
    print("=== 数据概览 ===")
    print(f"总记录数: {len(df)}")
    print(f"唯一req_id数: {df['req_id'].nunique()}")
    print(f"唯一point_id数: {df['point_id'].nunique()}")
    
    # 基本统计信息
    print("\n=== 基本统计信息 ===")
    numeric_cols = ['priority', 'sales_score', 'stockout_score', 'type_score', 'sku_cnt', 'point_stock']
    print(df[numeric_cols].describe())
    
    # 点位类型分布
    print("\n=== 点位类型分布 ===")
    type_counts = df['point_type'].value_counts().sort_index()
    print(type_counts)
    
    # 分析每个req_id的数据
    print("\n=== 每个req_id的数据分析 ===")
    req_analysis = df.groupby('req_id').agg({
        'point_id': 'count',
        'priority': ['mean', 'std', 'min', 'max'],
        'sales_score': ['mean', 'std', 'min', 'max'],
        'stockout_score': ['mean', 'std', 'min', 'max'],
        'point_stock': ['mean', 'std', 'min', 'max']
    }).round(3)
    print(req_analysis)
    
    # 分析权重计算
    print("\n=== 权重计算分析 ===")
    # 从detail字段中提取权重信息
    weights_info = []
    for idx, row in df.iterrows():
        try:
            detail = json.loads(row['detail'])
            if 'priority_cal' in detail:
                weights_info.append({
                    'req_id': row['req_id'],
                    'point_id': row['point_id'],
                    'priority_cal': detail['priority_cal'],
                    'sales_norm': detail.get('sales_norm', 0),
                    'stockout_norm': detail.get('stockout_norm', 0),
                    'type_norm': detail.get('type_norm', 0),
                    'max_sales': detail.get('max_sales', 0),
                    'min_sales': detail.get('min_sales', 0),
                    'max_stockout': detail.get('max_stockout', 0),
                    'min_stockout': detail.get('min_stockout', 0),
                    'max_type': detail.get('max_type', 0),
                    'min_type': detail.get('min_type', 0)
                })
        except:
            continue
    
    weights_df = pd.DataFrame(weights_info)
    if not weights_df.empty:
        print("权重公式分布:")
        print(weights_df['priority_cal'].value_counts())
        
        print("\n归一化范围:")
        print(f"销量归一化范围: {weights_df['min_sales'].iloc[0]} - {weights_df['max_sales'].iloc[0]}")
        print(f"缺货归一化范围: {weights_df['min_stockout'].iloc[0]} - {weights_df['max_stockout'].iloc[0]}")
        print(f"类型归一化范围: {weights_df['min_type'].iloc[0]} - {weights_df['max_type'].iloc[0]}")
    
    # 异常值检测
    print("\n=== 异常值检测 ===")
    
    # 检查库存异常
    max_stock = 108  # 根据用户提供的信息
    high_stock_points = df[df['point_stock'] > max_stock]
    if not high_stock_points.empty:
        print(f"库存超过最大值({max_stock})的点位:")
        print(high_stock_points[['point_id', 'point_stock', 'priority']])
    
    # 检查零库存但高优先级的点位
    zero_stock_high_priority = df[(df['point_stock'] == 0) & (df['priority'] > 0.5)]
    if not zero_stock_high_priority.empty:
        print(f"\n零库存但高优先级(>0.5)的点位:")
        print(zero_stock_high_priority[['point_id', 'point_stock', 'priority', 'stockout_score']])
    
    # 检查优先级分布
    print("\n=== 优先级分布分析 ===")
    priority_ranges = [
        (0, 0.2, "低优先级"),
        (0.2, 0.4, "中低优先级"),
        (0.4, 0.6, "中优先级"),
        (0.6, 0.8, "中高优先级"),
        (0.8, 1.0, "高优先级")
    ]
    
    for low, high, label in priority_ranges:
        count = len(df[(df['priority'] >= low) & (df['priority'] < high)])
        percentage = count / len(df) * 100
        print(f"{label}: {count}个点位 ({percentage:.1f}%)")
    
    # 分析权重影响
    print("\n=== 权重影响分析 ===")
    if not weights_df.empty:
        # 计算各分量的贡献
        df['sales_contribution'] = df['sales_score'] * 0.4  # 假设权重为0.4
        df['stockout_contribution'] = df['stockout_score'] * 0.45  # 假设权重为0.45
        df['type_contribution'] = df['type_score'] * 0.15  # 假设权重为0.15
        
        print("各分量对优先级的贡献:")
        print(f"销量贡献: {df['sales_contribution'].mean():.3f} ± {df['sales_contribution'].std():.3f}")
        print(f"缺货贡献: {df['stockout_contribution'].mean():.3f} ± {df['stockout_contribution'].std():.3f}")
        print(f"类型贡献: {df['type_contribution'].mean():.3f} ± {df['type_contribution'].std():.3f}")
    
    # 相关性分析
    print("\n=== 相关性分析 ===")
    correlation_matrix = df[['priority', 'sales_score', 'stockout_score', 'type_score', 'point_stock']].corr()
    print(correlation_matrix['priority'].sort_values(ascending=False))
    
    return df, weights_df

def generate_optimization_suggestions(df, weights_df):
    """生成优化建议"""
    
    print("\n" + "="*50)
    print("优化建议")
    print("="*50)
    
    # 1. 权重调整建议
    print("\n1. 权重调整建议:")
    if not weights_df.empty:
        # 分析当前权重效果
        sales_corr = df['priority'].corr(df['sales_score'])
        stockout_corr = df['priority'].corr(df['stockout_score'])
        type_corr = df['priority'].corr(df['type_score'])
        
        print(f"   - 销量与优先级相关性: {sales_corr:.3f}")
        print(f"   - 缺货与优先级相关性: {stockout_corr:.3f}")
        print(f"   - 类型与优先级相关性: {type_corr:.3f}")
        
        # 基于相关性分析权重调整建议
        print("\n   基于相关性的权重调整建议:")
        
        # 计算相关性绝对值，用于权重分配
        corr_abs = {
            'sales': abs(sales_corr),
            'stockout': abs(stockout_corr), 
            'type': abs(type_corr)
        }
        total_corr = sum(corr_abs.values())
        
        if total_corr > 0:
            # 基于相关性强度建议权重分配
            suggested_weights = {
                'sales': corr_abs['sales'] / total_corr,
                'stockout': corr_abs['stockout'] / total_corr,
                'type': corr_abs['type'] / total_corr
            }
            
            print(f"   - 建议销量权重: {suggested_weights['sales']:.3f}")
            print(f"   - 建议缺货权重: {suggested_weights['stockout']:.3f}")
            print(f"   - 建议类型权重: {suggested_weights['type']:.3f}")
            print(f"   - 权重总和: {sum(suggested_weights.values()):.3f}")
        
        # 具体建议
        if abs(stockout_corr) < 0.5:
            print("   - 建议: 缺货风险相关性较低，可能需要调整缺货风险的计算方式")
        if abs(sales_corr) < 0.3:
            print("   - 建议: 销量相关性较低，可能需要调整销量预测或权重")
        if abs(type_corr) < 0.2:
            print("   - 建议: 类型相关性较低，可能需要重新设计类型权重")
    
    # 2. 归一化问题
    print("\n2. 归一化问题:")
    if not weights_df.empty:
        sales_range = weights_df['max_sales'].iloc[0] - weights_df['min_sales'].iloc[0]
        stockout_range = weights_df['max_stockout'].iloc[0] - weights_df['min_stockout'].iloc[0]
        
        if sales_range == 0:
            print("   - 问题: 销量归一化分母为0，所有点位销量相同")
        if stockout_range == 0:
            print("   - 问题: 缺货归一化分母为0，所有点位缺货风险相同")
        
        if sales_range < 10:
            print("   - 建议: 销量范围较小，归一化效果可能不明显")
        if stockout_range < 5:
            print("   - 建议: 缺货风险范围较小，归一化效果可能不明显")
    
    # 3. 库存管理建议
    print("\n3. 库存管理建议:")
    zero_stock_count = len(df[df['point_stock'] == 0])
    low_stock_count = len(df[df['point_stock'] < 10])
    
    print(f"   - 零库存点位: {zero_stock_count}个 ({zero_stock_count/len(df)*100:.1f}%)")
    print(f"   - 低库存点位(<10): {low_stock_count}个 ({low_stock_count/len(df)*100:.1f}%)")
    
    if zero_stock_count > len(df) * 0.1:
        print("   - 建议: 零库存点位比例较高，需要优化补货策略")
    
    # 4. 优先级分布建议
    print("\n4. 优先级分布建议:")
    priority_std = df['priority'].std()
    if priority_std < 0.1:
        print("   - 问题: 优先级区分度较低，所有点位优先级相近")
        print("   - 建议: 调整权重或增加更多差异化因素")
    
    # 5. 时间窗口建议
    print("\n5. 时间窗口建议:")
    max_stockout = df['stockout_score'].max()
    if max_stockout > 20:
        print(f"   - 当前最大缺货时间: {max_stockout}小时")
        print("   - 建议: 考虑引入分时权重，近期缺货给予更高权重")
    
    # 6. 点位类型优化
    print("\n6. 点位类型优化:")
    type_priority_analysis = df.groupby('point_type')['priority'].agg(['mean', 'count']).round(3)
    print("   各类型点位优先级均值:")
    print(type_priority_analysis)
    
    # 检查是否有类型优先级不合理的情况
    type_means = type_priority_analysis['mean']
    if len(type_means) > 1:
        max_type_priority = type_means.idxmax()
        min_type_priority = type_means.idxmin()
        if type_means[max_type_priority] - type_means[min_type_priority] < 0.1:
            print("   - 建议: 点位类型间优先级差异较小，可能需要调整类型权重")

def create_visualizations(df):
    """创建可视化图表"""
    
    # 创建图表
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('优先级计算数据分析', fontsize=16)
    
    # 1. 优先级分布
    axes[0, 0].hist(df['priority'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
    axes[0, 0].set_title('优先级分布')
    axes[0, 0].set_xlabel('优先级')
    axes[0, 0].set_ylabel('频次')
    
    # 2. 销量分布
    axes[0, 1].hist(df['sales_score'], bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
    axes[0, 1].set_title('销量分布')
    axes[0, 1].set_xlabel('销量')
    axes[0, 1].set_ylabel('频次')
    
    # 3. 缺货风险分布
    axes[0, 2].hist(df['stockout_score'], bins=20, alpha=0.7, color='salmon', edgecolor='black')
    axes[0, 2].set_title('缺货风险分布')
    axes[0, 2].set_xlabel('缺货小时数')
    axes[0, 2].set_ylabel('频次')
    
    # 4. 优先级 vs 销量
    axes[1, 0].scatter(df['sales_score'], df['priority'], alpha=0.6, color='blue')
    axes[1, 0].set_title('优先级 vs 销量')
    axes[1, 0].set_xlabel('销量')
    axes[1, 0].set_ylabel('优先级')
    
    # 5. 优先级 vs 缺货风险
    axes[1, 1].scatter(df['stockout_score'], df['priority'], alpha=0.6, color='red')
    axes[1, 1].set_title('优先级 vs 缺货风险')
    axes[1, 1].set_xlabel('缺货小时数')
    axes[1, 1].set_ylabel('优先级')
    
    # 6. 点位类型优先级箱线图
    df.boxplot(column='priority', by='point_type', ax=axes[1, 2])
    axes[1, 2].set_title('各类型点位优先级分布')
    axes[1, 2].set_xlabel('点位类型')
    axes[1, 2].set_ylabel('优先级')
    
    plt.tight_layout()
    plt.savefig('priority_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    # 加载和分析数据
    df, weights_df = load_and_analyze_data()
    
    # 生成优化建议
    generate_optimization_suggestions(df, weights_df)
    
    # 创建可视化
    try:
        create_visualizations(df)
    except Exception as e:
        print(f"可视化创建失败: {e}")
        print("请确保安装了matplotlib和seaborn库") 