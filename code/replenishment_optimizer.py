"""
商品补货优化算法

解决问题：在点位现有库存基础上，通过补货使最终商品比例尽量接近期望比例。
考虑仓库库存约束和补货总量约束。

作者：AI助手  
日期：2024
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import math
from scipy.optimize import minimize_scalar


class ReplenishmentOptimizer:
    """
    商品补货优化器
    
    在点位现有库存基础上，优化补货数量以达到期望的商品比例。
    """
    
    def __init__(self, products: List[str], warehouse_stocks: List[int], 
                 current_stocks: List[int], target_ratios: List[float]):
        """
        初始化补货优化器
        
        Args:
            products: 商品名称列表
            warehouse_stocks: 仓库各商品库存数量 [Na, Nb, ...]
            current_stocks: 点位各商品当前库存 [Ga, Gb, ...]  
            target_ratios: 各商品期望比例 [ra, rb, ...]
        """
        self.products = products
        self.warehouse_stocks = np.array(warehouse_stocks)
        self.current_stocks = np.array(current_stocks)
        self.target_ratios = np.array(target_ratios)
        self.n_products = len(products)
        
        # 输入验证
        self._validate_inputs()
        
        # 标准化比例（确保和为1）
        self.target_ratios = self.target_ratios / np.sum(self.target_ratios)
        
        # 计算当前总库存
        self.current_total = np.sum(self.current_stocks)
    
    def _validate_inputs(self):
        """验证输入参数的有效性"""
        lengths = [len(self.products), len(self.warehouse_stocks), 
                  len(self.current_stocks), len(self.target_ratios)]
        if not all(l == lengths[0] for l in lengths):
            raise ValueError("商品、仓库库存、当前库存、期望比例的数量必须一致")
        
        if any(s < 0 for s in self.warehouse_stocks):
            raise ValueError("仓库库存不能为负数")
        
        if any(s < 0 for s in self.current_stocks):
            raise ValueError("当前库存不能为负数")
        
        if any(r < 0 for r in self.target_ratios):
            raise ValueError("期望比例不能为负数")
        
        if sum(self.target_ratios) == 0:
            raise ValueError("期望比例和不能为0")
    
    def optimize_fixed_replenishment_total(self, replenishment_total: int) -> Tuple[np.ndarray, Dict]:
        """
        固定补货总量的比例优化
        
        给定补货总量，优化各商品的补货分配以最接近期望比例。
        
        Args:
            replenishment_total: 总补货数量
            
        Returns:
            replenishment: 各商品补货数量 [Pa, Pb, ...]
            info: 优化信息
        """
        if replenishment_total <= 0:
            return np.zeros(self.n_products, dtype=int), {"status": "no_replenishment"}
        
        if replenishment_total > np.sum(self.warehouse_stocks):
            raise ValueError(f"补货总量{replenishment_total}超过仓库总库存{np.sum(self.warehouse_stocks)}")
        
        # 补货后的总量
        final_total = self.current_total + replenishment_total
        
        # 计算理想的补货后各商品数量
        target_final_quantities = final_total * self.target_ratios
        
        # 计算理想补货数量（不能为负数）
        ideal_replenishment = np.maximum(0, target_final_quantities - self.current_stocks)
        
        # 处理仓库库存约束
        feasible_replenishment = np.minimum(ideal_replenishment, self.warehouse_stocks)
        
        # 分配剩余补货量
        allocated_total = np.sum(feasible_replenishment)
        remaining = replenishment_total - allocated_total
        
        if remaining > 0:
            feasible_replenishment = self._allocate_remaining_replenishment(
                feasible_replenishment, remaining, final_total)
        elif remaining < 0:
            # 需要减少一些补货量
            feasible_replenishment = self._reduce_excess_replenishment(
                feasible_replenishment, -remaining, final_total)
        
        info = {
            "status": "success",
            "replenishment_total": replenishment_total,
            "final_total": final_total,
            "ideal_replenishment": ideal_replenishment,
            "allocated_remaining": max(0, remaining),
            "final_deviation": self._calculate_final_deviation(feasible_replenishment)
        }
        
        return feasible_replenishment.astype(int), info
    
    def optimize_target_final_total(self, target_final_total: int) -> Tuple[np.ndarray, Dict]:
        """
        目标总量的补货优化
        
        给定补货后的目标总量，计算需要的补货分配。
        
        Args:
            target_final_total: 补货后的目标总量
            
        Returns:
            replenishment: 各商品补货数量
            info: 优化信息
        """
        if target_final_total <= self.current_total:
            return np.zeros(self.n_products, dtype=int), {"status": "no_replenishment_needed"}
        
        replenishment_total = target_final_total - self.current_total
        return self.optimize_fixed_replenishment_total(replenishment_total)
    
    def optimize_adaptive_replenishment(self, min_replenishment: int = 0, 
                                      max_replenishment: Optional[int] = None) -> Tuple[np.ndarray, Dict]:
        """
        自适应补货量优化
        
        自动寻找最优的补货总量，使补货后比例最接近期望比例。
        
        Args:
            min_replenishment: 最小补货总量
            max_replenishment: 最大补货总量（默认为仓库总库存）
            
        Returns:
            replenishment: 各商品补货数量
            info: 优化信息
        """
        if max_replenishment is None:
            max_replenishment = min(np.sum(self.warehouse_stocks), 
                                  10 * self.current_total)  # 设置合理上限
        
        if min_replenishment >= max_replenishment:
            return np.zeros(self.n_products, dtype=int), {"status": "invalid_range"}
        
        # 定义目标函数：补货后的比例偏差
        def objective_function(replenishment_total):
            if replenishment_total < min_replenishment:
                return float('inf')
            try:
                replenishment, _ = self.optimize_fixed_replenishment_total(int(replenishment_total))
                return self._calculate_final_deviation(replenishment)
            except:
                return float('inf')
        
        # 使用黄金分割搜索找到最优补货总量
        result = minimize_scalar(objective_function, 
                               bounds=(min_replenishment, max_replenishment),
                               method='bounded')
        
        optimal_replenishment_total = int(result.x)
        optimal_replenishment, info = self.optimize_fixed_replenishment_total(optimal_replenishment_total)
        
        info.update({
            "optimization_method": "adaptive",
            "optimal_replenishment_total": optimal_replenishment_total,
            "search_result": result
        })
        
        return optimal_replenishment, info
    
    def _allocate_remaining_replenishment(self, replenishment: np.ndarray, 
                                        remaining: int, final_total: int) -> np.ndarray:
        """
        分配剩余的补货数量
        
        策略：优先给比例偏差最大且有仓库库存余量的商品分配
        """
        replenishment = replenishment.copy()
        
        for _ in range(int(remaining)):
            # 计算补货后的比例
            final_quantities = self.current_stocks + replenishment
            current_ratios = final_quantities / final_total if final_total > 0 else np.zeros(self.n_products)
            
            # 计算比例偏差
            deviations = self.target_ratios - current_ratios
            
            # 只考虑有仓库库存余量的商品
            available_mask = replenishment < self.warehouse_stocks
            
            if not np.any(available_mask):
                break  # 所有商品都已达到仓库库存上限
            
            # 选择偏差最大且有余量的商品
            priority_scores = np.where(available_mask, deviations, -np.inf)
            selected_idx = np.argmax(priority_scores)
            
            replenishment[selected_idx] += 1
        
        return replenishment
    
    def _reduce_excess_replenishment(self, replenishment: np.ndarray, 
                                   excess: int, final_total: int) -> np.ndarray:
        """
        减少多余的补货数量
        
        策略：优先减少对比例改善贡献最小的商品的补货量
        """
        replenishment = replenishment.copy()
        
        for _ in range(int(excess)):
            # 只考虑补货量大于0的商品
            reducible_mask = replenishment > 0
            
            if not np.any(reducible_mask):
                break
            
            # 计算减少1个单位后的比例偏差变化
            best_reduction_idx = -1
            best_deviation_change = float('inf')
            
            for i in range(self.n_products):
                if not reducible_mask[i]:
                    continue
                
                # 尝试减少商品i的补货量
                test_replenishment = replenishment.copy()
                test_replenishment[i] -= 1
                
                current_deviation = self._calculate_final_deviation(replenishment)
                test_deviation = self._calculate_final_deviation(test_replenishment)
                deviation_change = test_deviation - current_deviation
                
                if deviation_change < best_deviation_change:
                    best_deviation_change = deviation_change
                    best_reduction_idx = i
            
            if best_reduction_idx >= 0:
                replenishment[best_reduction_idx] -= 1
        
        return replenishment
    
    def _calculate_final_deviation(self, replenishment: np.ndarray) -> float:
        """
        计算补货后的比例偏差
        
        Args:
            replenishment: 补货数量数组
            
        Returns:
            deviation: 欧几里得距离偏差
        """
        final_quantities = self.current_stocks + replenishment
        final_total = np.sum(final_quantities)
        
        if final_total == 0:
            return 0.0
        
        actual_ratios = final_quantities / final_total
        return np.sqrt(np.sum((actual_ratios - self.target_ratios) ** 2))
    
    def evaluate_replenishment_plan(self, replenishment: np.ndarray) -> Dict:
        """
        评估补货方案的质量
        
        Args:
            replenishment: 补货数量数组
            
        Returns:
            evaluation: 详细评估结果
        """
        final_quantities = self.current_stocks + replenishment
        final_total = np.sum(final_quantities)
        replenishment_total = np.sum(replenishment)
        
        if final_total == 0:
            return {
                "current_total": self.current_total,
                "replenishment_total": 0,
                "final_total": 0,
                "current_ratios": np.zeros(self.n_products),
                "final_ratios": np.zeros(self.n_products),
                "target_ratios": self.target_ratios,
                "ratio_improvements": np.zeros(self.n_products),
                "final_deviation": 0.0,
                "improvement": 0.0,
                "warehouse_utilization": np.zeros(self.n_products)
            }
        
        current_ratios = self.current_stocks / self.current_total if self.current_total > 0 else np.zeros(self.n_products)
        final_ratios = final_quantities / final_total
        
        # 计算比例改善程度
        current_deviations = np.abs(current_ratios - self.target_ratios)
        final_deviations = np.abs(final_ratios - self.target_ratios)
        ratio_improvements = current_deviations - final_deviations
        
        # 计算总体改善
        current_total_deviation = np.sqrt(np.sum(current_deviations ** 2))
        final_total_deviation = np.sqrt(np.sum(final_deviations ** 2))
        improvement = current_total_deviation - final_total_deviation
        
        return {
            "current_total": self.current_total,
            "replenishment_total": replenishment_total,
            "final_total": final_total,
            "current_ratios": current_ratios,
            "final_ratios": final_ratios,
            "target_ratios": self.target_ratios,
            "current_deviations": current_deviations,
            "final_deviations": final_deviations,
            "ratio_improvements": ratio_improvements,
            "current_total_deviation": current_total_deviation,
            "final_total_deviation": final_total_deviation,
            "improvement": improvement,
            "warehouse_utilization": np.divide(replenishment, self.warehouse_stocks, 
                                                out=np.zeros_like(replenishment, dtype=float), 
                                                where=self.warehouse_stocks!=0)
        }
    
    def compare_strategies(self, replenishment_totals: List[int]) -> Dict:
        """
        比较不同补货总量下的策略效果
        
        Args:
            replenishment_totals: 要比较的补货总量列表
            
        Returns:
            comparison: 比较结果
        """
        results = {}
        
        for total in replenishment_totals:
            try:
                replenishment, info = self.optimize_fixed_replenishment_total(total)
                evaluation = self.evaluate_replenishment_plan(replenishment)
                results[total] = {
                    "replenishment": replenishment,
                    "info": info,
                    "evaluation": evaluation
                }
            except Exception as e:
                results[total] = {"error": str(e)}
        
        # 添加自适应策略
        try:
            adaptive_replenishment, adaptive_info = self.optimize_adaptive_replenishment()
            adaptive_evaluation = self.evaluate_replenishment_plan(adaptive_replenishment)
            results["adaptive"] = {
                "replenishment": adaptive_replenishment,
                "info": adaptive_info,
                "evaluation": adaptive_evaluation
            }
        except Exception as e:
            results["adaptive"] = {"error": str(e)}
        
        return results


def print_replenishment_result(optimizer: ReplenishmentOptimizer, 
                             replenishment: np.ndarray, 
                             info: Dict):
    """
    打印补货结果
    
    Args:
        optimizer: 补货优化器实例
        replenishment: 补货结果
        info: 算法信息
    """
    evaluation = optimizer.evaluate_replenishment_plan(replenishment)
    
    print("=== 商品补货方案 ===")
    print(f"当前总库存: {evaluation['current_total']}")
    print(f"补货总量: {evaluation['replenishment_total']}")
    print(f"补货后总量: {evaluation['final_total']}")
    print(f"当前总偏差: {evaluation['current_total_deviation']:.4f}")
    print(f"补货后总偏差: {evaluation['final_total_deviation']:.4f}")
    print(f"改善程度: {evaluation['improvement']:.4f}")
    print()
    
    print("商品详情:")
    print(f"{'商品':<8} {'仓库库存':<8} {'当前库存':<8} {'补货量':<8} {'补货后':<8} "
          f"{'期望比例':<8} {'当前比例':<8} {'补货后比例':<8} {'改善':<8}")
    print("-" * 90)
    
    for i, product in enumerate(optimizer.products):
        current_ratio = evaluation['current_ratios'][i]
        final_ratio = evaluation['final_ratios'][i]
        target_ratio = evaluation['target_ratios'][i]
        improvement = evaluation['ratio_improvements'][i]
        final_quantity = optimizer.current_stocks[i] + replenishment[i]
        
        print(f"{product:<8} {optimizer.warehouse_stocks[i]:<8} {optimizer.current_stocks[i]:<8} "
              f"{replenishment[i]:<8} {final_quantity:<8} "
              f"{target_ratio:<8.3f} {current_ratio:<8.3f} {final_ratio:<8.3f} {improvement:<8.3f}")


if __name__ == "__main__":
    # 使用示例
    products = ['a', 'b', 'c', 'd', 'e', 'f']
    warehouse_stocks = [100, 80, 120, 60, 90, 110]  # 仓库库存
    current_stocks = [5, 2, 8, 0, 3, 7]  # 点位当前库存
    target_ratios = [0.2, 0.15, 0.25, 0.1, 0.15, 0.15]  # 期望比例
    
    # 创建补货优化器
    optimizer = ReplenishmentOptimizer(products, warehouse_stocks, current_stocks, target_ratios)
    
    print("=== 固定补货总量策略 ===")
    replenishment1, info1 = optimizer.optimize_fixed_replenishment_total(50)
    print_replenishment_result(optimizer, replenishment1, info1)
    
    print("\n=== 目标总量策略 ===")
    replenishment2, info2 = optimizer.optimize_target_final_total(100)
    print_replenishment_result(optimizer, replenishment2, info2)
    
    print("\n=== 自适应补货策略 ===")
    replenishment3, info3 = optimizer.optimize_adaptive_replenishment(min_replenishment=30, max_replenishment=100)
    print_replenishment_result(optimizer, replenishment3, info3)
