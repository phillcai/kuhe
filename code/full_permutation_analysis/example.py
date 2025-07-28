"""
全排列路径算法有效性分析示例

展示如何使用分析系统
"""

import pandas as pd
import sys
import os

# 添加父目录到路径以便导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from full_permutation_analysis import FullPermutationAnalyzer


def load_sample_data(file_path: str = None) -> pd.DataFrame:
    """
    加载示例数据
    
    Args:
        file_path: 数据文件路径，如果为None则使用默认路径
        
    Returns:
        路径数据DataFrame
    """
    if file_path is None:
        # 尝试加载现有的多请求数据
        default_paths = [
            'data/multi_all_path.csv',
            '../data/multi_all_path.csv',
            '../../data/multi_all_path.csv'
        ]
        
        for path in default_paths:
            if os.path.exists(path):
                file_path = path
                break
    
    if file_path and os.path.exists(file_path):
        print(f"加载数据文件: {file_path}")
        df = pd.read_csv(file_path)
        print(f"数据加载完成，共{len(df)}条记录")
        return df
    else:
        print("未找到数据文件，使用模拟数据进行演示")
        return generate_mock_data()


def generate_mock_data() -> pd.DataFrame:
    """
    生成模拟数据用于演示
    
    Returns:
        模拟的路径数据DataFrame
    """
    import numpy as np
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
            duration = max(10000, duration)  # 确保最小时间
            
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
    print(f"生成模拟数据完成，共{len(df)}条记录")
    return df


def run_basic_example():
    """运行基础分析示例"""
    print("=" * 60)
    print("全排列路径算法有效性分析 - 基础示例")
    print("=" * 60)
    
    # 1. 加载数据
    df = load_sample_data()
    
    # 2. 创建分析器
    analyzer = FullPermutationAnalyzer(df, output_dir='output/basic_example')
    
    # 3. 运行完整分析
    print("\n开始执行完整分析...")
    results = analyzer.run_full_analysis()
    
    # 4. 打印摘要
    analyzer.print_summary()
    
    print("\n基础示例完成！")
    return analyzer, results


def run_step_by_step_example():
    """运行分步分析示例"""
    print("=" * 60)
    print("全排列路径算法有效性分析 - 分步示例")
    print("=" * 60)
    
    # 1. 加载数据
    df = load_sample_data()
    
    # 2. 创建分析器
    analyzer = FullPermutationAnalyzer(df, output_dir='output/step_by_step_example')
    
    # 3. 分步执行分析
    print("\n第一步：基础统计分析")
    stats_results = analyzer.run_statistics_analysis()
    print(f"✓ 统计分析完成，识别出{stats_results['basic_info']['总请求数']}个请求")
    
    print("\n第二步：解质量分析")
    quality_results = analyzer.run_quality_analysis()
    print(f"✓ 质量分析完成，算法有效性等级: {quality_results['algorithm_effectiveness_grade']}")
    
    print("\n第三步：请求分类分析")
    clustering_results = analyzer.run_clustering_analysis()
    print(f"✓ 聚类分析完成，识别出{clustering_results['cluster_count']}种请求类型")
    
    print("\n第四步：剪枝策略分析")
    pruning_results = analyzer.run_pruning_analysis()
    print(f"✓ 剪枝分析完成，风险评估: {pruning_results['risk_assessment']}")
    
    # 4. 生成可视化和报告
    print("\n第五步：生成可视化图表")
    all_results = {
        'statistics': stats_results,
        'quality': quality_results,
        'clustering': clustering_results,
        'pruning': pruning_results
    }
    
    viz_files = analyzer.create_visualizations(all_results)
    print(f"✓ 生成{len(viz_files)}个可视化文件")
    
    print("\n第六步：生成分析报告")
    report_files = analyzer.generate_reports(all_results)
    print(f"✓ 生成{len(report_files)}个报告文件")
    
    print("\n分步示例完成！")
    return analyzer, all_results


def run_custom_analysis_example():
    """运行自定义分析示例"""
    print("=" * 60)
    print("全排列路径算法有效性分析 - 自定义示例")
    print("=" * 60)
    
    # 1. 加载数据
    df = load_sample_data()
    
    # 2. 创建分析器
    analyzer = FullPermutationAnalyzer(df, output_dir='output/custom_example')
    
    # 3. 自定义分析参数
    print("\n执行自定义统计分析...")
    
    # 直接使用底层分析器进行更详细的分析
    stats_analyzer = analyzer.statistics_analyzer
    
    # 单请求分析
    single_request_results = stats_analyzer.analyze_single_request_stats()
    print("单请求分析完成")
    
    # 全局分析
    global_results = stats_analyzer.analyze_global_stats()
    print("全局分析完成")
    
    # 打印一些详细结果
    print("\n=== 详细分析结果示例 ===")
    
    # 显示异常检测结果
    if 'anomaly_detection' in single_request_results:
        anomalies = single_request_results['anomaly_detection']
        print(f"零损失请求数量: {len(anomalies.get('zero_loss_requests', []))}")
        print(f"高复杂度请求数量: {len(anomalies.get('high_complexity_requests', []))}")
    
    # 显示相关性分析结果
    if 'correlation_analysis' in global_results:
        corr_analysis = global_results['correlation_analysis']
        if 'strong_correlations' in corr_analysis:
            print(f"发现{len(corr_analysis['strong_correlations'])}个强相关关系")
    
    # 4. 保存自定义分析结果
    print("\n保存自定义分析结果...")
    
    # 组合统计分析结果
    stats_results = {
        'single_request_stats': single_request_results,
        'global_stats': global_results,
        'basic_info': {
            '总请求数': len(df['req_id'].unique()),
            '总路径数': len(df),
            '平均每请求路径数': len(df) / len(df['req_id'].unique())
        }
    }
    
    # 运行其他分析模块以获得完整结果
    print("运行质量分析...")
    quality_results = analyzer.run_quality_analysis()
    
    print("运行聚类分析...")
    clustering_results = analyzer.run_clustering_analysis()
    
    print("运行剪枝分析...")
    pruning_results = analyzer.run_pruning_analysis()
    
    # 组合所有结果
    all_results = {
        'statistics': stats_results,
        'quality': quality_results,
        'clustering': clustering_results,
        'pruning': pruning_results
    }
    
    # 生成可视化图表
    print("生成可视化图表...")
    viz_files = analyzer.create_visualizations(all_results)
    print(f"✓ 生成{len(viz_files)}个可视化文件")
    
    # 生成分析报告
    print("生成分析报告...")
    report_files = analyzer.generate_reports(all_results)
    print(f"✓ 生成{len(report_files)}个报告文件")
    
    # 保存完整结果到JSON
    print("保存完整分析结果...")
    # 使用report_generator保存JSON数据
    analyzer.report_generator.save_json_data(all_results, 'custom_analysis_results.json')
    
    print("\n自定义示例完成！")
    return analyzer


def main():
    """主函数"""
    print("全排列路径算法有效性分析系统演示")
    print("请选择运行模式:")
    print("1. 基础示例 - 一键完整分析")
    print("2. 分步示例 - 逐步执行分析")
    print("3. 自定义示例 - 详细自定义分析")
    
    try:
        choice = input("\n请输入选择 (1/2/3): ").strip()
        
        if choice == '1':
            analyzer, results = run_basic_example()
        elif choice == '2':
            analyzer, results = run_step_by_step_example()
        elif choice == '3':
            analyzer = run_custom_analysis_example()
        else:
            print("无效选择，运行基础示例")
            analyzer, results = run_basic_example()
        
        print(f"\n所有结果已保存到: {analyzer.output_dir}")
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"\n运行过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 