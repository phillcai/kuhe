"""
统计分析模块

实现第一层基础统计分析功能：
- 单请求维度分析
- 全局维度分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import logging
from .utils import DataProcessor

logger = logging.getLogger(__name__)


class StatisticsAnalyzer:
    """统计分析器"""
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化统计分析器
        
        Args:
            df: 包含路径数据的DataFrame
        """
        self.df = DataProcessor.clean_and_validate_data(df)
        self.df = DataProcessor.extract_path_features(self.df)
        
        # 基础信息
        self.total_requests = self.df['req_id'].nunique()
        self.total_paths = len(self.df)
        self.avg_paths_per_request = self.total_paths / self.total_requests
        
        logger.info(f"统计分析器初始化完成: {self.total_requests}个请求, {self.total_paths}条路径")
    
    def analyze_single_request_stats(self) -> Dict[str, Any]:
        """
        单请求维度统计分析
        
        Returns:
            单请求统计分析结果
        """
        logger.info("开始单请求维度统计分析...")
        
        results = {
            'summary_table': {},
            'detailed_stats': {},
            'path_length_analysis': {},
            'anomaly_detection': {}
        }
        
        # 按请求ID分组分析
        for req_id, group in self.df.groupby('req_id'):
            # 基础统计
            req_stats = self._analyze_single_request(group)
            results['summary_table'][req_id] = req_stats['summary']
            results['detailed_stats'][req_id] = req_stats['detailed']
            results['path_length_analysis'][req_id] = req_stats['path_length']
        
        # 异常检测
        results['anomaly_detection'] = self._detect_request_anomalies(results['summary_table'])
        
        # 请求间对比分析
        results['comparison_analysis'] = self._compare_requests(results['summary_table'])
        
        logger.info("单请求维度统计分析完成")
        return results
    
    def _analyze_single_request(self, group: pd.DataFrame) -> Dict[str, Any]:
        """
        分析单个请求的统计信息
        
        Args:
            group: 单个请求的数据
            
        Returns:
            单个请求的统计分析结果
        """
        req_id = group['req_id'].iloc[0]
        
        # 基础摘要统计
        summary = {
            'path_count': len(group),
            'avg_loss': group['path_sale_loss'].mean(),
            'avg_time_minutes': group['path_duration'].mean() / 60,
            'avg_replenish_rate': group['补货率'].mean() if '补货率' in group.columns else 1.0,
            'avg_path_length': group['path_length'].mean(),
            'min_loss': group['path_sale_loss'].min(),
            'max_loss': group['path_sale_loss'].max(),
            'min_time_minutes': group['path_duration'].min() / 60,
            'max_time_minutes': group['path_duration'].max() / 60,
        }
        
        # 详细统计
        detailed = {
            'path_sale_loss': DataProcessor.get_descriptive_statistics(group['path_sale_loss']),
            'path_duration': DataProcessor.get_descriptive_statistics(group['path_duration']),
            'path_length': DataProcessor.get_descriptive_statistics(group['path_length']),
            'time_per_point': DataProcessor.get_descriptive_statistics(group['time_per_point']),
            'loss_per_point': DataProcessor.get_descriptive_statistics(group['loss_per_point'])
        }
        
        if '补货率' in group.columns:
            detailed['replenish_rate'] = DataProcessor.get_descriptive_statistics(group['补货率'])
        
        # 路径长度分析
        path_length_stats = group['path_length'].value_counts().to_dict()
        path_length_analysis = {
            'length_distribution': path_length_stats,
            'most_common_length': group['path_length'].mode().iloc[0] if not group['path_length'].mode().empty else None,
            'length_range': (group['path_length'].min(), group['path_length'].max()),
            'avg_quality_by_length': {}
        }
        
        # 按路径长度分析质量
        if 'total_score' in group.columns:
            for length in sorted(path_length_stats.keys()):
                length_group = group[group['path_length'] == length]
                path_length_analysis['avg_quality_by_length'][length] = {
                    'count': len(length_group),
                    'avg_total_score': length_group['total_score'].mean(),
                    'avg_loss': length_group['path_sale_loss'].mean(),
                    'avg_time': length_group['path_duration'].mean()
                }
        
        return {
            'summary': summary,
            'detailed': detailed,
            'path_length': path_length_analysis
        }
    
    def _detect_request_anomalies(self, summary_table: Dict[str, Dict]) -> Dict[str, Any]:
        """
        检测请求异常值
        
        Args:
            summary_table: 请求摘要统计表
            
        Returns:
            异常检测结果
        """
        # 提取各指标数据
        path_counts = [data['path_count'] for data in summary_table.values()]
        avg_losses = [data['avg_loss'] for data in summary_table.values()]
        avg_times = [data['avg_time_minutes'] for data in summary_table.values()]
        
        # 使用IQR方法检测异常值
        def detect_outliers_iqr(values: List[float], req_ids: List[str]) -> Dict[str, List[str]]:
            if not values:
                return {'outliers': [], 'extreme_outliers': []}
            
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1
            
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            extreme_lower = q1 - 3 * iqr
            extreme_upper = q3 + 3 * iqr
            
            outliers = []
            extreme_outliers = []
            
            for i, (value, req_id) in enumerate(zip(values, req_ids)):
                if value < extreme_lower or value > extreme_upper:
                    extreme_outliers.append(req_id)
                elif value < lower_bound or value > upper_bound:
                    outliers.append(req_id)
            
            return {'outliers': outliers, 'extreme_outliers': extreme_outliers}
        
        req_ids = list(summary_table.keys())
        
        anomalies = {
            'path_count_anomalies': detect_outliers_iqr(path_counts, req_ids),
            'avg_loss_anomalies': detect_outliers_iqr(avg_losses, req_ids),
            'avg_time_anomalies': detect_outliers_iqr(avg_times, req_ids),
            'zero_loss_requests': [req_id for req_id, data in summary_table.items() 
                                 if data['avg_loss'] == 0],
            'high_complexity_requests': [req_id for req_id, data in summary_table.items() 
                                       if data['path_count'] > np.percentile(path_counts, 90)]
        }
        
        return anomalies
    
    def _compare_requests(self, summary_table: Dict[str, Dict]) -> Dict[str, Any]:
        """
        请求间对比分析
        
        Args:
            summary_table: 请求摘要统计表
            
        Returns:
            对比分析结果
        """
        # 提取数据进行对比
        req_ids = list(summary_table.keys())
        path_counts = [summary_table[req_id]['path_count'] for req_id in req_ids]
        avg_losses = [summary_table[req_id]['avg_loss'] for req_id in req_ids]
        avg_times = [summary_table[req_id]['avg_time_minutes'] for req_id in req_ids]
        
        # 排序分析
        comparison = {
            'by_path_count': {
                'highest': sorted(zip(req_ids, path_counts), key=lambda x: x[1], reverse=True)[:5],
                'lowest': sorted(zip(req_ids, path_counts), key=lambda x: x[1])[:5]
            },
            'by_avg_loss': {
                'highest': sorted(zip(req_ids, avg_losses), key=lambda x: x[1], reverse=True)[:5],
                'lowest': sorted(zip(req_ids, avg_losses), key=lambda x: x[1])[:5]
            },
            'by_avg_time': {
                'highest': sorted(zip(req_ids, avg_times), key=lambda x: x[1], reverse=True)[:5],
                'lowest': sorted(zip(req_ids, avg_times), key=lambda x: x[1])[:5]
            },
            'diversity_analysis': {
                'path_count_cv': np.std(path_counts) / np.mean(path_counts) if np.mean(path_counts) > 0 else 0,
                'avg_loss_cv': np.std(avg_losses) / np.mean(avg_losses) if np.mean(avg_losses) > 0 else 0,
                'avg_time_cv': np.std(avg_times) / np.mean(avg_times) if np.mean(avg_times) > 0 else 0
            }
        }
        
        return comparison
    
    def analyze_global_stats(self) -> Dict[str, Any]:
        """
        全局维度统计分析
        
        Returns:
            全局统计分析结果
        """
        logger.info("开始全局维度统计分析...")
        
        results = {
            'basic_info': {
                '总请求数': self.total_requests,
                '总路径数': self.total_paths,
                '平均每请求路径数': round(self.avg_paths_per_request, 1)
            },
            'global_metrics': {},
            'distribution_analysis': {},
            'correlation_analysis': {},
            'variance_analysis': {}
        }
        
        # 全局指标统计
        core_metrics = ['path_sale_loss', 'path_duration', 'path_length']
        if '补货率' in self.df.columns:
            core_metrics.append('补货率')
        
        for metric in core_metrics:
            if metric in self.df.columns:
                results['global_metrics'][metric] = DataProcessor.get_descriptive_statistics(self.df[metric])
        
        # 衍生指标统计
        derived_metrics = ['time_per_point', 'loss_per_point', 'path_complexity']
        for metric in derived_metrics:
            if metric in self.df.columns:
                results['global_metrics'][metric] = DataProcessor.get_descriptive_statistics(self.df[metric])
        
        # 分布分析
        results['distribution_analysis'] = self._analyze_distributions()
        
        # 相关性分析
        results['correlation_analysis'] = self._analyze_correlations()
        
        # 方差分析（请求间差异）
        results['variance_analysis'] = self._analyze_variance_between_requests()
        
        logger.info("全局维度统计分析完成")
        return results
    
    def _analyze_distributions(self) -> Dict[str, Any]:
        """
        分析数据分布特征
        
        Returns:
            分布分析结果
        """
        distribution_results = {}
        
        # 分析核心指标的分布
        metrics_to_analyze = ['path_sale_loss', 'path_duration', 'path_length']
        
        for metric in metrics_to_analyze:
            if metric not in self.df.columns:
                continue
                
            series = self.df[metric].dropna()
            
            # 基础分布统计
            dist_stats = {
                'zero_count': (series == 0).sum(),
                'zero_percentage': (series == 0).sum() / len(series) * 100,
                'positive_count': (series > 0).sum(),
                'negative_count': (series < 0).sum(),
                'unique_values': series.nunique(),
                'most_frequent_value': series.mode().iloc[0] if not series.mode().empty else None,
                'value_frequency': series.value_counts().head(10).to_dict()
            }
            
            # 分位数分析
            percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
            for p in percentiles:
                dist_stats[f'p{p}'] = series.quantile(p/100)
            
            distribution_results[metric] = dist_stats
        
        return distribution_results
    
    def _analyze_correlations(self) -> Dict[str, Any]:
        """
        分析指标间相关性
        
        Returns:
            相关性分析结果
        """
        # 选择数值型列进行相关性分析
        numeric_columns = ['path_sale_loss', 'path_duration', 'path_length', 
                          'time_per_point', 'loss_per_point', 'path_complexity']
        
        available_columns = [col for col in numeric_columns if col in self.df.columns]
        
        if len(available_columns) < 2:
            return {'error': '可用于相关性分析的数值列不足'}
        
        # 计算相关系数矩阵
        correlation_matrix = self.df[available_columns].corr()
        
        # 提取强相关关系（绝对值 > 0.5）
        strong_correlations = []
        for i in range(len(available_columns)):
            for j in range(i+1, len(available_columns)):
                corr_value = correlation_matrix.iloc[i, j]
                if abs(corr_value) > 0.5:
                    strong_correlations.append({
                        'metric1': available_columns[i],
                        'metric2': available_columns[j],
                        'correlation': corr_value,
                        'strength': 'strong' if abs(corr_value) > 0.7 else 'moderate'
                    })
        
        return {
            'correlation_matrix': correlation_matrix.to_dict(),
            'strong_correlations': strong_correlations,
            'summary': {
                'total_pairs': len(available_columns) * (len(available_columns) - 1) // 2,
                'strong_correlations_count': len(strong_correlations),
                'avg_correlation': correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].mean()
            }
        }
    
    def _analyze_variance_between_requests(self) -> Dict[str, Any]:
        """
        分析请求间方差（评估算法在不同请求上的一致性）
        
        Returns:
            方差分析结果
        """
        variance_results = {}
        
        # 计算请求间和请求内方差
        metrics_to_analyze = ['path_sale_loss', 'path_duration', 'path_length']
        
        for metric in metrics_to_analyze:
            if metric not in self.df.columns:
                continue
            
            # 按请求分组计算统计量
            req_means = self.df.groupby('req_id')[metric].mean()
            req_stds = self.df.groupby('req_id')[metric].std()
            req_counts = self.df.groupby('req_id')[metric].count()
            
            # 计算请求间方差和请求内方差
            overall_mean = self.df[metric].mean()
            between_variance = ((req_means - overall_mean) ** 2 * req_counts).sum() / (len(req_means) - 1)
            within_variance = (req_stds ** 2 * (req_counts - 1)).sum() / (req_counts.sum() - len(req_means))
            
            # F统计量（用于评估请求间差异显著性）
            f_statistic = between_variance / within_variance if within_variance > 0 else float('inf')
            
            variance_results[metric] = {
                'between_variance': between_variance,
                'within_variance': within_variance,
                'f_statistic': f_statistic,
                'variance_ratio': between_variance / within_variance if within_variance > 0 else float('inf'),
                'request_means_stats': DataProcessor.get_descriptive_statistics(req_means),
                'request_stds_stats': DataProcessor.get_descriptive_statistics(req_stds.dropna()),
                'consistency_score': 1 / (1 + req_means.std() / req_means.mean()) if req_means.mean() > 0 else 0
            }
        
        return variance_results
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """
        获取统计分析摘要
        
        Returns:
            分析摘要
        """
        single_stats = self.analyze_single_request_stats()
        global_stats = self.analyze_global_stats()
        
        # 生成关键发现
        key_findings = []
        
        # 异常请求识别
        anomalies = single_stats['anomaly_detection']
        if anomalies['zero_loss_requests']:
            key_findings.append(f"发现{len(anomalies['zero_loss_requests'])}个零损失请求")
        
        if anomalies['high_complexity_requests']:
            key_findings.append(f"发现{len(anomalies['high_complexity_requests'])}个高复杂度请求")
        
        # 数据分布特征
        loss_dist = global_stats['distribution_analysis'].get('path_sale_loss', {})
        if loss_dist.get('zero_percentage', 0) > 50:
            key_findings.append(f"超过50%的路径为零损失路径")
        
        # 请求间差异
        variance_analysis = global_stats['variance_analysis']
        for metric, analysis in variance_analysis.items():
            if analysis['consistency_score'] < 0.5:
                key_findings.append(f"{metric}在不同请求间差异较大")
        
        return {
            'basic_info': global_stats['basic_info'],
            'key_findings': key_findings,
            'anomaly_summary': {
                'zero_loss_requests_count': len(anomalies['zero_loss_requests']),
                'high_complexity_requests_count': len(anomalies['high_complexity_requests']),
                'total_anomalies': len(set(anomalies['path_count_anomalies']['outliers'] + 
                                         anomalies['avg_loss_anomalies']['outliers'] + 
                                         anomalies['avg_time_anomalies']['outliers']))
            },
            'data_quality_score': self._calculate_data_quality_score(global_stats),
            'single_request_stats': single_stats,
            'global_stats': global_stats
        }
    
    def _calculate_data_quality_score(self, global_stats: Dict[str, Any]) -> float:
        """
        计算数据质量评分
        
        Args:
            global_stats: 全局统计结果
            
        Returns:
            数据质量评分 (0-1)
        """
        score = 1.0
        
        # 检查数据完整性
        total_values = len(self.df)
        null_counts = self.df.isnull().sum().sum()
        completeness_score = 1 - (null_counts / (total_values * len(self.df.columns)))
        
        # 检查数据一致性（基于相关性分析）
        correlation_analysis = global_stats.get('correlation_analysis', {})
        consistency_score = 1.0
        if 'summary' in correlation_analysis:
            avg_corr = abs(correlation_analysis['summary'].get('avg_correlation', 0))
            consistency_score = min(1.0, avg_corr * 2)  # 适度相关性表示数据一致
        
        # 检查数据分布合理性
        distribution_score = 1.0
        dist_analysis = global_stats.get('distribution_analysis', {})
        for metric, dist_data in dist_analysis.items():
            if dist_data.get('zero_percentage', 0) > 80:  # 过多零值
                distribution_score *= 0.8
        
        # 综合评分
        final_score = (completeness_score * 0.4 + 
                      consistency_score * 0.3 + 
                      distribution_score * 0.3)
        
        return round(final_score, 3) 