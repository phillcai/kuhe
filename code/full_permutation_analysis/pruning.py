"""
剪枝策略模块

实现第四层路径剪枝策略建议功能：
- 基于质量分布的早停策略
- 基于路径特征的剪枝规则
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import logging
from .utils import DataProcessor

logger = logging.getLogger(__name__)


class PruningStrategyAnalyzer:
    """剪枝策略分析器"""
    
    def __init__(self, df: pd.DataFrame, score_column: str = 'total_score'):
        """
        初始化剪枝策略分析器
        
        Args:
            df: 包含路径数据的DataFrame
            score_column: 评分列名
        """
        self.df = DataProcessor.clean_and_validate_data(df)
        self.df = DataProcessor.extract_path_features(self.df)
        self.score_column = score_column
        
        # 验证评分列是否存在
        if score_column not in self.df.columns:
            logger.warning(f"评分列 '{score_column}' 不存在，将使用现有评价系统计算评分")
            self._calculate_scores()
        
        logger.info(f"剪枝策略分析器初始化完成，使用评分列: {self.score_column}")
    
    def _calculate_scores(self):
        """计算路径评分（如果不存在评分列）"""
        # 简单的评分计算逻辑
        from .multi_req_evaluation import MultiReqPathEvaluator
        
        evaluator = MultiReqPathEvaluator()
        self.df = evaluator.evaluate_paths(self.df)
        self.score_column = 'total_score'
    
    def suggest_pruning_strategies(self) -> Dict[str, Any]:
        """
        建议剪枝策略
        
        Returns:
            剪枝策略建议结果
        """
        logger.info("开始剪枝策略分析...")
        
        results = {
            'early_stopping_strategies': {},
            'feature_based_pruning': {},
            'dynamic_pruning_rules': {},
            'implementation_guidelines': {}
        }
        
        # 基于质量分布的早停策略
        results['early_stopping_strategies'] = self._analyze_early_stopping_strategies()
        
        # 基于路径特征的剪枝规则
        results['feature_based_pruning'] = self._analyze_feature_based_pruning()
        
        # 动态剪枝规则
        results['dynamic_pruning_rules'] = self._analyze_dynamic_pruning_rules()
        
        # 实施指导方案
        results['implementation_guidelines'] = self._generate_implementation_guidelines(
            results['early_stopping_strategies'],
            results['feature_based_pruning'],
            results['dynamic_pruning_rules']
        )
        
        logger.info("剪枝策略分析完成")
        return results
    
    def _analyze_early_stopping_strategies(self) -> Dict[str, Any]:
        """
        分析早停策略
        
        Returns:
            早停策略分析结果
        """
        early_stopping = {
            'threshold_based_stopping': {},
            'convergence_based_stopping': {},
            'time_based_stopping': {},
            'effectiveness_analysis': {}
        }
        
        # 按请求分析早停策略
        for req_id, group in self.df.groupby('req_id'):
            # 按评分排序
            sorted_group = group.sort_values(self.score_column, ascending=False)
            total_paths = len(sorted_group)
            
            req_analysis = self._analyze_single_request_early_stopping(sorted_group, req_id)
            
            # 阈值基早停
            if 'threshold_analysis' not in early_stopping['threshold_based_stopping']:
                early_stopping['threshold_based_stopping'][req_id] = req_analysis['threshold_based']
            
            # 收敛基早停
            if 'convergence_analysis' not in early_stopping['convergence_based_stopping']:
                early_stopping['convergence_based_stopping'][req_id] = req_analysis['convergence_based']
        
        # 全局早停策略分析
        early_stopping['global_recommendations'] = self._generate_global_early_stopping_recommendations(
            early_stopping
        )
        
        return early_stopping
    
    def _analyze_single_request_early_stopping(self, sorted_group: pd.DataFrame, req_id: str) -> Dict[str, Any]:
        """
        分析单个请求的早停策略
        
        Args:
            sorted_group: 按评分排序的请求数据
            req_id: 请求ID
            
        Returns:
            单个请求的早停分析结果
        """
        scores = sorted_group[self.score_column].values
        total_paths = len(scores)
        best_score = scores[0]
        
        analysis = {
            'threshold_based': {},
            'convergence_based': {},
            'efficiency_analysis': {}
        }
        
        # 阈值基早停分析
        thresholds = [0.95, 0.90, 0.85, 0.80]
        for threshold in thresholds:
            target_score = best_score * threshold
            
            # 找到达到目标分数需要的路径数
            paths_needed = 0
            for i, score in enumerate(scores):
                if score >= target_score:
                    paths_needed = i + 1
                else:
                    break
            
            if paths_needed == 0:
                paths_needed = total_paths
            
            efficiency = 1 - (paths_needed / total_paths)
            
            analysis['threshold_based'][threshold] = {
                'target_score': target_score,
                'paths_needed': paths_needed,
                'paths_saved': total_paths - paths_needed,
                'efficiency_gain': efficiency,
                'score_loss': (best_score - target_score) / best_score if best_score > 0 else 0
            }
        
        # 收敛基早停分析
        analysis['convergence_based'] = self._analyze_convergence_stopping(scores)
        
        # 效率分析
        analysis['efficiency_analysis'] = {
            'total_paths': total_paths,
            'best_score': best_score,
            'score_distribution': {
                'top_10_percent': scores[:max(1, total_paths//10)].mean() if total_paths >= 10 else best_score,
                'top_25_percent': scores[:max(1, total_paths//4)].mean() if total_paths >= 4 else best_score,
                'median_score': np.median(scores)
            }
        }
        
        return analysis
    
    def _analyze_convergence_stopping(self, scores: np.ndarray) -> Dict[str, Any]:
        """
        分析基于收敛的早停策略
        
        Args:
            scores: 按质量排序的评分数组
            
        Returns:
            收敛早停分析结果
        """
        if len(scores) < 10:
            return {'error': '数据量不足，无法进行收敛分析'}
        
        # 计算累积最大值（收敛曲线）
        cummax_scores = np.maximum.accumulate(scores)
        
        # 寻找收敛点
        convergence_analysis = {
            'plateau_detection': {},
            'improvement_rate_analysis': {},
            'recommended_stopping_points': []
        }
        
        # 平台期检测
        improvement_threshold = 0.001  # 0.1%的改进阈值
        plateau_start = len(cummax_scores)
        
        for i in range(len(cummax_scores) - 1, 0, -1):
            improvement = (cummax_scores[-1] - cummax_scores[i-1]) / cummax_scores[i-1] if cummax_scores[i-1] > 0 else 0
            if improvement > improvement_threshold:
                plateau_start = i
                break
        
        convergence_analysis['plateau_detection'] = {
            'plateau_start_position': plateau_start,
            'plateau_length': len(cummax_scores) - plateau_start,
            'plateau_ratio': (len(cummax_scores) - plateau_start) / len(cummax_scores),
            'score_at_plateau_start': cummax_scores[plateau_start-1] if plateau_start > 0 else cummax_scores[0]
        }
        
        # 改进率分析
        window_size = max(5, len(scores) // 20)  # 窗口大小为总数的5%，最小为5
        improvement_rates = []
        
        for i in range(window_size, len(cummax_scores)):
            prev_score = cummax_scores[i - window_size]
            curr_score = cummax_scores[i]
            rate = (curr_score - prev_score) / prev_score if prev_score > 0 else 0
            improvement_rates.append(rate)
        
        convergence_analysis['improvement_rate_analysis'] = {
            'window_size': window_size,
            'avg_improvement_rate': np.mean(improvement_rates) if improvement_rates else 0,
            'improvement_rate_trend': improvement_rates[-10:] if len(improvement_rates) >= 10 else improvement_rates
        }
        
        # 推荐停止点
        # 基于改进率的停止点
        if improvement_rates:
            low_improvement_threshold = np.mean(improvement_rates) * 0.1
            for i, rate in enumerate(improvement_rates):
                if rate < low_improvement_threshold:
                    stop_point = i + window_size
                    convergence_analysis['recommended_stopping_points'].append({
                        'type': 'improvement_rate_based',
                        'position': stop_point,
                        'score': cummax_scores[stop_point],
                        'efficiency_gain': 1 - (stop_point / len(cummax_scores)),
                        'reason': f'改进率低于阈值 {low_improvement_threshold:.4f}'
                    })
                    break
        
        # 基于平台期的停止点
        if plateau_start < len(cummax_scores):
            convergence_analysis['recommended_stopping_points'].append({
                'type': 'plateau_based',
                'position': plateau_start,
                'score': cummax_scores[plateau_start-1] if plateau_start > 0 else cummax_scores[0],
                'efficiency_gain': 1 - (plateau_start / len(cummax_scores)),
                'reason': f'进入平台期，后续改进有限'
            })
        
        return convergence_analysis
    
    def _generate_global_early_stopping_recommendations(self, early_stopping_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成全局早停策略建议
        
        Args:
            early_stopping_data: 早停分析数据
            
        Returns:
            全局早停建议
        """
        recommendations = {
            'optimal_thresholds': {},
            'universal_stopping_rules': [],
            'request_specific_rules': {},
            'cost_benefit_analysis': {}
        }
        
        # 分析最优阈值
        threshold_performances = {}
        
        for threshold in [0.95, 0.90, 0.85, 0.80]:
            total_efficiency = 0
            total_score_loss = 0
            valid_requests = 0
            
            for req_id, req_data in early_stopping_data['threshold_based_stopping'].items():
                if threshold in req_data:
                    total_efficiency += req_data[threshold]['efficiency_gain']
                    total_score_loss += req_data[threshold]['score_loss']
                    valid_requests += 1
            
            if valid_requests > 0:
                threshold_performances[threshold] = {
                    'avg_efficiency_gain': total_efficiency / valid_requests,
                    'avg_score_loss': total_score_loss / valid_requests,
                    'cost_benefit_ratio': (total_efficiency / valid_requests) / (total_score_loss / valid_requests) if total_score_loss > 0 else float('inf')
                }
        
        # 选择最优阈值
        if threshold_performances:
            optimal_threshold = max(threshold_performances.keys(), 
                                  key=lambda x: threshold_performances[x]['cost_benefit_ratio'])
            recommendations['optimal_thresholds']['global_optimal'] = {
                'threshold': optimal_threshold,
                'performance': threshold_performances[optimal_threshold]
            }
        
        # 通用停止规则
        recommendations['universal_stopping_rules'] = [
            f"当路径评分达到最优解的{optimal_threshold:.0%}时停止搜索",
            "当连续50个路径无显著改进时停止搜索",
            "当搜索时间超过预设限制时强制停止"
        ]
        
        # 成本效益分析
        if threshold_performances:
            recommendations['cost_benefit_analysis'] = {
                'threshold_comparison': threshold_performances,
                'recommended_strategy': f"使用{optimal_threshold:.0%}阈值可获得最佳成本效益比",
                'expected_savings': f"平均可节省{threshold_performances[optimal_threshold]['avg_efficiency_gain']:.1%}的计算资源"
            }
        
        return recommendations
    
    def _analyze_feature_based_pruning(self) -> Dict[str, Any]:
        """
        分析基于特征的剪枝规则
        
        Returns:
            特征剪枝分析结果
        """
        feature_pruning = {
            'length_based_rules': {},
            'performance_based_rules': {},
            'pattern_based_rules': {},
            'effectiveness_evaluation': {}
        }
        
        # 基于路径长度的剪枝规则
        feature_pruning['length_based_rules'] = self._analyze_length_based_pruning()
        
        # 基于性能的剪枝规则
        feature_pruning['performance_based_rules'] = self._analyze_performance_based_pruning()
        
        # 基于模式的剪枝规则
        feature_pruning['pattern_based_rules'] = self._analyze_pattern_based_pruning()
        
        # 有效性评估
        feature_pruning['effectiveness_evaluation'] = self._evaluate_pruning_effectiveness(
            feature_pruning
        )
        
        return feature_pruning
    
    def _analyze_length_based_pruning(self) -> Dict[str, Any]:
        """
        分析基于路径长度的剪枝规则
        
        Returns:
            长度剪枝分析结果
        """
        length_analysis = {
            'length_quality_correlation': {},
            'optimal_length_ranges': {},
            'pruning_rules': []
        }
        
        # 分析长度与质量的关系
        length_scores = self.df.groupby('path_length')[self.score_column].agg(['mean', 'std', 'count'])
        
        # 计算相关性
        try:
            correlation = self.df['path_length'].corr(self.df[self.score_column])
            length_analysis['length_quality_correlation'] = {
                'correlation_coefficient': correlation,
                'strength': 'strong' if abs(correlation) > 0.7 else 'moderate' if abs(correlation) > 0.3 else 'weak',
                'direction': 'positive' if correlation > 0 else 'negative'
            }
        except Exception as e:
            logger.warning(f"长度相关性分析失败: {e}")
            length_analysis['length_quality_correlation'] = {'error': str(e)}
        
        # 识别最优长度范围
        if not length_scores.empty:
            # 找到平均质量最高的长度
            best_lengths = length_scores.nlargest(3, 'mean')
            worst_lengths = length_scores.nsmallest(3, 'mean')
            
            length_analysis['optimal_length_ranges'] = {
                'best_performing_lengths': best_lengths.index.tolist(),
                'worst_performing_lengths': worst_lengths.index.tolist(),
                'recommended_range': (
                    int(length_scores['mean'].quantile(0.75)),
                    int(length_scores.index[length_scores['mean'].idxmax()])
                ) if len(length_scores) > 0 else None
            }
            
            # 生成剪枝规则
            if len(worst_lengths) > 0:
                min_acceptable_score = length_scores['mean'].quantile(0.25)
                bad_lengths = length_scores[length_scores['mean'] < min_acceptable_score].index.tolist()
                
                if bad_lengths:
                    length_analysis['pruning_rules'].append({
                        'rule_type': 'length_exclusion',
                        'description': f'排除长度为{bad_lengths}的路径',
                        'excluded_lengths': bad_lengths,
                        'expected_pruning_ratio': len(self.df[self.df['path_length'].isin(bad_lengths)]) / len(self.df),
                        'quality_impact': 'minimal'
                    })
            
            # 基于样本量的剪枝
            low_sample_lengths = length_scores[length_scores['count'] < 10].index.tolist()
            if low_sample_lengths:
                length_analysis['pruning_rules'].append({
                    'rule_type': 'low_sample_exclusion',
                    'description': f'排除样本量不足的长度{low_sample_lengths}',
                    'excluded_lengths': low_sample_lengths,
                    'expected_pruning_ratio': len(self.df[self.df['path_length'].isin(low_sample_lengths)]) / len(self.df),
                    'quality_impact': 'unknown'
                })
        
        return length_analysis
    
    def _analyze_performance_based_pruning(self) -> Dict[str, Any]:
        """
        分析基于性能的剪枝规则
        
        Returns:
            性能剪枝分析结果
        """
        performance_analysis = {
            'loss_based_rules': [],
            'time_based_rules': [],
            'composite_rules': [],
            'dynamic_thresholds': {}
        }
        
        # 基于损失的剪枝规则
        loss_stats = DataProcessor.get_descriptive_statistics(
            self.df['path_sale_loss'],
            percentiles=[0.25, 0.5, 0.75, 0.8, 0.9, 0.95]
        )
        high_loss_threshold = loss_stats['p75']  # 75分位数作为高损失阈值
        
        if high_loss_threshold > 0:
            high_loss_paths = self.df[self.df['path_sale_loss'] > high_loss_threshold]
            performance_analysis['loss_based_rules'].append({
                'rule_type': 'high_loss_exclusion',
                'description': f'排除损失超过{high_loss_threshold:.2f}的路径',
                'threshold': high_loss_threshold,
                'affected_paths': len(high_loss_paths),
                'pruning_ratio': len(high_loss_paths) / len(self.df),
                'avg_score_impact': high_loss_paths[self.score_column].mean() if len(high_loss_paths) > 0 else 0
            })
        
        # 基于时间的剪枝规则
        time_stats = DataProcessor.get_descriptive_statistics(
            self.df['path_duration'], 
            percentiles=[0.25, 0.5, 0.75, 0.9, 0.95]
        )
        high_time_threshold = time_stats['p90']  # 90分位数作为高时间阈值
        
        long_time_paths = self.df[self.df['path_duration'] > high_time_threshold]
        performance_analysis['time_based_rules'].append({
            'rule_type': 'long_time_exclusion',
            'description': f'排除时间超过{high_time_threshold/60:.1f}分钟的路径',
            'threshold': high_time_threshold,
            'affected_paths': len(long_time_paths),
            'pruning_ratio': len(long_time_paths) / len(self.df),
            'avg_score_impact': long_time_paths[self.score_column].mean() if len(long_time_paths) > 0 else 0
        })
        
        # 复合规则（同时考虑多个指标）
        # 高损失且长时间的路径
        bad_paths = self.df[
            (self.df['path_sale_loss'] > loss_stats['p75']) & 
            (self.df['path_duration'] > time_stats['p75'])
        ]
        
        if len(bad_paths) > 0:
            performance_analysis['composite_rules'].append({
                'rule_type': 'high_loss_and_long_time',
                'description': f'排除高损失(>{loss_stats["p75"]:.2f})且长时间(>{time_stats["p75"]/60:.1f}分钟)的路径',
                'conditions': {
                    'loss_threshold': loss_stats['p75'],
                    'time_threshold': time_stats['p75']
                },
                'affected_paths': len(bad_paths),
                'pruning_ratio': len(bad_paths) / len(self.df),
                'avg_score_impact': bad_paths[self.score_column].mean()
            })
        
        # 动态阈值分析
        performance_analysis['dynamic_thresholds'] = self._analyze_dynamic_thresholds()
        
        return performance_analysis
    
    def _analyze_dynamic_thresholds(self) -> Dict[str, Any]:
        """
        分析动态阈值策略
        
        Returns:
            动态阈值分析结果
        """
        dynamic_analysis = {}
        
        # 按请求分析最优阈值
        request_thresholds = {}
        
        for req_id, group in self.df.groupby('req_id'):
            req_loss_stats = DataProcessor.get_descriptive_statistics(
                group['path_sale_loss'], 
                percentiles=[0.25, 0.5, 0.75, 0.8, 0.9, 0.95]
            )
            req_time_stats = DataProcessor.get_descriptive_statistics(
                group['path_duration'], 
                percentiles=[0.25, 0.5, 0.75, 0.8, 0.9, 0.95]
            )
            
            # 基于该请求的分布确定阈值
            loss_threshold = req_loss_stats['p75'] if req_loss_stats['p75'] > 0 else req_loss_stats['max']
            time_threshold = req_time_stats['p80']
            
            request_thresholds[req_id] = {
                'loss_threshold': loss_threshold,
                'time_threshold': time_threshold,
                'path_count': len(group),
                'pruning_potential': len(group[
                    (group['path_sale_loss'] > loss_threshold) | 
                    (group['path_duration'] > time_threshold)
                ]) / len(group)
            }
        
        dynamic_analysis['request_specific_thresholds'] = request_thresholds
        
        # 分析阈值的一致性
        loss_thresholds = [data['loss_threshold'] for data in request_thresholds.values()]
        time_thresholds = [data['time_threshold'] for data in request_thresholds.values()]
        
        dynamic_analysis['threshold_consistency'] = {
            'loss_threshold_cv': np.std(loss_thresholds) / np.mean(loss_thresholds) if np.mean(loss_thresholds) > 0 else 0,
            'time_threshold_cv': np.std(time_thresholds) / np.mean(time_thresholds) if np.mean(time_thresholds) > 0 else 0,
            'recommendation': 'use_global_thresholds' if np.std(loss_thresholds) / np.mean(loss_thresholds) < 0.3 else 'use_dynamic_thresholds'
        }
        
        return dynamic_analysis
    
    def _analyze_pattern_based_pruning(self) -> Dict[str, Any]:
        """
        分析基于模式的剪枝规则
        
        Returns:
            模式剪枝分析结果
        """
        pattern_analysis = {
            'point_frequency_rules': {},
            'sequence_pattern_rules': {},
            'structural_rules': []
        }
        
        # 分析点位频率模式
        all_points = []
        point_scores = {}
        
        for _, row in self.df.iterrows():
            path = str(row['path'])
            score = row[self.score_column]
            points = path.split('_')
            
            for point in points:
                if point not in point_scores:
                    point_scores[point] = []
                point_scores[point].append(score)
                all_points.append(point)
        
        # 计算每个点位的平均质量
        point_quality = {}
        for point, scores in point_scores.items():
            point_quality[point] = {
                'avg_score': np.mean(scores),
                'frequency': len(scores),
                'score_std': np.std(scores)
            }
        
        # 识别低质量点位
        if point_quality:
            avg_quality = np.mean([data['avg_score'] for data in point_quality.values()])
            low_quality_points = [
                point for point, data in point_quality.items() 
                if data['avg_score'] < avg_quality * 0.8 and data['frequency'] > 10
            ]
            
            if low_quality_points:
                pattern_analysis['point_frequency_rules']['low_quality_points'] = {
                    'points': low_quality_points,
                    'rule_description': f'避免包含点位{low_quality_points}的路径',
                    'expected_impact': len(self.df[self.df['path'].str.contains('|'.join(low_quality_points), na=False)]) / len(self.df)
                }
        
        # 分析序列模式
        pair_scores = {}
        for _, row in self.df.iterrows():
            path = str(row['path'])
            score = row[self.score_column]
            points = path.split('_')
            
            for i in range(len(points) - 1):
                pair = f"{points[i]}_{points[i+1]}"
                if pair not in pair_scores:
                    pair_scores[pair] = []
                pair_scores[pair].append(score)
        
        # 识别低效序列
        if pair_scores:
            avg_pair_quality = np.mean([np.mean(scores) for scores in pair_scores.values()])
            low_quality_pairs = [
                pair for pair, scores in pair_scores.items()
                if np.mean(scores) < avg_pair_quality * 0.8 and len(scores) > 5
            ]
            
            if low_quality_pairs:
                pattern_analysis['sequence_pattern_rules']['low_quality_sequences'] = {
                    'sequences': low_quality_pairs,
                    'rule_description': f'避免包含序列{low_quality_pairs}的路径',
                    'expected_impact': sum([
                        len(self.df[self.df['path'].str.contains(pair, na=False)]) 
                        for pair in low_quality_pairs
                    ]) / len(self.df)
                }
        
        # 结构规则
        # 基于路径长度和质量的关系
        length_quality = self.df.groupby('path_length')[self.score_column].mean()
        if not length_quality.empty:
            optimal_length = length_quality.idxmax()
            pattern_analysis['structural_rules'].append({
                'rule_type': 'optimal_length_preference',
                'description': f'优先考虑长度为{optimal_length}的路径',
                'optimal_length': optimal_length,
                'quality_advantage': length_quality[optimal_length] - length_quality.mean()
            })
        
        return pattern_analysis
    
    def _evaluate_pruning_effectiveness(self, feature_pruning: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估剪枝策略的有效性
        
        Args:
            feature_pruning: 特征剪枝分析结果
            
        Returns:
            剪枝有效性评估结果
        """
        effectiveness = {
            'individual_rule_effectiveness': {},
            'combined_rule_effectiveness': {},
            'cost_benefit_analysis': {}
        }
        
        # 评估单个规则的有效性
        all_rules = []
        
        # 收集所有规则
        if 'length_based_rules' in feature_pruning:
            all_rules.extend(feature_pruning['length_based_rules'].get('pruning_rules', []))
        
        if 'performance_based_rules' in feature_pruning:
            all_rules.extend(feature_pruning['performance_based_rules'].get('loss_based_rules', []))
            all_rules.extend(feature_pruning['performance_based_rules'].get('time_based_rules', []))
            all_rules.extend(feature_pruning['performance_based_rules'].get('composite_rules', []))
        
        # 评估每个规则
        for rule in all_rules:
            rule_id = f"{rule.get('rule_type', 'unknown')}_{hash(str(rule)) % 1000}"
            
            effectiveness['individual_rule_effectiveness'][rule_id] = {
                'rule_description': rule.get('description', ''),
                'pruning_ratio': rule.get('pruning_ratio', 0),
                'quality_impact': rule.get('avg_score_impact', 0),
                'efficiency_score': self._calculate_rule_efficiency_score(rule),
                'recommendation': self._generate_rule_recommendation(rule)
            }
        
        # 评估组合规则的有效性
        effectiveness['combined_rule_effectiveness'] = self._evaluate_combined_rules(all_rules)
        
        # 成本效益分析
        effectiveness['cost_benefit_analysis'] = self._perform_cost_benefit_analysis(all_rules)
        
        return effectiveness
    
    def _calculate_rule_efficiency_score(self, rule: Dict[str, Any]) -> float:
        """
        计算规则效率评分
        
        Args:
            rule: 剪枝规则
            
        Returns:
            效率评分 (0-1)
        """
        pruning_ratio = rule.get('pruning_ratio', 0)
        quality_impact = rule.get('avg_score_impact', 0)
        
        # 全局平均质量
        global_avg_quality = self.df[self.score_column].mean()
        
        # 计算质量损失比例
        quality_loss_ratio = abs(quality_impact - global_avg_quality) / global_avg_quality if global_avg_quality > 0 else 0
        
        # 效率评分 = 剪枝比例 / (1 + 质量损失比例)
        efficiency_score = pruning_ratio / (1 + quality_loss_ratio)
        
        return min(1.0, efficiency_score)
    
    def _generate_rule_recommendation(self, rule: Dict[str, Any]) -> str:
        """
        生成规则建议
        
        Args:
            rule: 剪枝规则
            
        Returns:
            规则建议
        """
        pruning_ratio = rule.get('pruning_ratio', 0)
        quality_impact = rule.get('avg_score_impact', 0)
        global_avg_quality = self.df[self.score_column].mean()
        
        if pruning_ratio > 0.2 and quality_impact < global_avg_quality * 0.9:
            return "强烈推荐：高剪枝效率，低质量损失"
        elif pruning_ratio > 0.1 and quality_impact < global_avg_quality:
            return "推荐：中等剪枝效率，可接受的质量损失"
        elif pruning_ratio > 0.05:
            return "谨慎使用：剪枝效率有限"
        else:
            return "不推荐：剪枝效率过低"
    
    def _evaluate_combined_rules(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评估组合规则效果
        
        Args:
            rules: 剪枝规则列表
            
        Returns:
            组合规则评估结果
        """
        if not rules:
            return {'error': '无可用规则进行组合评估'}
        
        # 选择效率最高的规则进行组合
        efficient_rules = [
            rule for rule in rules 
            if rule.get('pruning_ratio', 0) > 0.05 and 
               rule.get('avg_score_impact', 0) > self.df[self.score_column].quantile(0.25)
        ]
        
        if not efficient_rules:
            return {'error': '无高效规则可用于组合'}
        
        # 模拟组合效果
        combined_effectiveness = {
            'rule_combination': [rule.get('rule_type', 'unknown') for rule in efficient_rules],
            'estimated_combined_pruning_ratio': min(0.8, sum([rule.get('pruning_ratio', 0) for rule in efficient_rules])),
            'estimated_quality_impact': np.mean([rule.get('avg_score_impact', 0) for rule in efficient_rules]),
            'synergy_analysis': self._analyze_rule_synergy(efficient_rules)
        }
        
        return combined_effectiveness
    
    def _analyze_rule_synergy(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析规则协同效应
        
        Args:
            rules: 规则列表
            
        Returns:
            协同效应分析结果
        """
        synergy = {
            'overlap_analysis': {},
            'complementarity_score': 0,
            'potential_conflicts': []
        }
        
        # 分析规则重叠
        rule_types = [rule.get('rule_type', '') for rule in rules]
        type_counts = {}
        for rule_type in rule_types:
            type_counts[rule_type] = type_counts.get(rule_type, 0) + 1
        
        synergy['overlap_analysis'] = {
            'rule_type_distribution': type_counts,
            'diversity_score': len(type_counts) / len(rules) if rules else 0
        }
        
        # 计算互补性评分
        length_based = any('length' in rule.get('rule_type', '') for rule in rules)
        performance_based = any('loss' in rule.get('rule_type', '') or 'time' in rule.get('rule_type', '') for rule in rules)
        pattern_based = any('pattern' in rule.get('rule_type', '') or 'sequence' in rule.get('rule_type', '') for rule in rules)
        
        complementarity_factors = [length_based, performance_based, pattern_based]
        synergy['complementarity_score'] = sum(complementarity_factors) / len(complementarity_factors)
        
        return synergy
    
    def _perform_cost_benefit_analysis(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行成本效益分析
        
        Args:
            rules: 剪枝规则列表
            
        Returns:
            成本效益分析结果
        """
        if not rules:
            return {'error': '无规则可用于成本效益分析'}
        
        analysis = {
            'computational_savings': {},
            'quality_trade_offs': {},
            'roi_analysis': {},
            'implementation_priorities': []
        }
        
        # 计算计算资源节省
        total_paths = len(self.df)
        total_pruning_potential = sum([rule.get('pruning_ratio', 0) for rule in rules])
        
        analysis['computational_savings'] = {
            'total_paths': total_paths,
            'potential_paths_saved': int(total_paths * min(0.8, total_pruning_potential)),
            'computational_reduction_ratio': min(0.8, total_pruning_potential),
            'estimated_time_savings': f"{min(80, total_pruning_potential * 100):.1f}%"
        }
        
        # 质量权衡分析
        global_avg_quality = self.df[self.score_column].mean()
        quality_impacts = [rule.get('avg_score_impact', global_avg_quality) for rule in rules]
        
        analysis['quality_trade_offs'] = {
            'global_avg_quality': global_avg_quality,
            'min_quality_after_pruning': min(quality_impacts) if quality_impacts else global_avg_quality,
            'avg_quality_after_pruning': np.mean(quality_impacts) if quality_impacts else global_avg_quality,
            'quality_retention_ratio': (np.mean(quality_impacts) / global_avg_quality) if global_avg_quality > 0 and quality_impacts else 1.0
        }
        
        # ROI分析
        quality_retention = analysis['quality_trade_offs']['quality_retention_ratio']
        computational_savings = analysis['computational_savings']['computational_reduction_ratio']
        
        roi_score = (computational_savings * quality_retention) / (1 - quality_retention + 0.1)  # 避免除零
        
        analysis['roi_analysis'] = {
            'roi_score': roi_score,
            'interpretation': 'excellent' if roi_score > 2 else 'good' if roi_score > 1 else 'fair' if roi_score > 0.5 else 'poor'
        }
        
        # 实施优先级
        rule_priorities = []
        for rule in rules:
            efficiency_score = self._calculate_rule_efficiency_score(rule)
            impact_score = rule.get('pruning_ratio', 0)
            priority_score = efficiency_score * 0.6 + impact_score * 0.4
            
            rule_priorities.append({
                'rule_type': rule.get('rule_type', 'unknown'),
                'priority_score': priority_score,
                'priority_level': 'high' if priority_score > 0.7 else 'medium' if priority_score > 0.4 else 'low'
            })
        
        rule_priorities.sort(key=lambda x: x['priority_score'], reverse=True)
        analysis['implementation_priorities'] = rule_priorities
        
        return analysis
    
    def _analyze_dynamic_pruning_rules(self) -> Dict[str, Any]:
        """
        分析动态剪枝规则
        
        Returns:
            动态剪枝规则分析结果
        """
        dynamic_rules = {
            'adaptive_thresholds': {},
            'context_aware_rules': {},
            'learning_based_rules': {},
            'implementation_framework': {}
        }
        
        # 自适应阈值分析
        dynamic_rules['adaptive_thresholds'] = self._analyze_adaptive_thresholds()
        
        # 上下文感知规则
        dynamic_rules['context_aware_rules'] = self._analyze_context_aware_rules()
        
        # 基于学习的规则
        dynamic_rules['learning_based_rules'] = self._analyze_learning_based_rules()
        
        # 实施框架
        dynamic_rules['implementation_framework'] = self._design_implementation_framework(
            dynamic_rules
        )
        
        return dynamic_rules
    
    def _analyze_adaptive_thresholds(self) -> Dict[str, Any]:
        """
        分析自适应阈值策略
        
        Returns:
            自适应阈值分析结果
        """
        adaptive_analysis = {
            'threshold_adaptation_strategies': [],
            'performance_monitoring': {},
            'adjustment_mechanisms': {}
        }
        
        # 基于历史性能的阈值调整
        for req_id, group in self.df.groupby('req_id'):
            sorted_group = group.sort_values(self.score_column, ascending=False)
            
            # 分析不同阈值下的性能
            thresholds = [0.95, 0.90, 0.85]
            threshold_performance = {}
            
            for threshold in thresholds:
                target_score = sorted_group[self.score_column].max() * threshold
                paths_needed = len(sorted_group[sorted_group[self.score_column] >= target_score])
                efficiency = 1 - (paths_needed / len(sorted_group))
                
                threshold_performance[threshold] = {
                    'paths_needed': paths_needed,
                    'efficiency': efficiency,
                    'score_achieved': target_score
                }
            
            # 找到最优阈值
            optimal_threshold = max(threshold_performance.keys(), 
                                  key=lambda x: threshold_performance[x]['efficiency'])
            
            adaptive_analysis['threshold_adaptation_strategies'].append({
                'req_id': req_id,
                'optimal_threshold': optimal_threshold,
                'performance_data': threshold_performance,
                'adaptation_rule': f"对于请求{req_id}，使用{optimal_threshold:.0%}阈值可获得最佳效率"
            })
        
        return adaptive_analysis
    
    def _analyze_context_aware_rules(self) -> Dict[str, Any]:
        """
        分析上下文感知规则
        
        Returns:
            上下文感知规则分析结果
        """
        context_rules = {
            'request_type_specific_rules': {},
            'temporal_rules': {},
            'resource_constraint_rules': {}
        }
        
        # 基于请求类型的规则
        # 如果有聚类信息，使用聚类结果
        if 'cluster' in self.df.columns:
            for cluster_id in self.df['cluster'].unique():
                cluster_data = self.df[self.df['cluster'] == cluster_id]
                
                # 为该聚类定制剪枝规则
                cluster_rules = []
                
                # 基于该聚类的特征定制规则
                avg_loss = cluster_data['path_sale_loss'].mean()
                avg_time = cluster_data['path_duration'].mean()
                
                if avg_loss > self.df['path_sale_loss'].quantile(0.75):
                    cluster_rules.append({
                        'rule': 'strict_loss_threshold',
                        'threshold': avg_loss * 0.8,
                        'reason': '该类型请求损失敏感'
                    })
                
                if avg_time > self.df['path_duration'].quantile(0.75):
                    cluster_rules.append({
                        'rule': 'strict_time_threshold',
                        'threshold': avg_time * 0.9,
                        'reason': '该类型请求时间敏感'
                    })
                
                context_rules['request_type_specific_rules'][f'cluster_{cluster_id}'] = cluster_rules
        
        return context_rules
    
    def _analyze_learning_based_rules(self) -> Dict[str, Any]:
        """
        分析基于学习的剪枝规则
        
        Returns:
            学习型剪枝规则分析结果
        """
        learning_rules = {
            'pattern_learning': {},
            'performance_prediction': {},
            'adaptive_mechanisms': {}
        }
        
        # 模式学习分析
        # 分析高质量路径的共同特征
        top_paths = self.df.nlargest(int(len(self.df) * 0.1), self.score_column)
        
        # 学习高质量路径的特征模式
        high_quality_patterns = {
            'avg_length': top_paths['path_length'].mean(),
            'length_std': top_paths['path_length'].std(),
            'common_length_range': (
                top_paths['path_length'].quantile(0.25),
                top_paths['path_length'].quantile(0.75)
            ),
            'performance_profile': {
                'avg_loss': top_paths['path_sale_loss'].mean(),
                'avg_time': top_paths['path_duration'].mean(),
                'avg_efficiency': top_paths['time_per_point'].mean()
            }
        }
        
        learning_rules['pattern_learning'] = {
            'high_quality_patterns': high_quality_patterns,
            'learning_rule': "优先保留符合高质量模式的路径",
            'pattern_matching_criteria': [
                f"路径长度在{high_quality_patterns['common_length_range'][0]:.0f}-{high_quality_patterns['common_length_range'][1]:.0f}之间",
                f"损失低于{high_quality_patterns['performance_profile']['avg_loss']:.2f}",
                f"时间效率高于{high_quality_patterns['performance_profile']['avg_efficiency']:.2f}"
            ]
        }
        
        return learning_rules
    
    def _design_implementation_framework(self, dynamic_rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        设计实施框架
        
        Args:
            dynamic_rules: 动态规则分析结果
            
        Returns:
            实施框架设计
        """
        framework = {
            'architecture_design': {},
            'implementation_phases': [],
            'monitoring_metrics': [],
            'feedback_mechanisms': {}
        }
        
        # 架构设计
        framework['architecture_design'] = {
            'components': [
                'threshold_manager',
                'rule_engine',
                'performance_monitor',
                'adaptation_controller'
            ],
            'data_flow': [
                '输入路径数据',
                '应用当前剪枝规则',
                '监控剪枝效果',
                '调整规则参数',
                '更新剪枝策略'
            ],
            'interfaces': [
                'rule_configuration_api',
                'performance_monitoring_api',
                'adaptation_control_api'
            ]
        }
        
        # 实施阶段
        framework['implementation_phases'] = [
            {
                'phase': 1,
                'name': '基础剪枝实施',
                'duration': '2-3周',
                'deliverables': ['静态剪枝规则', '基础监控']
            },
            {
                'phase': 2,
                'name': '自适应阈值实施',
                'duration': '3-4周',
                'deliverables': ['动态阈值调整', '性能反馈机制']
            },
            {
                'phase': 3,
                'name': '智能剪枝实施',
                'duration': '4-6周',
                'deliverables': ['学习型规则', '上下文感知剪枝']
            }
        ]
        
        # 监控指标
        framework['monitoring_metrics'] = [
            'pruning_ratio',
            'quality_retention_rate',
            'computational_savings',
            'false_positive_rate',
            'adaptation_frequency'
        ]
        
        return framework
    
    def _generate_implementation_guidelines(self, early_stopping: Dict[str, Any], 
                                          feature_pruning: Dict[str, Any], 
                                          dynamic_rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成实施指导方案
        
        Args:
            early_stopping: 早停策略分析结果
            feature_pruning: 特征剪枝分析结果
            dynamic_rules: 动态规则分析结果
            
        Returns:
            实施指导方案
        """
        guidelines = {
            'quick_wins': [],
            'implementation_roadmap': {},
            'risk_mitigation': {},
            'success_metrics': {},
            'resource_requirements': {}
        }
        
        # 快速收益策略
        guidelines['quick_wins'] = [
            {
                'strategy': '阈值基早停',
                'implementation_effort': 'low',
                'expected_benefit': 'high',
                'timeline': '1-2周',
                'description': '实施基于质量阈值的早停策略，快速减少计算量'
            },
            {
                'strategy': '长度基剪枝',
                'implementation_effort': 'low',
                'expected_benefit': 'medium',
                'timeline': '1周',
                'description': '排除明显不合理长度的路径'
            },
            {
                'strategy': '性能基剪枝',
                'implementation_effort': 'medium',
                'expected_benefit': 'high',
                'timeline': '2-3周',
                'description': '基于损失和时间阈值进行剪枝'
            }
        ]
        
        # 实施路线图
        guidelines['implementation_roadmap'] = {
            'phase_1': {
                'name': '基础剪枝实施',
                'duration': '4-6周',
                'objectives': ['实施静态剪枝规则', '建立监控体系'],
                'deliverables': ['剪枝规则引擎', '性能监控仪表板'],
                'success_criteria': ['剪枝率达到20%以上', '质量损失小于5%']
            },
            'phase_2': {
                'name': '自适应优化',
                'duration': '6-8周',
                'objectives': ['实施动态阈值调整', '优化剪枝策略'],
                'deliverables': ['自适应阈值系统', '策略优化工具'],
                'success_criteria': ['剪枝效率提升30%', '适应性评分达到0.8以上']
            },
            'phase_3': {
                'name': '智能化升级',
                'duration': '8-12周',
                'objectives': ['实施学习型剪枝', '完善反馈机制'],
                'deliverables': ['智能剪枝系统', '完整反馈循环'],
                'success_criteria': ['整体效率提升50%以上', '系统稳定性达到99%']
            }
        }
        
        # 风险缓解
        guidelines['risk_mitigation'] = {
            'quality_degradation_risk': {
                'description': '剪枝可能导致最优解丢失',
                'mitigation_strategies': [
                    '设置质量下限保护',
                    '实施渐进式剪枝',
                    '建立回滚机制'
                ],
                'monitoring_indicators': ['质量保持率', '最优解发现率']
            },
            'over_pruning_risk': {
                'description': '过度剪枝导致解空间过小',
                'mitigation_strategies': [
                    '设置最小路径数量保护',
                    '动态调整剪枝强度',
                    '多策略并行验证'
                ],
                'monitoring_indicators': ['路径覆盖率', '解多样性指标']
            },
            'adaptation_instability_risk': {
                'description': '自适应机制可能导致策略不稳定',
                'mitigation_strategies': [
                    '设置调整频率限制',
                    '使用平滑调整机制',
                    '建立稳定性检测'
                ],
                'monitoring_indicators': ['策略变化频率', '性能波动幅度']
            }
        }
        
        # 成功指标
        guidelines['success_metrics'] = {
            'efficiency_metrics': [
                '计算时间减少比例',
                '路径评估数量减少',
                '资源利用率提升'
            ],
            'quality_metrics': [
                '最优解保持率',
                '平均解质量保持率',
                '质量方差变化'
            ],
            'adaptability_metrics': [
                '不同场景适应性',
                '参数调整响应速度',
                '策略优化效果'
            ]
        }
        
        # 资源需求
        guidelines['resource_requirements'] = {
            'development_resources': {
                'developers': '2-3人',
                'timeline': '3-6个月',
                'skills_required': ['算法设计', '性能优化', '数据分析']
            },
            'infrastructure_resources': {
                'computing_power': '中等',
                'storage_requirements': '低',
                'monitoring_tools': '必需'
            },
            'operational_resources': {
                'maintenance_effort': '低到中等',
                'monitoring_frequency': '每日',
                'optimization_frequency': '每周'
            }
        }
        
        return guidelines
    
    def get_pruning_analysis_summary(self) -> Dict[str, Any]:
        """
        获取剪枝策略分析摘要
        
        Returns:
            剪枝策略分析摘要
        """
        # 执行完整分析
        analysis_results = self.suggest_pruning_strategies()
        
        # 提取关键信息
        early_stopping = analysis_results['early_stopping_strategies']
        feature_pruning = analysis_results['feature_based_pruning']
        implementation = analysis_results['implementation_guidelines']
        
        # 生成摘要
        summary = {
            'key_recommendations': [],
            'expected_benefits': {},
            'implementation_priority': [],
            'risk_assessment': 'low',
            'detailed_results': analysis_results
        }
        
        # 关键建议
        if 'global_recommendations' in early_stopping:
            global_rec = early_stopping['global_recommendations']
            if 'optimal_thresholds' in global_rec:
                optimal_threshold = global_rec['optimal_thresholds'].get('global_optimal', {}).get('threshold', 0.9)
                summary['key_recommendations'].append(f"实施{optimal_threshold:.0%}质量阈值早停策略")
        
        # 从快速收益中提取建议
        if 'quick_wins' in implementation:
            for win in implementation['quick_wins'][:3]:  # 前3个快速收益
                summary['key_recommendations'].append(win['description'])
        
        # 预期收益
        if 'cost_benefit_analysis' in feature_pruning.get('effectiveness_evaluation', {}):
            cost_benefit = feature_pruning['effectiveness_evaluation']['cost_benefit_analysis']
            summary['expected_benefits'] = {
                'computational_savings': cost_benefit.get('computational_savings', {}).get('estimated_time_savings', '未知'),
                'quality_retention': f"{cost_benefit.get('quality_trade_offs', {}).get('quality_retention_ratio', 1.0):.1%}",
                'roi_assessment': cost_benefit.get('roi_analysis', {}).get('interpretation', '未知')
            }
        
        # 实施优先级
        if 'quick_wins' in implementation:
            for win in implementation['quick_wins']:
                priority_item = {
                    'strategy': win['strategy'],
                    'effort': win['implementation_effort'],
                    'benefit': win['expected_benefit'],
                    'timeline': win['timeline']
                }
                summary['implementation_priority'].append(priority_item)
        
        # 风险评估
        if 'risk_mitigation' in implementation:
            risk_count = len(implementation['risk_mitigation'])
            if risk_count <= 2:
                summary['risk_assessment'] = 'low'
            elif risk_count <= 4:
                summary['risk_assessment'] = 'medium'
            else:
                summary['risk_assessment'] = 'high'
        
        return summary 