"""
基于线性规划的商品补货优化算法

与启发式算法对比的数学优化方法实现
使用scipy.optimize.linprog求解线性规划问题

作者：AI助手
日期：2024
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy.optimize import linprog, minimize
import warnings


class LinearProgrammingReplenishmentOptimizer:
    """
    基于线性规划的补货优化器
    
    将补货问题建模为线性规划问题，理论上能保证全局最优解。
    """
    
    def __init__(self, products: List[str], warehouse_stocks: List[int], 
                 current_stocks: List[int], target_ratios: List[float]):
        """
        初始化线性规划补货优化器
        
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
    
    def optimize_fixed_replenishment_total_lp(self, replenishment_total: int) -> Tuple[np.ndarray, Dict]:
        """
        使用线性规划优化固定补货总量的分配
        
        数学建模：
        minimize: sum((actual_ratio_i - target_ratio_i)^2)
        subject to:
            sum(P_i) = replenishment_total
            0 <= P_i <= N_i for all i
            actual_ratio_i = (G_i + P_i) / M
            M = sum(G) + replenishment_total
        
        Args:
            replenishment_total: 总补货数量
            
        Returns:
            replenishment: 各商品补货数量
            info: 优化信息
        """
        if replenishment_total <= 0:
            return np.zeros(self.n_products, dtype=int), {"status": "no_replenishment"}
        
        if replenishment_total > np.sum(self.warehouse_stocks):
            raise ValueError(f"补货总量{replenishment_total}超过仓库总库存{np.sum(self.warehouse_stocks)}")
        
        # 补货后的总量
        final_total = self.current_total + replenishment_total
        
        # 方法1：线性规划近似求解（L1范数最小化）
        # 引入辅助变量：P_i（补货量）和 d_i^+, d_i^-（偏差变量）
        # minimize: sum(d_i^+ + d_i^-)
        # subject to:
        #   (G_i + P_i)/M - r_i = d_i^+ - d_i^-
        #   sum(P_i) = replenishment_total
        #   0 <= P_i <= N_i
        #   d_i^+, d_i^- >= 0
        
        # 变量顺序：[P_1, ..., P_n, d_1^+, ..., d_n^+, d_1^-, ..., d_n^-]
        # 总共 3n 个变量
        n = self.n_products
        
        # 目标函数系数：最小化偏差变量之和
        c = np.concatenate([
            np.zeros(n),        # P_i 系数为0
            np.ones(n),         # d_i^+ 系数为1
            np.ones(n)          # d_i^- 系数为1
        ])
        
        # 等式约束矩阵 A_eq 和右端向量 b_eq
        A_eq = []
        b_eq = []
        
        # 约束1：sum(P_i) = replenishment_total
        eq_constraint_1 = np.concatenate([
            np.ones(n),         # P_i 系数为1
            np.zeros(n),        # d_i^+ 系数为0
            np.zeros(n)         # d_i^- 系数为0
        ])
        A_eq.append(eq_constraint_1)
        b_eq.append(replenishment_total)
        
        # 约束2：(G_i + P_i)/M - r_i = d_i^+ - d_i^-
        # 即：P_i/M - d_i^+ + d_i^- = r_i - G_i/M
        for i in range(n):
            eq_constraint_2 = np.zeros(3 * n)
            eq_constraint_2[i] = 1.0 / final_total         # P_i 系数
            eq_constraint_2[n + i] = -1.0                  # d_i^+ 系数
            eq_constraint_2[2 * n + i] = 1.0               # d_i^- 系数
            A_eq.append(eq_constraint_2)
            b_eq.append(self.target_ratios[i] - self.current_stocks[i] / final_total)
        
        A_eq = np.array(A_eq)
        b_eq = np.array(b_eq)
        
        # 不等式约束边界
        # 0 <= P_i <= N_i, d_i^+, d_i^- >= 0
        bounds = []
        
        # P_i 的边界
        for i in range(n):
            bounds.append((0, self.warehouse_stocks[i]))
        
        # d_i^+ 和 d_i^- 的边界
        for i in range(2 * n):
            bounds.append((0, None))
        
        # 求解线性规划
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
        
        if not result.success:
            # 如果线性规划求解失败，回退到启发式方法
            return self._fallback_heuristic_method(replenishment_total)
        
        # 提取补货量（前n个变量）
        replenishment = result.x[:n]
        
        # 转换为整数（四舍五入）
        replenishment_int = np.round(replenishment).astype(int)
        
        # 调整以满足总量约束
        replenishment_int = self._adjust_to_total_constraint(replenishment_int, replenishment_total)
        
        info = {
            "status": "success",
            "method": "linear_programming",
            "lp_success": result.success,
            "lp_objective": result.fun if result.success else None,
            "final_total": final_total,
            "final_deviation": self._calculate_final_deviation(replenishment_int)
        }
        
        return replenishment_int, info
    
    def optimize_adaptive_replenishment_lp(self, min_replenishment: int = 0, 
                                         max_replenishment: Optional[int] = None) -> Tuple[np.ndarray, Dict]:
        """
        使用非线性优化寻找最优补货总量
        
        Args:
            min_replenishment: 最小补货总量
            max_replenishment: 最大补货总量
            
        Returns:
            replenishment: 各商品补货数量
            info: 优化信息
        """
        if max_replenishment is None:
            max_replenishment = min(np.sum(self.warehouse_stocks), 
                                  10 * self.current_total)
        
        if min_replenishment >= max_replenishment:
            return np.zeros(self.n_products, dtype=int), {"status": "invalid_range"}
        
        # 定义目标函数：补货后的比例偏差
        def objective_function(replenishment_total):
            if replenishment_total < min_replenishment:
                return float('inf')
            try:
                replenishment, _ = self.optimize_fixed_replenishment_total_lp(int(replenishment_total))
                return self._calculate_final_deviation(replenishment)
            except:
                return float('inf')
        
        # 使用黄金分割搜索找到最优补货总量
        from scipy.optimize import minimize_scalar
        
        result = minimize_scalar(objective_function, 
                               bounds=(min_replenishment, max_replenishment),
                               method='bounded')
        
        optimal_replenishment_total = int(result.x)
        optimal_replenishment, info = self.optimize_fixed_replenishment_total_lp(optimal_replenishment_total)
        
        info.update({
            "optimization_method": "adaptive_lp",
            "optimal_replenishment_total": optimal_replenishment_total,
            "search_result": result
        })
        
        return optimal_replenishment, info
    
    def _fallback_heuristic_method(self, replenishment_total: int) -> Tuple[np.ndarray, Dict]:
        """
        线性规划失败时的启发式回退方法
        """
        final_total = self.current_total + replenishment_total
        target_final_quantities = final_total * self.target_ratios
        ideal_replenishment = np.maximum(0, target_final_quantities - self.current_stocks)
        feasible_replenishment = np.minimum(ideal_replenishment, self.warehouse_stocks)
        
        # 调整以满足总量约束
        feasible_replenishment = self._adjust_to_total_constraint(feasible_replenishment, replenishment_total)
        
        info = {
            "status": "fallback_heuristic",
            "method": "heuristic_fallback",
            "final_total": final_total,
            "final_deviation": self._calculate_final_deviation(feasible_replenishment)
        }
        
        return feasible_replenishment.astype(int), info
    
    def _adjust_to_total_constraint(self, replenishment: np.ndarray, target_total: int) -> np.ndarray:
        """
        调整补货数量以满足总量约束
        """
        replenishment = replenishment.copy().astype(float)
        current_total = np.sum(replenishment)
        difference = target_total - current_total
        
        if abs(difference) < 0.5:
            return replenishment.astype(int)
        
        if difference > 0:
            # 需要增加补货量
            for _ in range(int(difference)):
                # 找到可以增加且偏差最大的商品
                available_mask = replenishment < self.warehouse_stocks
                if not np.any(available_mask):
                    break
                
                final_quantities = self.current_stocks + replenishment + 1
                final_total = np.sum(final_quantities)
                potential_ratios = final_quantities / final_total
                deviations = self.target_ratios - potential_ratios
                
                priority_scores = np.where(available_mask, deviations, -np.inf)
                selected_idx = np.argmax(priority_scores)
                replenishment[selected_idx] += 1
        
        else:
            # 需要减少补货量
            for _ in range(int(-difference)):
                reducible_mask = replenishment > 0
                if not np.any(reducible_mask):
                    break
                
                # 选择减少后偏差增加最小的商品
                best_idx = -1
                best_deviation_increase = float('inf')
                
                for i in range(self.n_products):
                    if not reducible_mask[i]:
                        continue
                    
                    test_replenishment = replenishment.copy()
                    test_replenishment[i] -= 1
                    
                    current_deviation = self._calculate_final_deviation(replenishment)
                    test_deviation = self._calculate_final_deviation(test_replenishment)
                    deviation_increase = test_deviation - current_deviation
                    
                    if deviation_increase < best_deviation_increase:
                        best_deviation_increase = deviation_increase
                        best_idx = i
                
                if best_idx >= 0:
                    replenishment[best_idx] -= 1
        
        return replenishment.astype(int)
    
    def _calculate_final_deviation(self, replenishment: np.ndarray) -> float:
        """
        计算补货后的比例偏差（欧几里得距离）
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
                "final_deviation": 0.0,
                "improvement": 0.0
            }
        
        current_ratios = self.current_stocks / self.current_total if self.current_total > 0 else np.zeros(self.n_products)
        final_ratios = final_quantities / final_total
        
        current_deviation = np.sqrt(np.sum((current_ratios - self.target_ratios) ** 2))
        final_deviation = np.sqrt(np.sum((final_ratios - self.target_ratios) ** 2))
        improvement = current_deviation - final_deviation
        
        return {
            "current_total": self.current_total,
            "replenishment_total": replenishment_total,
            "final_total": final_total,
            "current_ratios": current_ratios,
            "final_ratios": final_ratios,
            "target_ratios": self.target_ratios,
            "current_total_deviation": current_deviation,
            "final_total_deviation": final_deviation,
            "improvement": improvement
        }


def print_lp_replenishment_result(optimizer: LinearProgrammingReplenishmentOptimizer, 
                                replenishment: np.ndarray, 
                                info: Dict):
    """
    打印线性规划补货结果
    """
    evaluation = optimizer.evaluate_replenishment_plan(replenishment)
    
    print("=== 线性规划补货方案 ===")
    print(f"求解方法: {info.get('method', 'unknown')}")
    print(f"当前总库存: {evaluation['current_total']}")
    print(f"补货总量: {evaluation['replenishment_total']}")
    print(f"补货后总量: {evaluation['final_total']}")
    print(f"当前总偏差: {evaluation['current_total_deviation']:.4f}")
    print(f"补货后总偏差: {evaluation['final_total_deviation']:.4f}")
    print(f"改善程度: {evaluation['improvement']:.4f}")
    
    if 'lp_objective' in info and info['lp_objective'] is not None:
        print(f"线性规划目标值: {info['lp_objective']:.4f}")
    
    print()
    
    print("商品详情:")
    print(f"{'商品':<8} {'仓库库存':<8} {'当前库存':<8} {'补货量':<8} {'补货后':<8} "
          f"{'期望比例':<8} {'当前比例':<8} {'补货后比例':<8}")
    print("-" * 80)
    
    for i, product in enumerate(optimizer.products):
        current_ratio = evaluation['current_ratios'][i]
        final_ratio = evaluation['final_ratios'][i]
        target_ratio = evaluation['target_ratios'][i]
        final_quantity = optimizer.current_stocks[i] + replenishment[i]
        
        print(f"{product:<8} {optimizer.warehouse_stocks[i]:<8} {optimizer.current_stocks[i]:<8} "
              f"{replenishment[i]:<8} {final_quantity:<8} "
              f"{target_ratio:<8.3f} {current_ratio:<8.3f} {final_ratio:<8.3f}")


if __name__ == "__main__":
    # 使用示例
    products = ['a', 'b', 'c', 'd', 'e', 'f']
    warehouse_stocks = [100, 80, 120, 60, 90, 110]  # 仓库库存
    current_stocks = [5, 2, 8, 0, 3, 7]  # 点位当前库存
    target_ratios = [0.2, 0.15, 0.25, 0.1, 0.15, 0.15]  # 期望比例
    
    # 创建线性规划补货优化器
    lp_optimizer = LinearProgrammingReplenishmentOptimizer(products, warehouse_stocks, current_stocks, target_ratios)
    
    print("=== 线性规划方法：固定补货总量 ===")
    lp_replenishment1, lp_info1 = lp_optimizer.optimize_fixed_replenishment_total_lp(50)
    print_lp_replenishment_result(lp_optimizer, lp_replenishment1, lp_info1)
    
    print("\n=== 线性规划方法：自适应补货 ===")
    lp_replenishment2, lp_info2 = lp_optimizer.optimize_adaptive_replenishment_lp(min_replenishment=30, max_replenishment=100)
    print_lp_replenishment_result(lp_optimizer, lp_replenishment2, lp_info2)
