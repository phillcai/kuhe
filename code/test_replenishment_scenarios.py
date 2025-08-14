"""
补货优化算法测试场景

测试不同库存状况和约束条件下补货算法的表现
"""

from replenishment_optimizer import ReplenishmentOptimizer, print_replenishment_result
import numpy as np


def test_scenario_1():
    """场景1：均衡库存，需要小幅调整"""
    print("=" * 60)
    print("场景1：均衡库存状况，需要小幅调整比例")
    print("=" * 60)
    
    products = ['a', 'b', 'c', 'd', 'e', 'f']
    warehouse_stocks = [100, 80, 120, 60, 90, 110]  
    current_stocks = [18, 12, 22, 8, 13, 12]  # 相对均衡的库存
    target_ratios = [0.2, 0.15, 0.25, 0.1, 0.15, 0.15]  
    
    optimizer = ReplenishmentOptimizer(products, warehouse_stocks, current_stocks, target_ratios)
    
    print(f"当前库存总量: {sum(current_stocks)}")
    print(f"当前比例: {[f'{x/sum(current_stocks):.3f}' for x in current_stocks]}")
    print(f"期望比例: {[f'{x:.3f}' for x in target_ratios]}")
    print()
    
    replenishment, info = optimizer.optimize_adaptive_replenishment(min_replenishment=20, max_replenishment=80)
    print_replenishment_result(optimizer, replenishment, info)


def test_scenario_2():
    """场景2：严重失衡，部分商品库存为0"""
    print("\n" + "=" * 60)
    print("场景2：严重失衡，部分商品断货")
    print("=" * 60)
    
    products = ['主力商品', '辅助商品A', '辅助商品B', '紧缺商品', '过量商品']
    warehouse_stocks = [50, 30, 25, 15, 40]  
    current_stocks = [2, 0, 1, 0, 20]  # 严重失衡
    target_ratios = [0.4, 0.2, 0.15, 0.1, 0.15]  
    
    optimizer = ReplenishmentOptimizer(products, warehouse_stocks, current_stocks, target_ratios)
    
    print("--- 固定补货总量30 ---")
    replenishment1, info1 = optimizer.optimize_fixed_replenishment_total(30)
    print_replenishment_result(optimizer, replenishment1, info1)
    
    print("\n--- 自适应补货策略 ---")
    replenishment2, info2 = optimizer.optimize_adaptive_replenishment(min_replenishment=20, max_replenishment=60)
    print_replenishment_result(optimizer, replenishment2, info2)


def test_scenario_3():
    """场景3：仓库库存不足，需要妥协"""
    print("\n" + "=" * 60)
    print("场景3：仓库库存不足，需要调整期望")
    print("=" * 60)
    
    products = ['a', 'b', 'c', 'd']
    warehouse_stocks = [8, 5, 12, 3]  # 仓库库存有限
    current_stocks = [2, 1, 3, 0]  
    target_ratios = [0.4, 0.3, 0.2, 0.1]  
    
    optimizer = ReplenishmentOptimizer(products, warehouse_stocks, current_stocks, target_ratios)
    
    print("--- 目标总量50（超出仓库能力）---")
    try:
        replenishment1, info1 = optimizer.optimize_target_final_total(50)
        print_replenishment_result(optimizer, replenishment1, info1)
    except Exception as e:
        print(f"错误: {e}")
    
    print("\n--- 目标总量30（在仓库能力内）---")
    replenishment2, info2 = optimizer.optimize_target_final_total(30)
    print_replenishment_result(optimizer, replenishment2, info2)


def test_scenario_4():
    """场景4：极端比例要求"""
    print("\n" + "=" * 60)
    print("场景4：极端比例要求（一个商品占主导）")
    print("=" * 60)
    
    products = ['主导商品', '辅助1', '辅助2', '辅助3']
    warehouse_stocks = [100, 20, 15, 10]  
    current_stocks = [10, 8, 6, 4]  # 当前比较均衡
    target_ratios = [0.8, 0.1, 0.05, 0.05]  # 极端不平衡的期望
    
    optimizer = ReplenishmentOptimizer(products, warehouse_stocks, current_stocks, target_ratios)
    
    print("--- 自适应补货策略 ---")
    replenishment, info = optimizer.optimize_adaptive_replenishment(max_replenishment=100)
    print_replenishment_result(optimizer, replenishment, info)


def test_scenario_5():
    """场景5：已经接近理想比例"""
    print("\n" + "=" * 60)
    print("场景5：当前比例已接近理想，微调优化")
    print("=" * 60)
    
    products = ['a', 'b', 'c', 'd', 'e']
    warehouse_stocks = [50, 40, 60, 30, 45]  
    current_stocks = [19, 14, 24, 9, 14]  # 接近期望比例
    target_ratios = [0.25, 0.15, 0.3, 0.1, 0.2]  
    
    optimizer = ReplenishmentOptimizer(products, warehouse_stocks, current_stocks, target_ratios)
    
    print("--- 小量补货优化 ---")
    replenishment, info = optimizer.optimize_adaptive_replenishment(min_replenishment=5, max_replenishment=20)
    print_replenishment_result(optimizer, replenishment, info)


def compare_all_strategies():
    """比较所有策略的性能"""
    print("\n" + "=" * 60)
    print("策略性能对比")
    print("=" * 60)
    
    # 使用一个标准测试用例
    products = ['a', 'b', 'c', 'd']
    warehouse_stocks = [50, 40, 60, 30]  
    current_stocks = [5, 2, 8, 1]  
    target_ratios = [0.3, 0.25, 0.3, 0.15]  
    
    optimizer = ReplenishmentOptimizer(products, warehouse_stocks, current_stocks, target_ratios)
    
    # 测试不同的补货总量
    replenishment_totals = [20, 40, 60, 80]
    
    print(f"{'策略':<15} {'补货总量':<8} {'补货后偏差':<12} {'改善程度':<10} {'仓库利用率':<10}")
    print("-" * 65)
    
    for total in replenishment_totals:
        try:
            replenishment, _ = optimizer.optimize_fixed_replenishment_total(total)
            evaluation = optimizer.evaluate_replenishment_plan(replenishment)
            avg_utilization = np.mean(evaluation['warehouse_utilization'])
            
            print(f"{'固定总量':<15} {total:<8} {evaluation['final_total_deviation']:<12.4f} "
                  f"{evaluation['improvement']:<10.4f} {avg_utilization:<10.3f}")
        except Exception as e:
            print(f"{'固定总量':<15} {total:<8} {'错误':<12} {str(e)[:20]:<10}")
    
    # 自适应策略
    try:
        adaptive_replenishment, adaptive_info = optimizer.optimize_adaptive_replenishment()
        adaptive_evaluation = optimizer.evaluate_replenishment_plan(adaptive_replenishment)
        adaptive_total = adaptive_info.get('optimal_replenishment_total', np.sum(adaptive_replenishment))
        avg_utilization = np.mean(adaptive_evaluation['warehouse_utilization'])
        
        print(f"{'自适应':<15} {adaptive_total:<8} {adaptive_evaluation['final_total_deviation']:<12.4f} "
              f"{adaptive_evaluation['improvement']:<10.4f} {avg_utilization:<10.3f}")
    except Exception as e:
        print(f"{'自适应':<15} {'N/A':<8} {'错误':<12} {str(e)[:20]:<10}")


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 60)
    print("边界情况测试")
    print("=" * 60)
    
    # 情况1：当前库存为0
    print("--- 情况1：所有商品当前库存为0 ---")
    products = ['a', 'b', 'c']
    warehouse_stocks = [30, 20, 25]  
    current_stocks = [0, 0, 0]  
    target_ratios = [0.4, 0.35, 0.25]  
    
    optimizer = ReplenishmentOptimizer(products, warehouse_stocks, current_stocks, target_ratios)
    replenishment, info = optimizer.optimize_fixed_replenishment_total(30)
    print_replenishment_result(optimizer, replenishment, info)
    
    # 情况2：某些商品仓库库存为0
    print("\n--- 情况2：部分商品仓库库存为0 ---")
    warehouse_stocks = [30, 0, 25]  # b商品仓库无库存
    current_stocks = [5, 3, 4]  
    
    optimizer2 = ReplenishmentOptimizer(products, warehouse_stocks, current_stocks, target_ratios)
    replenishment2, info2 = optimizer2.optimize_adaptive_replenishment()
    print_replenishment_result(optimizer2, replenishment2, info2)


if __name__ == "__main__":
    test_scenario_1()
    test_scenario_2() 
    test_scenario_3()
    test_scenario_4()
    test_scenario_5()
    compare_all_strategies()
    test_edge_cases()
