"""
商品配比优化算法

解决问题：给定一组商品及其库存，在满足总数量约束的前提下，
尽量按期望比例分配各商品数量。

作者：AI助手
日期：2024
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import math


class ProductAllocationOptimizer:
    """
    商品配比优化器
    
    解决在库存约束下，按期望比例分配商品数量的优化问题。
    """
    
    def __init__(self, products: List[str], stocks: List[int], target_ratios: List[float]):
        """
        初始化优化器
        
        Args:
            products: 商品名称列表
            stocks: 各商品库存数量
            target_ratios: 各商品期望比例
        """
        self.products = products
        self.stocks = np.array(stocks)
        self.target_ratios = np.array(target_ratios)
        self.n_products = len(products)
        
        # 输入验证
        self._validate_inputs()
        
        # 标准化比例（确保和为1）
        self.target_ratios = self.target_ratios / np.sum(self.target_ratios)
    
    def _validate_inputs(self):
        """验证输入参数的有效性"""
        if len(self.products) != len(self.stocks) or len(self.products) != len(self.target_ratios):
            raise ValueError("商品、库存、比例的数量必须一致")
        
        if any(s < 0 for s in self.stocks):
            raise ValueError("库存不能为负数")
        
        if any(r < 0 for r in self.target_ratios):
            raise ValueError("期望比例不能为负数")
        
        if sum(self.target_ratios) == 0:
            raise ValueError("期望比例和不能为0")
    
    def proportional_allocation(self, total_quantity: int) -> Tuple[np.ndarray, Dict]:
        """
        比例分配 + 调整算法
        
        算法步骤：
        1. 按比例初始分配
        2. 处理库存不足的情况
        3. 分配剩余数量
        
        Args:
            total_quantity: 总需求数量
            
        Returns:
            allocation: 各商品分配数量
            info: 算法执行信息
        """
        if total_quantity <= 0:
            return np.zeros(self.n_products, dtype=int), {"status": "empty"}
        
        if total_quantity > np.sum(self.stocks):
            raise ValueError(f"总需求量{total_quantity}超过总库存{np.sum(self.stocks)}")
        
        # 步骤1：按比例初始分配
        initial_allocation = self.target_ratios * total_quantity
        allocation = np.floor(initial_allocation).astype(int)
        
        # 步骤2：处理库存不足的情况
        allocation = np.minimum(allocation, self.stocks)
        
        # 步骤3：分配剩余数量
        remaining = total_quantity - np.sum(allocation)
        
        if remaining > 0:
            allocation = self._allocate_remaining(allocation, remaining, initial_allocation)
        
        info = {
            "status": "success",
            "initial_allocation": initial_allocation,
            "remaining_allocated": remaining,
            "deviation": self._calculate_deviation(allocation, total_quantity)
        }
        
        return allocation, info
    
    def _allocate_remaining(self, allocation: np.ndarray, remaining: int, 
                          initial_allocation: np.ndarray) -> np.ndarray:
        """
        分配剩余数量
        
        策略：优先给偏差最大且有库存余量的商品分配
        """
        allocation = allocation.copy()
        
        for _ in range(remaining):
            # 计算每个商品的分配优先级
            current_ratios = allocation / np.sum(allocation) if np.sum(allocation) > 0 else np.zeros(self.n_products)
            deviations = self.target_ratios - current_ratios
            
            # 只考虑有库存余量的商品
            available_mask = allocation < self.stocks
            
            if not np.any(available_mask):
                break  # 所有商品都已达到库存上限
            
            # 选择偏差最大且有余量的商品
            priority_scores = np.where(available_mask, deviations, -np.inf)
            selected_idx = np.argmax(priority_scores)
            
            allocation[selected_idx] += 1
        
        return allocation
    
    def greedy_optimization(self, total_quantity: int, max_iterations: int = 10000) -> Tuple[np.ndarray, Dict]:
        """
        贪心优化算法
        
        每次选择能最小化总偏差的调整
        
        Args:
            total_quantity: 总需求数量
            max_iterations: 最大迭代次数
            
        Returns:
            allocation: 各商品分配数量
            info: 算法执行信息
        """
        if total_quantity <= 0:
            return np.zeros(self.n_products, dtype=int), {"status": "empty"}
        
        if total_quantity > np.sum(self.stocks):
            raise ValueError(f"总需求量{total_quantity}超过总库存{np.sum(self.stocks)}")
        
        # 从比例分配结果开始
        allocation, _ = self.proportional_allocation(total_quantity)
        best_deviation = self._calculate_deviation(allocation, total_quantity)
        
        improved = True
        iterations = 0
        
        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            
            # 尝试所有可能的单步调整
            for i in range(self.n_products):
                for j in range(self.n_products):
                    if i != j and allocation[i] > 0 and allocation[j] < self.stocks[j]:
                        # 尝试从商品i转移1个到商品j
                        test_allocation = allocation.copy()
                        test_allocation[i] -= 1
                        test_allocation[j] += 1
                        
                        test_deviation = self._calculate_deviation(test_allocation, total_quantity)
                        
                        if test_deviation < best_deviation:
                            allocation = test_allocation
                            best_deviation = test_deviation
                            improved = True
        
        info = {
            "status": "success",
            "iterations": iterations,
            "final_deviation": best_deviation
        }
        
        return allocation, info
    
    def _calculate_deviation(self, allocation: np.ndarray, total_quantity: int) -> float:
        """
        计算分配结果与期望比例的偏差
        
        使用欧几里得距离作为偏差度量
        """
        if total_quantity == 0:
            return 0.0
        
        actual_ratios = allocation / total_quantity
        return np.sqrt(np.sum((actual_ratios - self.target_ratios) ** 2))
    
    def evaluate_solution(self, allocation: np.ndarray) -> Dict:
        """
        评估解决方案的质量
        
        Args:
            allocation: 分配方案
            
        Returns:
            evaluation: 评估结果字典
        """
        total_allocated = np.sum(allocation)
        
        if total_allocated == 0:
            return {
                "total_quantity": 0,
                "actual_ratios": np.zeros(self.n_products),
                "target_ratios": self.target_ratios,
                "deviations": np.zeros(self.n_products),
                "euclidean_deviation": 0.0,
                "max_deviation": 0.0,
                "stock_utilization": np.zeros(self.n_products)
            }
        
        actual_ratios = allocation / total_allocated
        deviations = np.abs(actual_ratios - self.target_ratios)
        
        return {
            "total_quantity": total_allocated,
            "actual_ratios": actual_ratios,
            "target_ratios": self.target_ratios,
            "deviations": deviations,
            "euclidean_deviation": np.sqrt(np.sum(deviations ** 2)),
            "max_deviation": np.max(deviations),
            "stock_utilization": allocation / self.stocks
        }
    
    def find_optimal_allocation(self, total_quantity: int, method: str = "auto") -> Tuple[np.ndarray, Dict]:
        """
        寻找最优分配方案
        
        Args:
            total_quantity: 总需求数量
            method: 算法选择 ("proportional", "greedy", "auto")
            
        Returns:
            allocation: 最优分配方案
            info: 详细信息
        """
        if method == "proportional":
            return self.proportional_allocation(total_quantity)
        elif method == "greedy":
            return self.greedy_optimization(total_quantity)
        elif method == "auto":
            # 自动选择：小规模用贪心，大规模用比例分配
            if total_quantity <= 1000:
                return self.greedy_optimization(total_quantity)
            else:
                return self.proportional_allocation(total_quantity)
        else:
            raise ValueError(f"未知的方法: {method}")


def print_allocation_result(optimizer: ProductAllocationOptimizer, 
                          allocation: np.ndarray, 
                          info: Dict):
    """
    打印分配结果
    
    Args:
        optimizer: 优化器实例
        allocation: 分配结果
        info: 算法信息
    """
    evaluation = optimizer.evaluate_solution(allocation)
    
    print("=== 商品分配结果 ===")
    print(f"总数量: {evaluation['total_quantity']}")
    print(f"欧几里得偏差: {evaluation['euclidean_deviation']:.4f}")
    print(f"最大偏差: {evaluation['max_deviation']:.4f}")
    print()
    
    print("商品详情:")
    print(f"{'商品':<8} {'库存':<8} {'分配':<8} {'期望比例':<10} {'实际比例':<10} {'偏差':<8} {'库存利用率':<10}")
    print("-" * 80)
    
    for i, product in enumerate(optimizer.products):
        print(f"{product:<8} {optimizer.stocks[i]:<8} {allocation[i]:<8} "
              f"{evaluation['target_ratios'][i]:<10.3f} {evaluation['actual_ratios'][i]:<10.3f} "
              f"{evaluation['deviations'][i]:<8.3f} {evaluation['stock_utilization'][i]:<10.3f}")


if __name__ == "__main__":
    # 使用示例
    products = ['a', 'b', 'c', 'd', 'e', 'f']
    stocks = [100, 80, 120, 60, 90, 110]  # 各商品库存
    target_ratios = [0.2, 0.15, 0.25, 0.1, 0.15, 0.15]  # 期望比例
    total_quantity = 200  # 需要分配的总数量
    
    # 创建优化器
    optimizer = ProductAllocationOptimizer(products, stocks, target_ratios)
    
    print("=== 比例分配算法 ===")
    allocation1, info1 = optimizer.proportional_allocation(total_quantity)
    print_allocation_result(optimizer, allocation1, info1)
    
    print("\n=== 贪心优化算法 ===")
    allocation2, info2 = optimizer.greedy_optimization(total_quantity)
    print_allocation_result(optimizer, allocation2, info2)
    
    print("\n=== 自动选择算法 ===")
    allocation3, info3 = optimizer.find_optimal_allocation(total_quantity, method="auto")
    print_allocation_result(optimizer, allocation3, info3)
