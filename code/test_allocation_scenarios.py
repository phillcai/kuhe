"""
商品配比优化算法测试场景

测试不同约束条件下算法的表现
"""

from product_allocation_optimizer import ProductAllocationOptimizer, print_allocation_result
import numpy as np


def test_scenario_1():
    """场景1：库存充足，完美分配"""
    print("=" * 60)
    print("场景1：库存充足的理想情况")
    print("=" * 60)
    
    products = ['a', 'b', 'c', 'd', 'e', 'f']
    stocks = [100, 80, 120, 60, 90, 110]  
    target_ratios = [0.2, 0.15, 0.25, 0.1, 0.15, 0.15]  
    total_quantity = 200  
    
    optimizer = ProductAllocationOptimizer(products, stocks, target_ratios)
    allocation, info = optimizer.find_optimal_allocation(total_quantity)
    print_allocation_result(optimizer, allocation, info)


def test_scenario_2():
    """场景2：部分商品库存不足"""
    print("\n" + "=" * 60)
    print("场景2：部分商品库存不足的约束情况")
    print("=" * 60)
    
    products = ['a', 'b', 'c', 'd', 'e', 'f']
    stocks = [15, 10, 25, 5, 18, 12]  # 库存较少
    target_ratios = [0.2, 0.15, 0.25, 0.1, 0.15, 0.15]  
    total_quantity = 80  # 接近库存总量
    
    optimizer = ProductAllocationOptimizer(products, stocks, target_ratios)
    
    print("\n--- 比例分配算法 ---")
    allocation1, info1 = optimizer.proportional_allocation(total_quantity)
    print_allocation_result(optimizer, allocation1, info1)
    
    print("\n--- 贪心优化算法 ---")
    allocation2, info2 = optimizer.greedy_optimization(total_quantity)
    print_allocation_result(optimizer, allocation2, info2)


def test_scenario_3():
    """场景3：极端不平衡的期望比例"""
    print("\n" + "=" * 60)
    print("场景3：极端不平衡的期望比例")
    print("=" * 60)
    
    products = ['主力商品', '辅助1', '辅助2', '辅助3']
    stocks = [50, 20, 15, 25]  
    target_ratios = [0.8, 0.1, 0.05, 0.05]  # 主力商品占80%
    total_quantity = 100  
    
    optimizer = ProductAllocationOptimizer(products, stocks, target_ratios)
    
    print("\n--- 比例分配算法 ---")
    allocation1, info1 = optimizer.proportional_allocation(total_quantity)
    print_allocation_result(optimizer, allocation1, info1)
    
    print("\n--- 贪心优化算法 ---")
    allocation2, info2 = optimizer.greedy_optimization(total_quantity)
    print_allocation_result(optimizer, allocation2, info2)


def test_scenario_4():
    """场景4：小数量分配的精度问题"""
    print("\n" + "=" * 60)
    print("场景4：小数量分配的精度问题")
    print("=" * 60)
    
    products = ['a', 'b', 'c', 'd', 'e']
    stocks = [10, 10, 10, 10, 10]  
    target_ratios = [0.3, 0.25, 0.2, 0.15, 0.1]  
    total_quantity = 13  # 小数量，难以精确分配
    
    optimizer = ProductAllocationOptimizer(products, stocks, target_ratios)
    
    print("\n--- 比例分配算法 ---")
    allocation1, info1 = optimizer.proportional_allocation(total_quantity)
    print_allocation_result(optimizer, allocation1, info1)
    
    print("\n--- 贪心优化算法 ---")
    allocation2, info2 = optimizer.greedy_optimization(total_quantity)
    print_allocation_result(optimizer, allocation2, info2)


def test_scenario_5():
    """场景5：库存严重不足"""
    print("\n" + "=" * 60)
    print("场景5：库存严重不足，需要大幅调整比例")
    print("=" * 60)
    
    products = ['a', 'b', 'c', 'd']
    stocks = [5, 2, 8, 1]  # 总库存16
    target_ratios = [0.4, 0.3, 0.2, 0.1]  
    total_quantity = 15  # 接近总库存上限
    
    optimizer = ProductAllocationOptimizer(products, stocks, target_ratios)
    
    print("\n--- 比例分配算法 ---")
    allocation1, info1 = optimizer.proportional_allocation(total_quantity)
    print_allocation_result(optimizer, allocation1, info1)
    
    print("\n--- 贪心优化算法 ---")
    allocation2, info2 = optimizer.greedy_optimization(total_quantity)
    print_allocation_result(optimizer, allocation2, info2)


def compare_algorithms_performance():
    """比较不同算法在多个场景下的性能"""
    print("\n" + "=" * 60)
    print("算法性能对比总结")
    print("=" * 60)
    
    scenarios = [
        ("理想情况", ['a','b','c','d'], [100,80,60,90], [0.3,0.25,0.2,0.25], 100),
        ("库存约束", ['a','b','c','d'], [8,6,4,7], [0.3,0.25,0.2,0.25], 20),
        ("不平衡比例", ['a','b','c','d'], [50,30,20,40], [0.7,0.1,0.1,0.1], 80),
        ("小数量", ['a','b','c','d'], [10,10,10,10], [0.4,0.3,0.2,0.1], 7),
    ]
    
    print(f"{'场景':<12} {'方法':<8} {'欧几里得偏差':<12} {'最大偏差':<10}")
    print("-" * 50)
    
    for name, products, stocks, ratios, total in scenarios:
        optimizer = ProductAllocationOptimizer(products, stocks, ratios)
        
        # 比例分配
        alloc1, _ = optimizer.proportional_allocation(total)
        eval1 = optimizer.evaluate_solution(alloc1)
        
        # 贪心优化  
        alloc2, _ = optimizer.greedy_optimization(total)
        eval2 = optimizer.evaluate_solution(alloc2)
        
        print(f"{name:<12} {'比例':<8} {eval1['euclidean_deviation']:<12.4f} {eval1['max_deviation']:<10.4f}")
        print(f"{'':<12} {'贪心':<8} {eval2['euclidean_deviation']:<12.4f} {eval2['max_deviation']:<10.4f}")
        print()


if __name__ == "__main__":
    test_scenario_1()
    test_scenario_2() 
    test_scenario_3()
    test_scenario_4()
    test_scenario_5()
    compare_algorithms_performance()
