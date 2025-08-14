"""
补货优化算法对比分析

对比启发式算法与线性规划方法在不同场景下的性能表现

作者：AI助手
日期：2024
"""

import numpy as np
import time
from typing import List, Dict, Tuple
import pandas as pd

from replenishment_optimizer import ReplenishmentOptimizer, print_replenishment_result
from linear_programming_replenishment import LinearProgrammingReplenishmentOptimizer, print_lp_replenishment_result


class AlgorithmComparator:
    """
    算法对比分析器
    
    对比启发式算法与线性规划方法的性能
    """
    
    def __init__(self, products: List[str], warehouse_stocks: List[int], 
                 current_stocks: List[int], target_ratios: List[float]):
        """初始化对比器"""
        self.products = products
        self.warehouse_stocks = warehouse_stocks
        self.current_stocks = current_stocks
        self.target_ratios = target_ratios
        
        # 创建两个优化器
        self.heuristic_optimizer = ReplenishmentOptimizer(
            products, warehouse_stocks, current_stocks, target_ratios)
        self.lp_optimizer = LinearProgrammingReplenishmentOptimizer(
            products, warehouse_stocks, current_stocks, target_ratios)
    
    def compare_fixed_total_methods(self, replenishment_total: int) -> Dict:
        """
        对比固定补货总量方法
        
        Args:
            replenishment_total: 补货总量
            
        Returns:
            comparison: 对比结果
        """
        results = {}
        
        # 启发式方法
        start_time = time.time()
        try:
            heuristic_replenishment, heuristic_info = self.heuristic_optimizer.optimize_fixed_replenishment_total(replenishment_total)
            heuristic_time = time.time() - start_time
            heuristic_evaluation = self.heuristic_optimizer.evaluate_replenishment_plan(heuristic_replenishment)
            
            results['heuristic'] = {
                'replenishment': heuristic_replenishment,
                'info': heuristic_info,
                'evaluation': heuristic_evaluation,
                'computation_time': heuristic_time,
                'success': True
            }
        except Exception as e:
            results['heuristic'] = {
                'error': str(e),
                'success': False,
                'computation_time': time.time() - start_time
            }
        
        # 线性规划方法
        start_time = time.time()
        try:
            lp_replenishment, lp_info = self.lp_optimizer.optimize_fixed_replenishment_total_lp(replenishment_total)
            lp_time = time.time() - start_time
            lp_evaluation = self.lp_optimizer.evaluate_replenishment_plan(lp_replenishment)
            
            results['linear_programming'] = {
                'replenishment': lp_replenishment,
                'info': lp_info,
                'evaluation': lp_evaluation,
                'computation_time': lp_time,
                'success': True
            }
        except Exception as e:
            results['linear_programming'] = {
                'error': str(e),
                'success': False,
                'computation_time': time.time() - start_time
            }
        
        return results
    
    def compare_adaptive_methods(self, min_replenishment: int = 0, max_replenishment: int = None) -> Dict:
        """
        对比自适应补货方法
        
        Args:
            min_replenishment: 最小补货量
            max_replenishment: 最大补货量
            
        Returns:
            comparison: 对比结果
        """
        if max_replenishment is None:
            max_replenishment = min(np.sum(self.warehouse_stocks), 200)
        
        results = {}
        
        # 启发式方法
        start_time = time.time()
        try:
            heuristic_replenishment, heuristic_info = self.heuristic_optimizer.optimize_adaptive_replenishment(
                min_replenishment, max_replenishment)
            heuristic_time = time.time() - start_time
            heuristic_evaluation = self.heuristic_optimizer.evaluate_replenishment_plan(heuristic_replenishment)
            
            results['heuristic'] = {
                'replenishment': heuristic_replenishment,
                'info': heuristic_info,
                'evaluation': heuristic_evaluation,
                'computation_time': heuristic_time,
                'success': True
            }
        except Exception as e:
            results['heuristic'] = {
                'error': str(e),
                'success': False,
                'computation_time': time.time() - start_time
            }
        
        # 线性规划方法
        start_time = time.time()
        try:
            lp_replenishment, lp_info = self.lp_optimizer.optimize_adaptive_replenishment_lp(
                min_replenishment, max_replenishment)
            lp_time = time.time() - start_time
            lp_evaluation = self.lp_optimizer.evaluate_replenishment_plan(lp_replenishment)
            
            results['linear_programming'] = {
                'replenishment': lp_replenishment,
                'info': lp_info,
                'evaluation': lp_evaluation,
                'computation_time': lp_time,
                'success': True
            }
        except Exception as e:
            results['linear_programming'] = {
                'error': str(e),
                'success': False,
                'computation_time': time.time() - start_time
            }
        
        return results
    
    def comprehensive_comparison(self, replenishment_totals: List[int]) -> pd.DataFrame:
        """
        全面对比不同补货总量下两种方法的性能
        
        Args:
            replenishment_totals: 要测试的补货总量列表
            
        Returns:
            comparison_df: 对比结果DataFrame
        """
        comparison_data = []
        
        for total in replenishment_totals:
            print(f"测试补货总量: {total}")
            
            comparison = self.compare_fixed_total_methods(total)
            
            row = {'replenishment_total': total}
            
            # 启发式方法结果
            if comparison['heuristic']['success']:
                heuristic_eval = comparison['heuristic']['evaluation']
                row.update({
                    'heuristic_final_deviation': heuristic_eval['final_total_deviation'],
                    'heuristic_improvement': heuristic_eval['improvement'],
                    'heuristic_time': comparison['heuristic']['computation_time'],
                    'heuristic_success': True
                })
            else:
                row.update({
                    'heuristic_final_deviation': np.nan,
                    'heuristic_improvement': np.nan,
                    'heuristic_time': comparison['heuristic']['computation_time'],
                    'heuristic_success': False
                })
            
            # 线性规划方法结果
            if comparison['linear_programming']['success']:
                lp_eval = comparison['linear_programming']['evaluation']
                lp_info = comparison['linear_programming']['info']
                row.update({
                    'lp_final_deviation': lp_eval['final_total_deviation'],
                    'lp_improvement': lp_eval['improvement'],
                    'lp_time': comparison['linear_programming']['computation_time'],
                    'lp_success': True,
                    'lp_method': lp_info.get('method', 'unknown')
                })
            else:
                row.update({
                    'lp_final_deviation': np.nan,
                    'lp_improvement': np.nan,
                    'lp_time': comparison['linear_programming']['computation_time'],
                    'lp_success': False,
                    'lp_method': 'failed'
                })
            
            comparison_data.append(row)
        
        return pd.DataFrame(comparison_data)
    
    def analyze_performance_metrics(self, comparison_df: pd.DataFrame) -> Dict:
        """
        分析性能指标
        
        Args:
            comparison_df: 对比结果DataFrame
            
        Returns:
            analysis: 性能分析结果
        """
        analysis = {}
        
        # 成功率
        heuristic_success_rate = comparison_df['heuristic_success'].mean()
        lp_success_rate = comparison_df['lp_success'].mean()
        
        # 有效数据（成功求解的情况）
        valid_data = comparison_df[
            comparison_df['heuristic_success'] & comparison_df['lp_success']
        ]
        
        if len(valid_data) > 0:
            # 解质量对比
            heuristic_better_count = (valid_data['heuristic_final_deviation'] < valid_data['lp_final_deviation']).sum()
            lp_better_count = (valid_data['lp_final_deviation'] < valid_data['heuristic_final_deviation']).sum()
            tie_count = len(valid_data) - heuristic_better_count - lp_better_count
            
            # 计算时间对比
            avg_heuristic_time = valid_data['heuristic_time'].mean()
            avg_lp_time = valid_data['lp_time'].mean()
            
            # 偏差统计
            avg_heuristic_deviation = valid_data['heuristic_final_deviation'].mean()
            avg_lp_deviation = valid_data['lp_final_deviation'].mean()
            
            analysis = {
                'success_rates': {
                    'heuristic': heuristic_success_rate,
                    'linear_programming': lp_success_rate
                },
                'solution_quality': {
                    'heuristic_better': heuristic_better_count,
                    'lp_better': lp_better_count,
                    'tie': tie_count,
                    'total_valid': len(valid_data)
                },
                'computation_time': {
                    'avg_heuristic_time': avg_heuristic_time,
                    'avg_lp_time': avg_lp_time,
                    'speedup_ratio': avg_lp_time / avg_heuristic_time if avg_heuristic_time > 0 else float('inf')
                },
                'average_deviations': {
                    'heuristic': avg_heuristic_deviation,
                    'linear_programming': avg_lp_deviation
                }
            }
        else:
            analysis = {
                'success_rates': {
                    'heuristic': heuristic_success_rate,
                    'linear_programming': lp_success_rate
                },
                'note': '没有足够的有效对比数据'
            }
        
        return analysis


def print_comparison_summary(comparison_df: pd.DataFrame, analysis: Dict):
    """
    打印对比总结
    """
    print("=" * 80)
    print("算法对比总结")
    print("=" * 80)
    
    print(f"测试用例数量: {len(comparison_df)}")
    print(f"启发式算法成功率: {analysis['success_rates']['heuristic']:.1%}")
    print(f"线性规划算法成功率: {analysis['success_rates']['linear_programming']:.1%}")
    
    if 'solution_quality' in analysis:
        quality = analysis['solution_quality']
        print(f"\n解质量对比 (共{quality['total_valid']}个有效对比):")
        print(f"  启发式算法更优: {quality['heuristic_better']} 次")
        print(f"  线性规划算法更优: {quality['lp_better']} 次")
        print(f"  平局: {quality['tie']} 次")
        
        time_stats = analysis['computation_time']
        print(f"\n计算时间对比:")
        print(f"  启发式算法平均时间: {time_stats['avg_heuristic_time']*1000:.2f} ms")
        print(f"  线性规划算法平均时间: {time_stats['avg_lp_time']*1000:.2f} ms")
        print(f"  启发式算法速度优势: {time_stats['speedup_ratio']:.1f}x")
        
        deviations = analysis['average_deviations']
        print(f"\n平均偏差对比:")
        print(f"  启发式算法: {deviations['heuristic']:.6f}")
        print(f"  线性规划算法: {deviations['linear_programming']:.6f}")
    
    print("\n详细对比表:")
    print(comparison_df.to_string(index=False, float_format='%.6f'))


def test_scenario_comparison():
    """测试不同场景下的算法对比"""
    
    print("=" * 80)
    print("场景1：均衡库存状况")
    print("=" * 80)
    
    products = ['a', 'b', 'c', 'd', 'e', 'f']
    warehouse_stocks = [100, 80, 120, 60, 90, 110]
    current_stocks = [18, 12, 22, 8, 13, 12]
    target_ratios = [0.2, 0.15, 0.25, 0.1, 0.15, 0.15]
    
    comparator = AlgorithmComparator(products, warehouse_stocks, current_stocks, target_ratios)
    
    # 测试不同的补货总量
    replenishment_totals = [20, 40, 60, 80, 100]
    comparison_df = comparator.comprehensive_comparison(replenishment_totals)
    analysis = comparator.analyze_performance_metrics(comparison_df)
    print_comparison_summary(comparison_df, analysis)
    
    print("\n" + "=" * 80)
    print("场景2：严重失衡状况")
    print("=" * 80)
    
    products2 = ['主力商品', '辅助商品A', '辅助商品B', '紧缺商品', '过量商品']
    warehouse_stocks2 = [50, 30, 25, 15, 40]
    current_stocks2 = [2, 0, 1, 0, 20]
    target_ratios2 = [0.4, 0.2, 0.15, 0.1, 0.15]
    
    comparator2 = AlgorithmComparator(products2, warehouse_stocks2, current_stocks2, target_ratios2)
    
    replenishment_totals2 = [10, 20, 30, 40, 50]
    comparison_df2 = comparator2.comprehensive_comparison(replenishment_totals2)
    analysis2 = comparator2.analyze_performance_metrics(comparison_df2)
    print_comparison_summary(comparison_df2, analysis2)
    
    print("\n" + "=" * 80)
    print("自适应方法对比")
    print("=" * 80)
    
    # 测试自适应方法
    adaptive_comparison = comparator.compare_adaptive_methods(min_replenishment=20, max_replenishment=100)
    
    print("启发式自适应方法:")
    if adaptive_comparison['heuristic']['success']:
        heuristic_eval = adaptive_comparison['heuristic']['evaluation']
        heuristic_info = adaptive_comparison['heuristic']['info']
        print(f"  补货总量: {heuristic_info.get('optimal_replenishment_total', '未知')}")
        print(f"  最终偏差: {heuristic_eval['final_total_deviation']:.6f}")
        print(f"  计算时间: {adaptive_comparison['heuristic']['computation_time']*1000:.2f} ms")
    else:
        print(f"  失败: {adaptive_comparison['heuristic']['error']}")
    
    print("\n线性规划自适应方法:")
    if adaptive_comparison['linear_programming']['success']:
        lp_eval = adaptive_comparison['linear_programming']['evaluation']
        lp_info = adaptive_comparison['linear_programming']['info']
        print(f"  补货总量: {lp_info.get('optimal_replenishment_total', '未知')}")
        print(f"  最终偏差: {lp_eval['final_total_deviation']:.6f}")
        print(f"  计算时间: {adaptive_comparison['linear_programming']['computation_time']*1000:.2f} ms")
    else:
        print(f"  失败: {adaptive_comparison['linear_programming']['error']}")


if __name__ == "__main__":
    test_scenario_comparison()
