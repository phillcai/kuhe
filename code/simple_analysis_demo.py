"""
全排列路径算法有效性分析 - 简化演示版本

只使用pandas和numpy，不依赖matplotlib等复杂库
"""

import pandas as pd
import numpy as np
import sys
import os

# 添加路径以导入multi_req_evaluation
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_data():
    """加载数据"""
    try:
        # 尝试加载现有数据
        df = pd.read_csv('../data/multi_all_path.csv')
        print(f"✓ 成功加载数据文件，共{len(df)}条记录")
        return df
    except FileNotFoundError:
        print("未找到数据文件，使用模拟数据进行演示")
        return generate_mock_data()

def generate_mock_data():
    """生成模拟数据"""
    np.random.seed(42)
    
    data = []
    req_ids = ['req_001', 'req_002', 'req_003', 'req_004', 'req_005']
    
    for req_id in req_ids:
        n_paths = np.random.randint(50, 200)
        
        for i in range(n_paths):
            # 生成路径
            path_length = np.random.randint(2, 6)
            path_points = np.random.choice(range(100, 200), path_length, replace=False)
            path = '_'.join(map(str, path_points))
            
            # 生成指标
            loss = np.random.exponential(5) + np.random.uniform(0, 10)
            duration = np.random.normal(30000, 8000) + path_length * 5000
            duration = max(10000, duration)
            
            data.append({
                'req_id': req_id,
                'path': path,
                'path_duration': f"{duration:.0f}",
                'path_sale_loss': loss,
                '总点位数': path_length,
                '补货点位数': path_length,
                '补货率': 1.0
            })
    
    df = pd.DataFrame(data)
    print(f"✓ 生成模拟数据，共{len(df)}条记录")
    return df

def basic_statistics_analysis(df):
    """基础统计分析"""
    print("\n" + "="*60)
    print("第一层：基础统计分析")
    print("="*60)
    
    # 数据预处理
    df = df.copy()
    df['path_duration'] = df['path_duration'].astype(str).str.replace(',', '').astype(float)
    df['path_sale_loss'] = df['path_sale_loss'].astype(float)
    
    # 全局统计
    print(f"\n📊 数据概览:")
    print(f"  • 总请求数: {df['req_id'].nunique()}")
    print(f"  • 总路径数: {len(df)}")
    print(f"  • 平均每请求路径数: {len(df) / df['req_id'].nunique():.1f}")
    
    # 各请求统计
    print(f"\n📈 各请求统计:")
    for req_id in sorted(df['req_id'].unique()):
        req_data = df[df['req_id'] == req_id]
        
        print(f"\n  {req_id}:")
        print(f"    路径数量: {len(req_data)}")
        print(f"    平均损失: {req_data['path_sale_loss'].mean():.2f}")
        print(f"    损失范围: {req_data['path_sale_loss'].min():.2f} - {req_data['path_sale_loss'].max():.2f}")
        print(f"    平均时长: {req_data['path_duration'].mean()/60:.1f}分钟")
        print(f"    时长范围: {req_data['path_duration'].min()/60:.1f} - {req_data['path_duration'].max()/60:.1f}分钟")
    
    # 全局分布特征
    print(f"\n📊 全局分布特征:")
    print(f"  销量损失:")
    print(f"    平均值: {df['path_sale_loss'].mean():.2f}")
    print(f"    标准差: {df['path_sale_loss'].std():.2f}")
    print(f"    最小值: {df['path_sale_loss'].min():.2f}")
    print(f"    最大值: {df['path_sale_loss'].max():.2f}")
    print(f"    25%分位: {df['path_sale_loss'].quantile(0.25):.2f}")
    print(f"    50%分位: {df['path_sale_loss'].quantile(0.5):.2f}")
    print(f"    75%分位: {df['path_sale_loss'].quantile(0.75):.2f}")
    
    print(f"  行驶时间:")
    print(f"    平均值: {df['path_duration'].mean()/60:.1f}分钟")
    print(f"    标准差: {df['path_duration'].std()/60:.1f}分钟")
    print(f"    最小值: {df['path_duration'].min()/60:.1f}分钟")
    print(f"    最大值: {df['path_duration'].max()/60:.1f}分钟")
    print(f"    25%分位: {df['path_duration'].quantile(0.25)/60:.1f}分钟")
    print(f"    50%分位: {df['path_duration'].quantile(0.5)/60:.1f}分钟")
    print(f"    75%分位: {df['path_duration'].quantile(0.75)/60:.1f}分钟")
    
    return df

def quality_analysis(df):
    """解质量分析"""
    print("\n" + "="*60)
    print("第二层：解质量分析")
    print("="*60)
    
    # 计算简单评分（基于损失和时间的综合评分）
    df = df.copy()
    
    results = []
    for req_id in df['req_id'].unique():
        req_data = df[df['req_id'] == req_id].copy()
        
        # 标准化评分（越小越好的指标）
        loss_scores = 1 - (req_data['path_sale_loss'] - req_data['path_sale_loss'].min()) / (req_data['path_sale_loss'].max() - req_data['path_sale_loss'].min() + 1e-6)
        time_scores = 1 - (req_data['path_duration'] - req_data['path_duration'].min()) / (req_data['path_duration'].max() - req_data['path_duration'].min() + 1e-6)
        
        # 综合评分
        total_scores = 0.6 * loss_scores + 0.4 * time_scores
        req_data['total_score'] = total_scores
        
        # 分析最优解
        best_idx = total_scores.idxmax()
        best_path = req_data.loc[best_idx]
        
        # Top-K分析
        top_10_percent = req_data.nlargest(max(1, len(req_data)//10), 'total_score')
        
        results.append({
            'req_id': req_id,
            'total_paths': len(req_data),
            'best_score': best_path['total_score'],
            'best_loss': best_path['path_sale_loss'],
            'best_time': best_path['path_duration'],
            'avg_score': total_scores.mean(),
            'top_10_percent_avg': top_10_percent['total_score'].mean(),
            'score_std': total_scores.std()
        })
    
    print(f"\n🎯 最优解发现能力分析:")
    for result in results:
        print(f"\n  {result['req_id']}:")
        print(f"    总路径数: {result['total_paths']}")
        print(f"    最优评分: {result['best_score']:.3f}")
        print(f"    平均评分: {result['avg_score']:.3f}")
        print(f"    前10%平均评分: {result['top_10_percent_avg']:.3f}")
        print(f"    评分标准差: {result['score_std']:.3f}")
        print(f"    最优路径损失: {result['best_loss']:.2f}")
        print(f"    最优路径时长: {result['best_time']/60:.1f}分钟")
        
        # 算法价值评估
        value_score = (result['best_score'] - result['avg_score']) / result['avg_score'] if result['avg_score'] > 0 else 0
        print(f"    算法价值评分: {value_score:.3f}")
    
    # 全局质量评估
    all_best_scores = [r['best_score'] for r in results]
    all_avg_scores = [r['avg_score'] for r in results]
    
    print(f"\n🏆 全局质量评估:")
    print(f"  平均最优评分: {np.mean(all_best_scores):.3f}")
    print(f"  平均评分: {np.mean(all_avg_scores):.3f}")
    print(f"  算法整体价值: {(np.mean(all_best_scores) - np.mean(all_avg_scores)) / np.mean(all_avg_scores):.3f}")
    
    # 算法有效性等级
    overall_value = (np.mean(all_best_scores) - np.mean(all_avg_scores)) / np.mean(all_avg_scores)
    if overall_value > 0.3:
        grade = "优秀"
    elif overall_value > 0.15:
        grade = "良好"
    elif overall_value > 0.05:
        grade = "一般"
    else:
        grade = "较差"
    
    print(f"  算法有效性等级: {grade}")
    
    return results

def clustering_analysis(df):
    """请求分类分析（简化版）"""
    print("\n" + "="*60)
    print("第三层：请求分类分析")
    print("="*60)
    
    # 基于统计特征进行简单分类
    req_features = []
    
    for req_id in df['req_id'].unique():
        req_data = df[df['req_id'] == req_id]
        
        features = {
            'req_id': req_id,
            'avg_loss': req_data['path_sale_loss'].mean(),
            'avg_time': req_data['path_duration'].mean(),
            'path_count': len(req_data),
            'loss_cv': req_data['path_sale_loss'].std() / req_data['path_sale_loss'].mean() if req_data['path_sale_loss'].mean() > 0 else 0,
            'time_cv': req_data['path_duration'].std() / req_data['path_duration'].mean() if req_data['path_duration'].mean() > 0 else 0
        }
        req_features.append(features)
    
    # 简单分类逻辑
    print(f"\n🔍 请求类型识别:")
    
    loss_threshold = np.median([f['avg_loss'] for f in req_features])
    time_threshold = np.median([f['avg_time'] for f in req_features])
    
    clusters = {
        '损失敏感型': [],
        '时间敏感型': [],
        '平衡型': [],
        '高复杂型': []
    }
    
    for features in req_features:
        if features['avg_loss'] > loss_threshold and features['loss_cv'] > 0.3:
            cluster_type = '损失敏感型'
        elif features['avg_time'] > time_threshold and features['time_cv'] > 0.3:
            cluster_type = '时间敏感型'
        elif features['path_count'] > np.median([f['path_count'] for f in req_features]) * 1.5:
            cluster_type = '高复杂型'
        else:
            cluster_type = '平衡型'
        
        clusters[cluster_type].append(features['req_id'])
        
        print(f"  {features['req_id']}: {cluster_type}")
        print(f"    平均损失: {features['avg_loss']:.2f}")
        print(f"    平均时长: {features['avg_time']/60:.1f}分钟")
        print(f"    路径数量: {features['path_count']}")
        print(f"    损失变异系数: {features['loss_cv']:.3f}")
        print(f"    时长变异系数: {features['time_cv']:.3f}")
    
    print(f"\n📊 聚类分布:")
    for cluster_type, req_ids in clusters.items():
        if req_ids:
            print(f"  {cluster_type}: {len(req_ids)}个请求 {req_ids}")
    
    return clusters

def pruning_analysis(df):
    """剪枝策略分析（简化版）"""
    print("\n" + "="*60)
    print("第四层：剪枝策略建议")
    print("="*60)
    
    # 分析剪枝潜力
    total_paths = len(df)
    
    # 基于损失的剪枝分析
    loss_75 = df['path_sale_loss'].quantile(0.75)
    high_loss_paths = len(df[df['path_sale_loss'] > loss_75])
    loss_pruning_ratio = high_loss_paths / total_paths
    
    # 基于时间的剪枝分析
    time_90 = df['path_duration'].quantile(0.90)
    long_time_paths = len(df[df['path_duration'] > time_90])
    time_pruning_ratio = long_time_paths / total_paths
    
    # 组合剪枝分析
    combined_paths = len(df[(df['path_sale_loss'] > loss_75) | (df['path_duration'] > time_90)])
    combined_pruning_ratio = combined_paths / total_paths
    
    print(f"\n✂️ 剪枝策略建议:")
    
    print(f"\n  1. 基于损失的剪枝:")
    print(f"     阈值: 损失 > {loss_75:.2f}")
    print(f"     可剪枝路径: {high_loss_paths}条 ({loss_pruning_ratio:.1%})")
    print(f"     建议: {'强烈推荐' if loss_pruning_ratio > 0.2 else '推荐' if loss_pruning_ratio > 0.1 else '谨慎使用'}")
    
    print(f"\n  2. 基于时间的剪枝:")
    print(f"     阈值: 时长 > {time_90/60:.1f}分钟")
    print(f"     可剪枝路径: {long_time_paths}条 ({time_pruning_ratio:.1%})")
    print(f"     建议: {'强烈推荐' if time_pruning_ratio > 0.15 else '推荐' if time_pruning_ratio > 0.08 else '谨慎使用'}")
    
    print(f"\n  3. 组合剪枝策略:")
    print(f"     可剪枝路径: {combined_paths}条 ({combined_pruning_ratio:.1%})")
    print(f"     预期计算节省: {combined_pruning_ratio:.1%}")
    print(f"     建议: {'立即实施' if combined_pruning_ratio > 0.3 else '可以实施' if combined_pruning_ratio > 0.15 else '效果有限'}")
    
    # 早停策略分析
    print(f"\n  4. 早停策略建议:")
    
    for req_id in df['req_id'].unique():
        req_data = df[df['req_id'] == req_id]
        
        # 模拟排序后的质量分布
        loss_sorted = req_data['path_sale_loss'].sort_values()
        
        # 找到达到90%最优解需要的路径数
        best_loss = loss_sorted.iloc[0]
        target_loss = best_loss * 1.1  # 允许10%的质量损失
        
        paths_needed = len(loss_sorted[loss_sorted <= target_loss])
        early_stop_ratio = 1 - (paths_needed / len(req_data))
        
        print(f"     {req_id}: 可提前停止{early_stop_ratio:.1%}的搜索")
    
    # 风险评估
    risk_factors = []
    if combined_pruning_ratio > 0.5:
        risk_factors.append("过度剪枝风险")
    if loss_pruning_ratio > 0.3:
        risk_factors.append("可能丢失最优解")
    
    risk_level = "高" if len(risk_factors) > 1 else "中" if len(risk_factors) == 1 else "低"
    
    print(f"\n  ⚠️ 风险评估:")
    print(f"     风险等级: {risk_level}")
    if risk_factors:
        print(f"     风险因素: {', '.join(risk_factors)}")
    print(f"     建议: {'分阶段实施，密切监控' if risk_level == '高' else '正常实施，定期检查' if risk_level == '中' else '可以放心实施'}")

def generate_summary(df, quality_results, clusters):
    """生成分析摘要"""
    print("\n" + "="*80)
    print("全排列路径算法有效性分析摘要")
    print("="*80)
    
    # 数据概览
    print(f"\n📊 数据概览:")
    print(f"  • 总请求数: {df['req_id'].nunique()}")
    print(f"  • 总路径数: {len(df)}")
    print(f"  • 平均每请求路径数: {len(df) / df['req_id'].nunique():.1f}")
    
    # 关键发现
    print(f"\n🔍 关键发现:")
    
    # 算法有效性
    all_values = [(r['best_score'] - r['avg_score']) / r['avg_score'] for r in quality_results if r['avg_score'] > 0]
    overall_value = np.mean(all_values) if all_values else 0
    
    print(f"  1. 算法整体价值评分: {overall_value:.3f}")
    
    # 请求多样性
    cluster_count = len([c for c in clusters.values() if c])
    print(f"  2. 识别出{cluster_count}种不同类型的请求")
    
    # 优化潜力
    total_paths = len(df)
    high_loss_paths = len(df[df['path_sale_loss'] > df['path_sale_loss'].quantile(0.75)])
    optimization_potential = high_loss_paths / total_paths
    print(f"  3. 约{optimization_potential:.1%}的路径具有优化潜力")
    
    # 核心建议
    print(f"\n💡 核心建议:")
    
    if overall_value > 0.2:
        print(f"  1. 全排列算法表现优秀，建议继续使用并优化")
    elif overall_value > 0.1:
        print(f"  1. 全排列算法表现良好，可考虑进一步优化")
    else:
        print(f"  1. 全排列算法效果有限，建议评估替代方案")
    
    if cluster_count > 2:
        print(f"  2. 建议针对不同类型请求采用差异化策略")
    
    if optimization_potential > 0.2:
        print(f"  3. 建议实施剪枝策略，预期可节省{optimization_potential:.1%}的计算资源")
    
    # 下一步行动
    print(f"\n🎯 下一步行动:")
    print(f"  1. 实施基于损失阈值的剪枝策略")
    print(f"  2. 为不同类型请求设计专门的优化参数")
    print(f"  3. 建立持续监控机制，跟踪算法性能")
    print(f"  4. 收集更多数据以提高分析准确性")
    
    print(f"\n" + "="*80)

def main():
    """主函数"""
    print("全排列路径算法有效性分析系统 - 简化演示版")
    print("="*60)
    
    try:
        # 1. 加载数据
        df = load_data()
        
        # 2. 基础统计分析
        df = basic_statistics_analysis(df)
        
        # 3. 解质量分析
        quality_results = quality_analysis(df)
        
        # 4. 请求分类分析
        clusters = clustering_analysis(df)
        
        # 5. 剪枝策略分析
        pruning_analysis(df)
        
        # 6. 生成摘要
        generate_summary(df, quality_results, clusters)
        
        print(f"\n✅ 分析完成！")
        
    except Exception as e:
        print(f"\n❌ 分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 