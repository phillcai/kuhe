"""
解质量分析模块

实现第二层解的质量分析功能：
- 最优解发现能力分析
- 解空间质量分布分析
- 路径特征分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import logging
from .utils import DataProcessor

logger = logging.getLogger(__name__)


class QualityAnalyzer:
    """解质量分析器"""
    
    def __init__(self, df: pd.DataFrame, score_column: str = 'total_score'):
        """
        初始化解质量分析器
        
        Args:
            df: 包含路径数据和评分的DataFrame
            score_column: 评分列名
        """
        self.df = DataProcessor.clean_and_validate_data(df)
        self.df = DataProcessor.extract_path_features(self.df)
        self.score_column = score_column
        
        # 验证评分列是否存在
        if score_column not in self.df.columns:
            logger.warning(f"评分列 '{score_column}' 不存在，将使用现有评价系统计算评分")
            self._calculate_scores()
        
        logger.info(f"解质量分析器初始化完成，使用评分列: {self.score_column}")
    
    def _calculate_scores(self):
        """计算路径评分（如果不存在评分列）"""
        # 简单的评分计算逻辑，可以根据需要调整
        from .multi_req_evaluation import MultiReqPathEvaluator
        
        evaluator = MultiReqPathEvaluator()
        self.df = evaluator.evaluate_paths(self.df)
        self.score_column = 'total_score'
    
    def analyze_optimal_discovery_capability(self) -> Dict[str, Any]:
        """
        分析最优解发现能力
        
        Returns:
            最优解发现能力分析结果
        """
        logger.info("开始最优解发现能力分析...")
        
        results = {
            'top_k_analysis': {},
            'optimal_vs_average': {},
            'request_optimal_comparison': {},
            'discovery_effectiveness': {}
        }
        
        # Top-K路径质量分布分析
        results['top_k_analysis'] = self._analyze_top_k_paths()
        
        # 最优解与平均解差距分析
        results['optimal_vs_average'] = self._analyze_optimal_vs_average()
        
        # 各请求最优解质量对比
        results['request_optimal_comparison'] = self._compare_request_optimal_solutions()
        
        # 发现有效性评估
        results['discovery_effectiveness'] = self._evaluate_discovery_effectiveness()
        
        logger.info("最优解发现能力分析完成")
        return results
    
    def _analyze_top_k_paths(self, percentiles: List[float] = None) -> Dict[str, Any]:
        """
        分析Top-K路径质量分布
        
        Args:
            percentiles: 要分析的百分位数列表
            
        Returns:
            Top-K分析结果
        """
        if percentiles is None:
            percentiles = [1, 5, 10, 25]
        
        top_k_results = {}
        
        # 按请求分组分析
        for req_id, group in self.df.groupby('req_id'):
            # 按评分排序
            sorted_group = group.sort_values(self.score_column, ascending=False)
            total_paths = len(sorted_group)
            
            req_top_k = {}
            for p in percentiles:
                k = max(1, int(total_paths * p / 100))
                top_k_paths = sorted_group.head(k)
                
                req_top_k[f'top_{p}%'] = {
                    'path_count': k,
                    'avg_score': top_k_paths[self.score_column].mean(),
                    'avg_loss': top_k_paths['path_sale_loss'].mean(),
                    'avg_time': top_k_paths['path_duration'].mean(),
                    'score_std': top_k_paths[self.score_column].std(),
                    'score_range': (top_k_paths[self.score_column].min(), 
                                   top_k_paths[self.score_column].max()),
                    'best_path': {
                        'path': top_k_paths.iloc[0]['path'],
                        'score': top_k_paths.iloc[0][self.score_column],
                        'loss': top_k_paths.iloc[0]['path_sale_loss'],
                        'time': top_k_paths.iloc[0]['path_duration']
                    }
                }
            
            top_k_results[req_id] = req_top_k
        
        # 全局Top-K统计
        global_top_k = {}
        for p in percentiles:
            all_scores = []
            all_losses = []
            all_times = []
            
            for req_data in top_k_results.values():
                if f'top_{p}%' in req_data:
                    all_scores.append(req_data[f'top_{p}%']['avg_score'])
                    all_losses.append(req_data[f'top_{p}%']['avg_loss'])
                    all_times.append(req_data[f'top_{p}%']['avg_time'])
            
            global_top_k[f'top_{p}%'] = {
                'avg_score_across_requests': np.mean(all_scores) if all_scores else 0,
                'score_consistency': np.std(all_scores) / np.mean(all_scores) if all_scores and np.mean(all_scores) > 0 else 0,
                'avg_loss_across_requests': np.mean(all_losses) if all_losses else 0,
                'avg_time_across_requests': np.mean(all_times) if all_times else 0
            }
        
        return {
            'by_request': top_k_results,
            'global_summary': global_top_k
        }
    
    def _analyze_optimal_vs_average(self) -> Dict[str, Any]:
        """
        分析最优解与平均解的差距
        
        Returns:
            最优解vs平均解分析结果
        """
        optimal_vs_avg = {}
        
        # 按请求分析
        for req_id, group in self.df.groupby('req_id'):
            best_path = group.loc[group[self.score_column].idxmax()]
            avg_score = group[self.score_column].mean()
            avg_loss = group['path_sale_loss'].mean()
            avg_time = group['path_duration'].mean()
            
            # 计算提升幅度
            score_improvement = (best_path[self.score_column] - avg_score) / avg_score if avg_score > 0 else 0
            loss_improvement = (avg_loss - best_path['path_sale_loss']) / avg_loss if avg_loss > 0 else 0
            time_improvement = (avg_time - best_path['path_duration']) / avg_time if avg_time > 0 else 0
            
            optimal_vs_avg[req_id] = {
                'best_score': best_path[self.score_column],
                'avg_score': avg_score,
                'score_improvement_ratio': score_improvement,
                'best_loss': best_path['path_sale_loss'],
                'avg_loss': avg_loss,
                'loss_improvement_ratio': loss_improvement,
                'best_time': best_path['path_duration'],
                'avg_time': avg_time,
                'time_improvement_ratio': time_improvement,
                'algorithm_value_score': (score_improvement + loss_improvement + time_improvement) / 3
            }
        
        # 全局统计
        all_score_improvements = [data['score_improvement_ratio'] for data in optimal_vs_avg.values()]
        all_loss_improvements = [data['loss_improvement_ratio'] for data in optimal_vs_avg.values()]
        all_time_improvements = [data['time_improvement_ratio'] for data in optimal_vs_avg.values()]
        all_value_scores = [data['algorithm_value_score'] for data in optimal_vs_avg.values()]
        
        global_summary = {
            'avg_score_improvement': np.mean(all_score_improvements),
            'avg_loss_improvement': np.mean(all_loss_improvements),
            'avg_time_improvement': np.mean(all_time_improvements),
            'avg_algorithm_value': np.mean(all_value_scores),
            'improvement_consistency': {
                'score_cv': np.std(all_score_improvements) / np.mean(all_score_improvements) if np.mean(all_score_improvements) > 0 else 0,
                'loss_cv': np.std(all_loss_improvements) / np.mean(all_loss_improvements) if np.mean(all_loss_improvements) > 0 else 0,
                'time_cv': np.std(all_time_improvements) / np.mean(all_time_improvements) if np.mean(all_time_improvements) > 0 else 0
            }
        }
        
        return {
            'by_request': optimal_vs_avg,
            'global_summary': global_summary
        }
    
    def _compare_request_optimal_solutions(self) -> Dict[str, Any]:
        """
        比较各请求的最优解质量
        
        Returns:
            请求最优解比较结果
        """
        optimal_solutions = {}
        
        # 收集各请求的最优解
        for req_id, group in self.df.groupby('req_id'):
            best_path = group.loc[group[self.score_column].idxmax()]
            
            optimal_solutions[req_id] = {
                'path': best_path['path'],
                'score': best_path[self.score_column],
                'loss': best_path['path_sale_loss'],
                'time': best_path['path_duration'],
                'path_length': best_path['path_length'],
                'rank_in_request': 1,  # 最优解在该请求中的排名
                'score_percentile': 100  # 最优解在该请求中的百分位
            }
        
        # 全局排序
        all_optimal = list(optimal_solutions.values())
        all_optimal.sort(key=lambda x: x['score'], reverse=True)
        
        # 添加全局排名
        for i, solution in enumerate(all_optimal):
            # 找到对应的req_id
            for req_id, data in optimal_solutions.items():
                if data['path'] == solution['path']:
                    optimal_solutions[req_id]['global_rank'] = i + 1
                    optimal_solutions[req_id]['global_percentile'] = (len(all_optimal) - i) / len(all_optimal) * 100
                    break
        
        # 质量一致性分析
        scores = [sol['score'] for sol in all_optimal]
        losses = [sol['loss'] for sol in all_optimal]
        times = [sol['time'] for sol in all_optimal]
        lengths = [sol['path_length'] for sol in all_optimal]
        
        consistency_analysis = {
            'score_stats': DataProcessor.get_descriptive_statistics(pd.Series(scores)),
            'loss_stats': DataProcessor.get_descriptive_statistics(pd.Series(losses)),
            'time_stats': DataProcessor.get_descriptive_statistics(pd.Series(times)),
            'length_stats': DataProcessor.get_descriptive_statistics(pd.Series(lengths)),
            'quality_tiers': self._classify_solution_quality_tiers(all_optimal)
        }
        
        return {
            'optimal_solutions': optimal_solutions,
            'consistency_analysis': consistency_analysis,
            'ranking_summary': {
                'best_overall': all_optimal[0],
                'worst_optimal': all_optimal[-1],
                'median_optimal': all_optimal[len(all_optimal)//2]
            }
        }
    
    def _classify_solution_quality_tiers(self, solutions: List[Dict]) -> Dict[str, Any]:
        """
        将最优解分类为不同质量层次
        
        Args:
            solutions: 最优解列表
            
        Returns:
            质量层次分类结果
        """
        scores = [sol['score'] for sol in solutions]
        
        # 使用四分位数划分质量层次
        q25 = np.percentile(scores, 25)
        q50 = np.percentile(scores, 50)
        q75 = np.percentile(scores, 75)
        
        tiers = {
            'excellent': [],  # 前25%
            'good': [],       # 25%-50%
            'fair': [],       # 50%-75%
            'poor': []        # 后25%
        }
        
        for sol in solutions:
            score = sol['score']
            if score >= q75:
                tiers['excellent'].append(sol)
            elif score >= q50:
                tiers['good'].append(sol)
            elif score >= q25:
                tiers['fair'].append(sol)
            else:
                tiers['poor'].append(sol)
        
        # 统计各层次特征
        tier_stats = {}
        for tier_name, tier_solutions in tiers.items():
            if tier_solutions:
                tier_scores = [sol['score'] for sol in tier_solutions]
                tier_losses = [sol['loss'] for sol in tier_solutions]
                tier_times = [sol['time'] for sol in tier_solutions]
                
                tier_stats[tier_name] = {
                    'count': len(tier_solutions),
                    'avg_score': np.mean(tier_scores),
                    'avg_loss': np.mean(tier_losses),
                    'avg_time': np.mean(tier_times),
                    'score_range': (min(tier_scores), max(tier_scores))
                }
        
        return {
            'tiers': tiers,
            'tier_statistics': tier_stats,
            'thresholds': {'q25': q25, 'q50': q50, 'q75': q75}
        }
    
    def _evaluate_discovery_effectiveness(self) -> Dict[str, Any]:
        """
        评估最优解发现的有效性
        
        Returns:
            发现有效性评估结果
        """
        effectiveness_metrics = {}
        
        # 按请求评估
        for req_id, group in self.df.groupby('req_id'):
            sorted_group = group.sort_values(self.score_column, ascending=False)
            total_paths = len(sorted_group)
            
            # 计算收敛指标
            scores = sorted_group[self.score_column].values
            best_score = scores[0]
            
            # 计算达到90%最优解质量需要多少路径
            target_score = best_score * 0.9
            paths_to_90_percent = len(scores[scores >= target_score])
            
            # 计算评分的收敛速度
            cummax_scores = np.maximum.accumulate(scores)
            convergence_rate = np.mean(np.diff(cummax_scores)[:10]) if len(cummax_scores) > 10 else 0
            
            effectiveness_metrics[req_id] = {
                'total_paths': total_paths,
                'best_score': best_score,
                'paths_to_90_percent': paths_to_90_percent,
                'efficiency_ratio': paths_to_90_percent / total_paths,
                'convergence_rate': convergence_rate,
                'score_improvement_curve': cummax_scores[:min(100, len(cummax_scores))].tolist(),
                'discovery_quality': self._calculate_discovery_quality(scores)
            }
        
        # 全局有效性评估
        all_efficiency_ratios = [metrics['efficiency_ratio'] for metrics in effectiveness_metrics.values()]
        all_convergence_rates = [metrics['convergence_rate'] for metrics in effectiveness_metrics.values()]
        
        global_effectiveness = {
            'avg_efficiency_ratio': np.mean(all_efficiency_ratios),
            'avg_convergence_rate': np.mean(all_convergence_rates),
            'consistency_score': 1 - np.std(all_efficiency_ratios),  # 一致性评分
            'overall_effectiveness_grade': self._grade_overall_effectiveness(
                np.mean(all_efficiency_ratios), 
                np.mean(all_convergence_rates)
            )
        }
        
        return {
            'by_request': effectiveness_metrics,
            'global_effectiveness': global_effectiveness
        }
    
    def _calculate_discovery_quality(self, scores: np.ndarray) -> float:
        """
        计算发现质量评分
        
        Args:
            scores: 按质量排序的评分数组
            
        Returns:
            发现质量评分 (0-1)
        """
        if len(scores) == 0:
            return 0
        
        # 基于评分分布的质量评估
        best_score = scores[0]
        worst_score = scores[-1]
        
        if best_score == worst_score:
            return 1.0  # 所有解质量相同
        
        # 计算前10%解的质量集中度
        top_10_percent = max(1, len(scores) // 10)
        top_scores = scores[:top_10_percent]
        
        # 质量集中度：前10%解的标准差相对于全部解的标准差
        top_std = np.std(top_scores)
        all_std = np.std(scores)
        concentration = 1 - (top_std / all_std) if all_std > 0 else 1
        
        # 质量区分度：最优解相对于平均解的提升
        avg_score = np.mean(scores)
        discrimination = (best_score - avg_score) / avg_score if avg_score > 0 else 0
        
        # 综合质量评分
        quality_score = (concentration * 0.6 + min(1, discrimination) * 0.4)
        return max(0, min(1, quality_score))
    
    def _grade_overall_effectiveness(self, efficiency_ratio: float, convergence_rate: float) -> str:
        """
        评估整体有效性等级
        
        Args:
            efficiency_ratio: 平均效率比率
            convergence_rate: 平均收敛速度
            
        Returns:
            有效性等级
        """
        # 综合评分
        score = efficiency_ratio * 0.7 + min(1, convergence_rate * 10) * 0.3
        
        if score >= 0.8:
            return 'Excellent'
        elif score >= 0.6:
            return 'Good'
        elif score >= 0.4:
            return 'Fair'
        else:
            return 'Poor'
    
    def analyze_solution_quality_distribution(self) -> Dict[str, Any]:
        """
        分析解空间质量分布
        
        Returns:
            解空间质量分布分析结果
        """
        logger.info("开始解空间质量分布分析...")
        
        results = {
            'convergence_analysis': {},
            'distribution_characteristics': {},
            'quality_gradient_analysis': {}
        }
        
        # 收敛曲线分析
        results['convergence_analysis'] = self._analyze_convergence_curves()
        
        # 分布特征分析
        results['distribution_characteristics'] = self._analyze_distribution_characteristics()
        
        # 质量梯度分析
        results['quality_gradient_analysis'] = self._analyze_quality_gradients()
        
        logger.info("解空间质量分布分析完成")
        return results
    
    def _analyze_convergence_curves(self) -> Dict[str, Any]:
        """
        分析路径质量收敛曲线
        
        Returns:
            收敛曲线分析结果
        """
        convergence_results = {}
        
        # 按请求分析收敛特征
        for req_id, group in self.df.groupby('req_id'):
            sorted_scores = group[self.score_column].sort_values(ascending=False).values
            
            # 计算累积最大值（收敛曲线）
            cummax_scores = np.maximum.accumulate(sorted_scores)
            
            # 分析收敛特征
            convergence_results[req_id] = {
                'convergence_curve': cummax_scores.tolist(),
                'final_best_score': cummax_scores[-1],
                'convergence_speed': self._calculate_convergence_speed(cummax_scores),
                'plateau_analysis': self._analyze_convergence_plateau(cummax_scores),
                'improvement_points': self._find_improvement_points(cummax_scores)
            }
        
        # 全局收敛特征
        all_speeds = [result['convergence_speed'] for result in convergence_results.values()]
        all_plateaus = [result['plateau_analysis']['plateau_length'] for result in convergence_results.values()]
        
        global_convergence = {
            'avg_convergence_speed': np.mean(all_speeds),
            'avg_plateau_length': np.mean(all_plateaus),
            'speed_consistency': np.std(all_speeds) / np.mean(all_speeds) if np.mean(all_speeds) > 0 else 0,
            'convergence_pattern_classification': self._classify_convergence_patterns(convergence_results)
        }
        
        return {
            'by_request': convergence_results,
            'global_analysis': global_convergence
        }
    
    def _calculate_convergence_speed(self, cummax_scores: np.ndarray) -> float:
        """
        计算收敛速度
        
        Args:
            cummax_scores: 累积最大评分数组
            
        Returns:
            收敛速度指标
        """
        if len(cummax_scores) < 2:
            return 0
        
        # 计算前半部分的改进幅度
        half_point = len(cummax_scores) // 2
        if half_point == 0:
            return 0
        
        initial_score = cummax_scores[0]
        mid_score = cummax_scores[half_point]
        final_score = cummax_scores[-1]
        
        if final_score == initial_score:
            return 0
        
        # 收敛速度 = 前半段改进幅度 / 总改进幅度
        first_half_improvement = mid_score - initial_score
        total_improvement = final_score - initial_score
        
        speed = first_half_improvement / total_improvement if total_improvement > 0 else 0
        return max(0, min(1, speed))
    
    def _analyze_convergence_plateau(self, cummax_scores: np.ndarray) -> Dict[str, Any]:
        """
        分析收敛平台期
        
        Args:
            cummax_scores: 累积最大评分数组
            
        Returns:
            平台期分析结果
        """
        if len(cummax_scores) < 2:
            return {'plateau_length': 0, 'plateau_start': 0, 'plateau_score': 0}
        
        # 找到最后一次显著改进的位置
        final_score = cummax_scores[-1]
        threshold = final_score * 0.001  # 0.1%的改进阈值
        
        plateau_start = len(cummax_scores) - 1
        for i in range(len(cummax_scores) - 2, -1, -1):
            if final_score - cummax_scores[i] > threshold:
                plateau_start = i + 1
                break
        
        plateau_length = len(cummax_scores) - plateau_start
        plateau_ratio = plateau_length / len(cummax_scores)
        
        return {
            'plateau_length': plateau_length,
            'plateau_ratio': plateau_ratio,
            'plateau_start': plateau_start,
            'plateau_score': final_score
        }
    
    def _find_improvement_points(self, cummax_scores: np.ndarray) -> List[Dict[str, Any]]:
        """
        找到显著改进点
        
        Args:
            cummax_scores: 累积最大评分数组
            
        Returns:
            改进点列表
        """
        if len(cummax_scores) < 2:
            return []
        
        improvement_points = []
        prev_score = cummax_scores[0]
        
        for i, score in enumerate(cummax_scores[1:], 1):
            if score > prev_score:
                improvement = score - prev_score
                improvement_ratio = improvement / prev_score if prev_score > 0 else 0
                
                improvement_points.append({
                    'position': i,
                    'score': score,
                    'improvement': improvement,
                    'improvement_ratio': improvement_ratio
                })
                prev_score = score
        
        return improvement_points
    
    def _classify_convergence_patterns(self, convergence_results: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        分类收敛模式
        
        Args:
            convergence_results: 收敛分析结果
            
        Returns:
            收敛模式分类
        """
        patterns = {
            'fast_convergence': [],    # 快速收敛
            'gradual_convergence': [], # 渐进收敛
            'slow_convergence': [],    # 缓慢收敛
            'plateau_dominant': []     # 平台期主导
        }
        
        for req_id, result in convergence_results.items():
            speed = result.get('convergence_speed', 0)
            plateau_analysis = result.get('plateau_analysis', {})
            plateau_ratio = plateau_analysis.get('plateau_ratio', 0)
            
            if speed > 0.7:
                patterns['fast_convergence'].append(req_id)
            elif speed > 0.3:
                patterns['gradual_convergence'].append(req_id)
            elif plateau_ratio > 0.6:
                patterns['plateau_dominant'].append(req_id)
            else:
                patterns['slow_convergence'].append(req_id)
        
        return patterns
    
    def _analyze_distribution_characteristics(self) -> Dict[str, Any]:
        """
        分析解的分布特征
        
        Returns:
            分布特征分析结果
        """
        distribution_analysis = {}
        
        # 按请求分析分布特征
        for req_id, group in self.df.groupby('req_id'):
            scores = group[self.score_column]
            
            distribution_analysis[req_id] = {
                'basic_stats': DataProcessor.get_descriptive_statistics(scores),
                'distribution_shape': self._analyze_distribution_shape(scores),
                'quality_concentration': self._analyze_quality_concentration(scores),
                'outlier_analysis': self._analyze_score_outliers(scores)
            }
        
        # 全局分布特征
        all_scores = self.df[self.score_column]
        global_distribution = {
            'overall_stats': DataProcessor.get_descriptive_statistics(all_scores),
            'cross_request_variance': self._analyze_cross_request_variance(),
            'distribution_consistency': self._analyze_distribution_consistency(distribution_analysis)
        }
        
        return {
            'by_request': distribution_analysis,
            'global_distribution': global_distribution
        }
    
    def _analyze_distribution_shape(self, scores: pd.Series) -> Dict[str, Any]:
        """
        分析分布形状特征
        
        Args:
            scores: 评分序列
            
        Returns:
            分布形状分析结果
        """
        shape_analysis = {
            'is_normal': False,
            'distribution_type': 'unknown',
            'modality': 'unknown'
        }
        
        try:
            from scipy import stats
            
            # 正态性检验
            _, p_value = stats.normaltest(scores.dropna())
            shape_analysis['is_normal'] = p_value > 0.05
            shape_analysis['normality_p_value'] = p_value
            
            # 分布类型判断
            skewness = stats.skew(scores.dropna())
            kurtosis = stats.kurtosis(scores.dropna())
            
            if abs(skewness) < 0.5:
                shape_analysis['distribution_type'] = 'symmetric'
            elif skewness > 0.5:
                shape_analysis['distribution_type'] = 'right_skewed'
            else:
                shape_analysis['distribution_type'] = 'left_skewed'
            
            # 峰度分析
            if kurtosis > 1:
                shape_analysis['kurtosis_type'] = 'leptokurtic'  # 尖峰
            elif kurtosis < -1:
                shape_analysis['kurtosis_type'] = 'platykurtic'  # 平峰
            else:
                shape_analysis['kurtosis_type'] = 'mesokurtic'   # 正常峰
            
            shape_analysis['skewness'] = skewness
            shape_analysis['kurtosis'] = kurtosis
            
        except ImportError:
            logger.warning("scipy未安装，跳过分布形状的高级分析")
        
        return shape_analysis
    
    def _analyze_quality_concentration(self, scores: pd.Series) -> Dict[str, Any]:
        """
        分析质量集中度
        
        Args:
            scores: 评分序列
            
        Returns:
            质量集中度分析结果
        """
        sorted_scores = scores.sort_values(ascending=False)
        total_count = len(sorted_scores)
        
        # 计算不同比例的质量集中度
        concentration_ratios = [0.1, 0.2, 0.3, 0.5]
        concentration_analysis = {}
        
        for ratio in concentration_ratios:
            top_count = max(1, int(total_count * ratio))
            top_scores = sorted_scores.head(top_count)
            
            concentration_analysis[f'top_{int(ratio*100)}%'] = {
                'count': top_count,
                'score_range': (top_scores.min(), top_scores.max()),
                'avg_score': top_scores.mean(),
                'score_std': top_scores.std(),
                'concentration_index': 1 - (top_scores.std() / sorted_scores.std()) if sorted_scores.std() > 0 else 1
            }
        
        return concentration_analysis
    
    def _analyze_score_outliers(self, scores: pd.Series) -> Dict[str, Any]:
        """
        分析评分异常值
        
        Args:
            scores: 评分序列
            
        Returns:
            异常值分析结果
        """
        q1 = scores.quantile(0.25)
        q3 = scores.quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = scores[(scores < lower_bound) | (scores > upper_bound)]
        
        return {
            'outlier_count': len(outliers),
            'outlier_ratio': len(outliers) / len(scores),
            'lower_outliers': len(scores[scores < lower_bound]),
            'upper_outliers': len(scores[scores > upper_bound]),
            'outlier_bounds': (lower_bound, upper_bound),
            'extreme_values': {
                'min': scores.min(),
                'max': scores.max(),
                'most_extreme_low': outliers.min() if len(outliers) > 0 else None,
                'most_extreme_high': outliers.max() if len(outliers) > 0 else None
            }
        }
    
    def _analyze_cross_request_variance(self) -> Dict[str, Any]:
        """
        分析跨请求方差
        
        Returns:
            跨请求方差分析结果
        """
        # 计算各请求的平均评分
        request_means = self.df.groupby('req_id')[self.score_column].mean()
        request_stds = self.df.groupby('req_id')[self.score_column].std()
        
        return {
            'request_mean_stats': DataProcessor.get_descriptive_statistics(request_means),
            'request_std_stats': DataProcessor.get_descriptive_statistics(request_stds.dropna()),
            'between_request_variance': request_means.var(),
            'within_request_avg_variance': request_stds.mean(),
            'variance_ratio': request_means.var() / request_stds.mean() if request_stds.mean() > 0 else 0,
            'consistency_score': 1 / (1 + request_means.std() / request_means.mean()) if request_means.mean() > 0 else 0
        }
    
    def _analyze_distribution_consistency(self, distribution_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析分布一致性
        
        Args:
            distribution_analysis: 各请求的分布分析结果
            
        Returns:
            分布一致性分析结果
        """
        # 收集各请求的分布特征
        skewness_values = []
        kurtosis_values = []
        cv_values = []
        
        for req_data in distribution_analysis.values():
            basic_stats = req_data['basic_stats']
            shape_data = req_data['distribution_shape']
            
            cv_values.append(basic_stats['cv'])
            if 'skewness' in shape_data:
                skewness_values.append(shape_data['skewness'])
            if 'kurtosis' in shape_data:
                kurtosis_values.append(shape_data['kurtosis'])
        
        consistency_metrics = {
            'cv_consistency': np.std(cv_values) if cv_values else 0,
            'avg_cv': np.mean(cv_values) if cv_values else 0
        }
        
        if skewness_values:
            consistency_metrics['skewness_consistency'] = np.std(skewness_values)
            consistency_metrics['avg_skewness'] = np.mean(skewness_values)
        
        if kurtosis_values:
            consistency_metrics['kurtosis_consistency'] = np.std(kurtosis_values)
            consistency_metrics['avg_kurtosis'] = np.mean(kurtosis_values)
        
        # 综合一致性评分
        consistency_score = 1 / (1 + consistency_metrics['cv_consistency'])
        consistency_metrics['overall_consistency_score'] = consistency_score
        
        return consistency_metrics
    
    def _analyze_quality_gradients(self) -> Dict[str, Any]:
        """
        分析质量梯度
        
        Returns:
            质量梯度分析结果
        """
        gradient_analysis = {}
        
        # 按请求分析质量梯度
        for req_id, group in self.df.groupby('req_id'):
            sorted_scores = group[self.score_column].sort_values(ascending=False).values
            
            # 计算质量梯度（相邻解之间的质量差异）
            gradients = np.diff(sorted_scores)
            
            # 分析不同区间的梯度特征
            total_len = len(gradients)
            if total_len > 10:
                top_10_percent = gradients[:max(1, total_len//10)]
                middle_gradients = gradients[total_len//10:total_len*9//10] if total_len > 20 else gradients
                bottom_10_percent = gradients[-max(1, total_len//10):] if total_len > 10 else gradients[-1:]
                
                gradient_analysis[req_id] = {
                    'overall_gradient_stats': {
                        'mean': np.mean(gradients),
                        'std': np.std(gradients),
                        'min': np.min(gradients),
                        'max': np.max(gradients)
                    },
                    'top_10_percent_gradient': {
                        'mean': np.mean(top_10_percent),
                        'std': np.std(top_10_percent)
                    },
                    'middle_gradient': {
                        'mean': np.mean(middle_gradients),
                        'std': np.std(middle_gradients)
                    },
                    'bottom_10_percent_gradient': {
                        'mean': np.mean(bottom_10_percent),
                        'std': np.std(bottom_10_percent)
                    },
                    'gradient_uniformity': np.std(gradients) / abs(np.mean(gradients)) if np.mean(gradients) != 0 else 0
                }
        
        return gradient_analysis
    
    def analyze_path_characteristics(self) -> Dict[str, Any]:
        """
        分析路径特征
        
        Returns:
            路径特征分析结果
        """
        logger.info("开始路径特征分析...")
        
        results = {
            'length_vs_quality': {},
            'high_quality_patterns': {},
            'low_quality_patterns': {}
        }
        
        # 路径长度vs质量关系分析
        results['length_vs_quality'] = self._analyze_length_quality_relationship()
        
        # 高质量路径模式识别
        results['high_quality_patterns'] = self._identify_high_quality_patterns()
        
        # 低质量路径问题模式识别
        results['low_quality_patterns'] = self._identify_low_quality_patterns()
        
        logger.info("路径特征分析完成")
        return results
    
    def _analyze_length_quality_relationship(self) -> Dict[str, Any]:
        """
        分析路径长度与质量的关系
        
        Returns:
            长度-质量关系分析结果
        """
        length_quality_analysis = {}
        
        # 按路径长度分组分析
        length_groups = self.df.groupby('path_length')
        
        for length, group in length_groups:
            length_quality_analysis[length] = {
                'count': len(group),
                'avg_score': group[self.score_column].mean(),
                'score_std': group[self.score_column].std(),
                'avg_loss': group['path_sale_loss'].mean(),
                'avg_time': group['path_duration'].mean(),
                'best_score': group[self.score_column].max(),
                'worst_score': group[self.score_column].min(),
                'score_range': group[self.score_column].max() - group[self.score_column].min()
            }
        
        # 相关性分析
        correlation_analysis = {}
        try:
            score_length_corr = self.df[self.score_column].corr(self.df['path_length'])
            loss_length_corr = self.df['path_sale_loss'].corr(self.df['path_length'])
            time_length_corr = self.df['path_duration'].corr(self.df['path_length'])
            
            correlation_analysis = {
                'score_length_correlation': score_length_corr,
                'loss_length_correlation': loss_length_corr,
                'time_length_correlation': time_length_corr,
                'correlation_strength': {
                    'score': 'strong' if abs(score_length_corr) > 0.7 else 'moderate' if abs(score_length_corr) > 0.3 else 'weak',
                    'loss': 'strong' if abs(loss_length_corr) > 0.7 else 'moderate' if abs(loss_length_corr) > 0.3 else 'weak',
                    'time': 'strong' if abs(time_length_corr) > 0.7 else 'moderate' if abs(time_length_corr) > 0.3 else 'weak'
                }
            }
        except Exception as e:
            logger.warning(f"相关性分析失败: {e}")
            correlation_analysis = {'error': str(e)}
        
        # 最优长度识别
        if length_quality_analysis:
            best_length = max(length_quality_analysis.keys(), 
                            key=lambda x: length_quality_analysis[x]['avg_score'])
            worst_length = min(length_quality_analysis.keys(), 
                             key=lambda x: length_quality_analysis[x]['avg_score'])
            
            optimal_length_analysis = {
                'best_avg_length': best_length,
                'worst_avg_length': worst_length,
                'length_recommendation': self._recommend_optimal_length(length_quality_analysis)
            }
        else:
            optimal_length_analysis = {}
        
        return {
            'by_length': length_quality_analysis,
            'correlation_analysis': correlation_analysis,
            'optimal_length_analysis': optimal_length_analysis
        }
    
    def _recommend_optimal_length(self, length_analysis: Dict[int, Dict]) -> Dict[str, Any]:
        """
        推荐最优路径长度
        
        Args:
            length_analysis: 按长度的分析结果
            
        Returns:
            长度推荐结果
        """
        # 计算每个长度的综合评分（考虑质量和数量）
        length_scores = {}
        
        for length, data in length_analysis.items():
            # 综合评分 = 平均质量 * log(数量) （考虑样本量）
            sample_weight = min(1.0, np.log(data['count'] + 1) / np.log(100))  # 样本量权重
            quality_score = data['avg_score']
            stability_score = 1 / (1 + data['score_std']) if data['score_std'] > 0 else 1
            
            comprehensive_score = quality_score * sample_weight * stability_score
            length_scores[length] = comprehensive_score
        
        if not length_scores:
            return {}
        
        recommended_length = max(length_scores.keys(), key=lambda x: length_scores[x])
        
        return {
            'recommended_length': recommended_length,
            'recommendation_score': length_scores[recommended_length],
            'reason': f"长度{recommended_length}在质量、稳定性和样本量方面表现最佳",
            'all_length_scores': length_scores
        }
    
    def _identify_high_quality_patterns(self) -> Dict[str, Any]:
        """
        识别高质量路径的共同模式
        
        Returns:
            高质量路径模式识别结果
        """
        # 定义高质量路径（前20%）
        score_threshold = self.df[self.score_column].quantile(0.8)
        high_quality_paths = self.df[self.df[self.score_column] >= score_threshold]
        
        if len(high_quality_paths) == 0:
            return {'error': '未找到高质量路径'}
        
        patterns = {
            'length_patterns': {},
            'structural_patterns': {},
            'performance_characteristics': {}
        }
        
        # 长度模式分析
        length_dist = high_quality_paths['path_length'].value_counts()
        patterns['length_patterns'] = {
            'most_common_lengths': length_dist.head(5).to_dict(),
            'avg_length': high_quality_paths['path_length'].mean(),
            'length_range': (high_quality_paths['path_length'].min(), 
                           high_quality_paths['path_length'].max())
        }
        
        # 性能特征分析
        patterns['performance_characteristics'] = {
            'avg_score': high_quality_paths[self.score_column].mean(),
            'avg_loss': high_quality_paths['path_sale_loss'].mean(),
            'avg_time': high_quality_paths['path_duration'].mean(),
            'avg_time_per_point': high_quality_paths['time_per_point'].mean(),
            'avg_loss_per_point': high_quality_paths['loss_per_point'].mean(),
            'score_consistency': high_quality_paths[self.score_column].std()
        }
        
        # 结构模式分析（基于路径字符串）
        patterns['structural_patterns'] = self._analyze_path_structures(high_quality_paths['path'])
        
        return patterns
    
    def _identify_low_quality_patterns(self) -> Dict[str, Any]:
        """
        识别低质量路径的问题模式
        
        Returns:
            低质量路径问题模式识别结果
        """
        # 定义低质量路径（后20%）
        score_threshold = self.df[self.score_column].quantile(0.2)
        low_quality_paths = self.df[self.df[self.score_column] <= score_threshold]
        
        if len(low_quality_paths) == 0:
            return {'error': '未找到低质量路径'}
        
        problems = {
            'length_problems': {},
            'structural_problems': {},
            'performance_issues': {}
        }
        
        # 长度问题分析
        length_dist = low_quality_paths['path_length'].value_counts()
        problems['length_problems'] = {
            'most_common_lengths': length_dist.head(5).to_dict(),
            'avg_length': low_quality_paths['path_length'].mean(),
            'length_range': (low_quality_paths['path_length'].min(), 
                           low_quality_paths['path_length'].max())
        }
        
        # 性能问题分析
        problems['performance_issues'] = {
            'avg_score': low_quality_paths[self.score_column].mean(),
            'avg_loss': low_quality_paths['path_sale_loss'].mean(),
            'avg_time': low_quality_paths['path_duration'].mean(),
            'avg_time_per_point': low_quality_paths['time_per_point'].mean(),
            'avg_loss_per_point': low_quality_paths['loss_per_point'].mean(),
            'worst_performers': self._identify_worst_performers(low_quality_paths)
        }
        
        # 结构问题分析
        problems['structural_problems'] = self._analyze_path_structures(low_quality_paths['path'])
        
        return problems
    
    def _analyze_path_structures(self, paths: pd.Series) -> Dict[str, Any]:
        """
        分析路径结构模式
        
        Args:
            paths: 路径字符串序列
            
        Returns:
            路径结构分析结果
        """
        # 提取路径中的点位信息
        all_points = []
        point_frequencies = {}
        
        for path in paths:
            if pd.isna(path):
                continue
            points = str(path).split('_')
            all_points.extend(points)
            
            for point in points:
                point_frequencies[point] = point_frequencies.get(point, 0) + 1
        
        # 分析最常见的点位
        sorted_points = sorted(point_frequencies.items(), key=lambda x: x[1], reverse=True)
        
        # 分析点位组合模式
        pair_frequencies = {}
        for path in paths:
            if pd.isna(path):
                continue
            points = str(path).split('_')
            for i in range(len(points) - 1):
                pair = f"{points[i]}_{points[i+1]}"
                pair_frequencies[pair] = pair_frequencies.get(pair, 0) + 1
        
        sorted_pairs = sorted(pair_frequencies.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'most_frequent_points': sorted_points[:10],
            'most_frequent_pairs': sorted_pairs[:10],
            'unique_points_count': len(point_frequencies),
            'avg_points_per_path': len(all_points) / len(paths) if len(paths) > 0 else 0,
            'point_diversity': len(point_frequencies) / len(all_points) if len(all_points) > 0 else 0
        }
    
    def _identify_worst_performers(self, low_quality_paths: pd.DataFrame) -> Dict[str, Any]:
        """
        识别最差的性能表现
        
        Args:
            low_quality_paths: 低质量路径数据
            
        Returns:
            最差性能识别结果
        """
        worst_performers = {}
        
        # 找到各个维度的最差表现
        worst_score_idx = low_quality_paths[self.score_column].idxmin()
        worst_loss_idx = low_quality_paths['path_sale_loss'].idxmax()
        worst_time_idx = low_quality_paths['path_duration'].idxmax()
        
        worst_performers['worst_score'] = {
            'path': low_quality_paths.loc[worst_score_idx, 'path'],
            'score': low_quality_paths.loc[worst_score_idx, self.score_column],
            'loss': low_quality_paths.loc[worst_score_idx, 'path_sale_loss'],
            'time': low_quality_paths.loc[worst_score_idx, 'path_duration']
        }
        
        worst_performers['highest_loss'] = {
            'path': low_quality_paths.loc[worst_loss_idx, 'path'],
            'score': low_quality_paths.loc[worst_loss_idx, self.score_column],
            'loss': low_quality_paths.loc[worst_loss_idx, 'path_sale_loss'],
            'time': low_quality_paths.loc[worst_loss_idx, 'path_duration']
        }
        
        worst_performers['longest_time'] = {
            'path': low_quality_paths.loc[worst_time_idx, 'path'],
            'score': low_quality_paths.loc[worst_time_idx, self.score_column],
            'loss': low_quality_paths.loc[worst_time_idx, 'path_sale_loss'],
            'time': low_quality_paths.loc[worst_time_idx, 'path_duration']
        }
        
        return worst_performers
    
    def get_quality_analysis_summary(self) -> Dict[str, Any]:
        """
        获取解质量分析摘要
        
        Returns:
            质量分析摘要
        """
        # 执行所有分析
        optimal_analysis = self.analyze_optimal_discovery_capability()
        distribution_analysis = self.analyze_solution_quality_distribution()
        path_analysis = self.analyze_path_characteristics()
        
        # 生成关键发现
        key_findings = []
        
        # 最优解发现能力
        global_effectiveness = optimal_analysis['discovery_effectiveness']['global_effectiveness']
        effectiveness_grade = global_effectiveness['overall_effectiveness_grade']
        key_findings.append(f"算法发现有效性等级: {effectiveness_grade}")
        
        # 收敛特征
        convergence_patterns = distribution_analysis['convergence_analysis']['global_analysis']['convergence_pattern_classification']
        for pattern, reqs in convergence_patterns.items():
            if reqs:
                key_findings.append(f"{len(reqs)}个请求表现为{pattern}模式")
        
        # 路径长度建议
        length_analysis = path_analysis['length_vs_quality']['optimal_length_analysis']
        if 'recommended_length' in length_analysis:
            key_findings.append(f"推荐最优路径长度: {length_analysis['recommended_length']}")
        
        return {
            'key_findings': key_findings,
            'algorithm_effectiveness_grade': effectiveness_grade,
            'avg_improvement_ratio': optimal_analysis['optimal_vs_average']['global_summary']['avg_algorithm_value'],
            'convergence_consistency': distribution_analysis['convergence_analysis']['global_analysis']['speed_consistency'],
            'quality_distribution_summary': {
                'overall_score_stats': distribution_analysis['distribution_characteristics']['global_distribution']['overall_stats'],
                'cross_request_consistency': distribution_analysis['distribution_characteristics']['global_distribution']['cross_request_variance']['consistency_score']
            },
            'optimal_analysis': optimal_analysis,
            'distribution_analysis': distribution_analysis,
            'path_analysis': path_analysis
        } 