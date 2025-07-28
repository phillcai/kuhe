"""
可视化模块

提供各种分析结果的可视化功能
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class VisualizationManager:
    """可视化管理器"""
    
    def __init__(self, output_dir: str = 'output/visualizations'):
        """
        初始化可视化管理器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 设置图表样式
        plt.style.use('default')
        sns.set_palette("husl")
        
        logger.info(f"可视化管理器初始化完成，输出目录: {output_dir}")
    
    def create_statistics_visualizations(self, statistics_results: Dict[str, Any], 
                                       filename: str = 'statistics_analysis.png') -> str:
        """
        创建统计分析可视化图表
        
        Args:
            statistics_results: 统计分析结果
            filename: 输出文件名
            
        Returns:
            保存的文件路径
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('全排列路径算法统计分析', fontsize=16, fontweight='bold')
        
        try:
            # 1. 各请求路径数量对比
            if 'single_request_stats' in statistics_results:
                single_stats = statistics_results['single_request_stats']
                if 'summary_table' in single_stats:
                    req_ids = list(single_stats['summary_table'].keys())
                    path_counts = [single_stats['summary_table'][req_id]['path_count'] 
                                 for req_id in req_ids]
                    
                    axes[0, 0].bar(range(len(req_ids)), path_counts, color='skyblue', alpha=0.7)
                    axes[0, 0].set_title('各请求路径数量分布')
                    axes[0, 0].set_xlabel('请求ID')
                    axes[0, 0].set_ylabel('路径数量')
                    axes[0, 0].tick_params(axis='x', rotation=45)
                    axes[0, 0].set_xticks(range(len(req_ids)))
                    axes[0, 0].set_xticklabels([req_id[:8] for req_id in req_ids])
            
            # 2. 平均损失对比
            if 'single_request_stats' in statistics_results:
                avg_losses = [single_stats['summary_table'][req_id]['avg_loss'] 
                            for req_id in req_ids]
                
                axes[0, 1].bar(range(len(req_ids)), avg_losses, color='lightcoral', alpha=0.7)
                axes[0, 1].set_title('各请求平均销量损失')
                axes[0, 1].set_xlabel('请求ID')
                axes[0, 1].set_ylabel('平均损失')
                axes[0, 1].tick_params(axis='x', rotation=45)
                axes[0, 1].set_xticks(range(len(req_ids)))
                axes[0, 1].set_xticklabels([req_id[:8] for req_id in req_ids])
            
            # 3. 全局指标分布
            if 'global_stats' in statistics_results:
                global_stats = statistics_results['global_stats']
                if 'global_metrics' in global_stats:
                    metrics = global_stats['global_metrics']
                    if 'path_sale_loss' in metrics:
                        loss_stats = metrics['path_sale_loss']
                        labels = ['最小值', '25%分位', '中位数', '75%分位', '最大值']
                        values = [loss_stats['min'], loss_stats['p25'], 
                                loss_stats['p50'], loss_stats['p75'], loss_stats['max']]
                        
                        axes[1, 0].plot(labels, values, marker='o', linewidth=2, markersize=8)
                        axes[1, 0].set_title('销量损失分布特征')
                        axes[1, 0].set_ylabel('损失值')
                        axes[1, 0].tick_params(axis='x', rotation=45)
            
            # 4. 数据质量评分
            if 'data_quality_score' in statistics_results:
                quality_score = statistics_results['data_quality_score']
                
                # 创建质量评分仪表盘
                theta = np.linspace(0, 2*np.pi, 100)
                r = np.ones_like(theta)
                
                ax_polar = plt.subplot(2, 2, 4, projection='polar')
                ax_polar.fill_between(theta, 0, r, alpha=0.3, color='lightgreen')
                ax_polar.fill_between(theta, 0, r * quality_score, alpha=0.7, color='green')
                ax_polar.set_ylim(0, 1)
                ax_polar.set_title(f'数据质量评分: {quality_score:.3f}', pad=20)
                ax_polar.set_theta_zero_location('N')
                ax_polar.set_theta_direction(-1)
                ax_polar.set_rlabel_position(0)
        
        except Exception as e:
            logger.error(f"统计可视化创建失败: {e}")
            # 创建错误信息图表
            fig.text(0.5, 0.5, f'可视化创建失败: {str(e)}', 
                    ha='center', va='center', fontsize=12)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"统计分析可视化已保存到: {filepath}")
        return filepath
    
    def create_quality_visualizations(self, quality_results: Dict[str, Any], 
                                    filename: str = 'quality_analysis.png') -> str:
        """
        创建解质量分析可视化图表
        
        Args:
            quality_results: 质量分析结果
            filename: 输出文件名
            
        Returns:
            保存的文件路径
        """
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('解质量分析', fontsize=16, fontweight='bold')
        
        try:
            # 1. Top-K路径质量分布
            if 'optimal_analysis' in quality_results:
                optimal_analysis = quality_results['optimal_analysis']
                if 'top_k_analysis' in optimal_analysis:
                    top_k_data = optimal_analysis['top_k_analysis'].get('global_summary', {})
                    
                    percentiles = ['top_1%', 'top_5%', 'top_10%', 'top_25%']
                    scores = [top_k_data.get(p, {}).get('avg_score_across_requests', 0) 
                            for p in percentiles]
                    
                    if any(score > 0 for score in scores):
                        axes[0, 0].bar(percentiles, scores, color='gold', alpha=0.7)
                        axes[0, 0].set_title('Top-K路径平均质量')
                        axes[0, 0].set_ylabel('平均评分')
                        axes[0, 0].tick_params(axis='x', rotation=45)
            
            # 2. 收敛曲线示例
            if 'distribution_analysis' in quality_results:
                convergence_data = quality_results['distribution_analysis'].get('convergence_analysis', {})
                if 'by_request' in convergence_data:
                    # 选择一个请求的收敛曲线作为示例
                    for req_id, req_data in list(convergence_data['by_request'].items())[:1]:
                        curve = req_data.get('convergence_curve', [])
                        if curve:
                            axes[0, 1].plot(curve[:100], linewidth=2, color='blue')
                            axes[0, 1].set_title(f'收敛曲线示例 ({req_id[:8]})')
                            axes[0, 1].set_xlabel('路径排序位置')
                            axes[0, 1].set_ylabel('累积最优评分')
            
            # 3. 路径长度vs质量关系
            if 'path_analysis' in quality_results:
                length_analysis = quality_results['path_analysis'].get('length_vs_quality', {})
                if 'by_length' in length_analysis:
                    length_data = length_analysis['by_length']
                    lengths = list(length_data.keys())
                    avg_scores = [length_data[length]['avg_score'] for length in lengths]
                    
                    axes[0, 2].scatter(lengths, avg_scores, s=60, alpha=0.7, color='purple')
                    axes[0, 2].plot(lengths, avg_scores, '--', alpha=0.5, color='purple')
                    axes[0, 2].set_title('路径长度vs平均质量')
                    axes[0, 2].set_xlabel('路径长度')
                    axes[0, 2].set_ylabel('平均评分')
            
            # 4. 算法价值分布
            if 'optimal_analysis' in quality_results:
                value_data = optimal_analysis.get('optimal_vs_average', {})
                if 'by_request' in value_data:
                    improvements = [data['algorithm_value_score'] 
                                  for data in value_data['by_request'].values()]
                    
                    if improvements:
                        axes[1, 0].hist(improvements, bins=10, alpha=0.7, color='green', edgecolor='black')
                        axes[1, 0].set_title('算法价值评分分布')
                        axes[1, 0].set_xlabel('价值评分')
                        axes[1, 0].set_ylabel('请求数量')
            
            # 5. 质量层次分布
            if 'optimal_analysis' in quality_results:
                comparison_data = optimal_analysis.get('request_optimal_comparison', {})
                if 'consistency_analysis' in comparison_data:
                    quality_tiers = comparison_data['consistency_analysis'].get('quality_tiers', {})
                    if 'tier_statistics' in quality_tiers:
                        tier_stats = quality_tiers['tier_statistics']
                        tier_names = list(tier_stats.keys())
                        tier_counts = [tier_stats[name]['count'] for name in tier_names]
                        
                        colors = ['gold', 'silver', 'orange', 'lightcoral']
                        axes[1, 1].pie(tier_counts, labels=tier_names, autopct='%1.1f%%', 
                                     colors=colors[:len(tier_names)])
                        axes[1, 1].set_title('最优解质量层次分布')
            
            # 6. 发现有效性评估
            if 'optimal_analysis' in quality_results:
                effectiveness_data = optimal_analysis.get('discovery_effectiveness', {})
                if 'global_effectiveness' in effectiveness_data:
                    global_eff = effectiveness_data['global_effectiveness']
                    
                    metrics = ['效率比率', '收敛速度', '一致性评分']
                    values = [
                        global_eff.get('avg_efficiency_ratio', 0),
                        min(1.0, global_eff.get('avg_convergence_rate', 0) * 10),  # 标准化
                        global_eff.get('consistency_score', 0)
                    ]
                    
                    angles = np.linspace(0, 2*np.pi, len(metrics), endpoint=False)
                    values_plot = values + [values[0]]  # 闭合图形
                    angles_plot = np.concatenate([angles, [angles[0]]])
                    
                    ax_radar = plt.subplot(2, 3, 6, projection='polar')
                    ax_radar.plot(angles_plot, values_plot, 'o-', linewidth=2, color='red')
                    ax_radar.fill(angles_plot, values_plot, alpha=0.25, color='red')
                    ax_radar.set_xticks(angles)
                    ax_radar.set_xticklabels(metrics)
                    ax_radar.set_ylim(0, 1)
                    ax_radar.set_title('算法发现有效性', pad=20)
        
        except Exception as e:
            logger.error(f"质量可视化创建失败: {e}")
            fig.text(0.5, 0.5, f'可视化创建失败: {str(e)}', 
                    ha='center', va='center', fontsize=12)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"质量分析可视化已保存到: {filepath}")
        return filepath
    
    def create_clustering_visualizations(self, clustering_results: Dict[str, Any], 
                                       filename: str = 'clustering_analysis.png') -> str:
        """
        创建聚类分析可视化图表
        
        Args:
            clustering_results: 聚类分析结果
            filename: 输出文件名
            
        Returns:
            保存的文件路径
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('请求聚类分析', fontsize=16, fontweight='bold')
        
        try:
            detailed_results = clustering_results.get('detailed_results', {})
            
            # 1. 聚类大小分布
            if 'cluster_descriptions' in clustering_results:
                cluster_desc = clustering_results['cluster_descriptions']
                cluster_ids = list(cluster_desc.keys())
                cluster_sizes = [cluster_desc[cid]['size'] for cid in cluster_ids]
                
                axes[0, 0].bar(range(len(cluster_ids)), cluster_sizes, 
                             color='lightblue', alpha=0.7)
                axes[0, 0].set_title('各聚类规模分布')
                axes[0, 0].set_xlabel('聚类ID')
                axes[0, 0].set_ylabel('请求数量')
                axes[0, 0].set_xticks(range(len(cluster_ids)))
                axes[0, 0].set_xticklabels([f'聚类{cid}' for cid in cluster_ids])
            
            # 2. 聚类适用性评分
            if 'cluster_descriptions' in clustering_results:
                suitability_scores = [cluster_desc[cid]['suitability_score'] 
                                    for cid in cluster_ids]
                
                colors = ['green' if score >= 0.7 else 'orange' if score >= 0.4 else 'red' 
                         for score in suitability_scores]
                
                axes[0, 1].bar(range(len(cluster_ids)), suitability_scores, 
                             color=colors, alpha=0.7)
                axes[0, 1].set_title('各聚类算法适用性评分')
                axes[0, 1].set_xlabel('聚类ID')
                axes[0, 1].set_ylabel('适用性评分')
                axes[0, 1].set_ylim(0, 1)
                axes[0, 1].set_xticks(range(len(cluster_ids)))
                axes[0, 1].set_xticklabels([f'聚类{cid}' for cid in cluster_ids])
            
            # 3. 聚类特征雷达图
            if detailed_results and 'cluster_characteristics' in detailed_results:
                cluster_chars = detailed_results['cluster_characteristics']
                
                # 选择第一个聚类作为示例
                for cluster_id in list(cluster_chars.keys())[:1]:
                    if isinstance(cluster_id, int) and 'feature_means' in cluster_chars[cluster_id]:
                        features = cluster_chars[cluster_id]['feature_means']
                        
                        # 选择关键特征
                        key_features = ['avg_loss', 'avg_time', 'avg_length', 'path_count']
                        available_features = [f for f in key_features if f in features]
                        
                        if len(available_features) >= 3:
                            values = [features[f] for f in available_features]
                            # 标准化值到0-1范围
                            max_val = max(values) if max(values) > 0 else 1
                            values_norm = [v / max_val for v in values]
                            
                            angles = np.linspace(0, 2*np.pi, len(available_features), endpoint=False)
                            values_plot = values_norm + [values_norm[0]]
                            angles_plot = np.concatenate([angles, [angles[0]]])
                            
                            ax_radar = plt.subplot(2, 2, 3, projection='polar')
                            ax_radar.plot(angles_plot, values_plot, 'o-', linewidth=2)
                            ax_radar.fill(angles_plot, values_plot, alpha=0.25)
                            ax_radar.set_xticks(angles)
                            ax_radar.set_xticklabels(available_features)
                            ax_radar.set_ylim(0, 1)
                            ax_radar.set_title(f'聚类{cluster_id}特征分布')
            
            # 4. 聚类质量评估
            if 'clustering_quality' in clustering_results:
                quality_data = clustering_results['clustering_quality']
                silhouette_score = quality_data.get('silhouette_score', 0)
                
                # 创建质量评估条形图
                metrics = ['轮廓系数']
                values = [silhouette_score]
                
                colors = ['green' if silhouette_score > 0.5 else 'orange' if silhouette_score > 0.2 else 'red']
                
                axes[1, 1].bar(metrics, values, color=colors, alpha=0.7)
                axes[1, 1].set_title('聚类质量评估')
                axes[1, 1].set_ylabel('评分')
                axes[1, 1].set_ylim(-1, 1)
                
                # 添加评分解释
                if silhouette_score > 0.5:
                    quality_text = '优秀'
                elif silhouette_score > 0.2:
                    quality_text = '良好'
                else:
                    quality_text = '需改进'
                
                axes[1, 1].text(0, silhouette_score + 0.1, f'{quality_text}\n({silhouette_score:.3f})', 
                               ha='center', va='bottom')
        
        except Exception as e:
            logger.error(f"聚类可视化创建失败: {e}")
            fig.text(0.5, 0.5, f'可视化创建失败: {str(e)}', 
                    ha='center', va='center', fontsize=12)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"聚类分析可视化已保存到: {filepath}")
        return filepath
    
    def create_pruning_visualizations(self, pruning_results: Dict[str, Any], 
                                    filename: str = 'pruning_analysis.png') -> str:
        """
        创建剪枝策略可视化图表
        
        Args:
            pruning_results: 剪枝分析结果
            filename: 输出文件名
            
        Returns:
            保存的文件路径
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('剪枝策略分析', fontsize=16, fontweight='bold')
        
        try:
            # 1. 预期收益分析
            if 'expected_benefits' in pruning_results:
                benefits = pruning_results['expected_benefits']
                
                metrics = ['计算节省', '质量保持', 'ROI评估']
                values = [
                    float(benefits.get('computational_savings', '0%').rstrip('%')) / 100,
                    float(benefits.get('quality_retention', '0%').rstrip('%')) / 100,
                    0.8 if benefits.get('roi_assessment') == 'excellent' else 
                    0.6 if benefits.get('roi_assessment') == 'good' else 
                    0.4 if benefits.get('roi_assessment') == 'fair' else 0.2
                ]
                
                colors = ['green', 'blue', 'purple']
                bars = axes[0, 0].bar(metrics, values, color=colors, alpha=0.7)
                axes[0, 0].set_title('剪枝策略预期收益')
                axes[0, 0].set_ylabel('收益比例')
                axes[0, 0].set_ylim(0, 1)
                
                # 添加数值标签
                for bar, value in zip(bars, values):
                    axes[0, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                                   f'{value:.1%}', ha='center', va='bottom')
            
            # 2. 实施优先级
            if 'implementation_priority' in pruning_results:
                priorities = pruning_results['implementation_priority']
                
                strategies = [p['strategy'] for p in priorities]
                efforts = [p['effort'] for p in priorities]
                benefits = [p['benefit'] for p in priorities]
                
                # 创建散点图：努力vs收益
                effort_map = {'low': 1, 'medium': 2, 'high': 3}
                benefit_map = {'low': 1, 'medium': 2, 'high': 3}
                
                x_values = [effort_map.get(effort, 2) for effort in efforts]
                y_values = [benefit_map.get(benefit, 2) for benefit in benefits]
                
                scatter = axes[0, 1].scatter(x_values, y_values, s=100, alpha=0.7, c=range(len(strategies)))
                axes[0, 1].set_title('实施优先级矩阵')
                axes[0, 1].set_xlabel('实施难度')
                axes[0, 1].set_ylabel('预期收益')
                axes[0, 1].set_xticks([1, 2, 3])
                axes[0, 1].set_xticklabels(['低', '中', '高'])
                axes[0, 1].set_yticks([1, 2, 3])
                axes[0, 1].set_yticklabels(['低', '中', '高'])
                
                # 添加策略标签
                for i, strategy in enumerate(strategies):
                    axes[0, 1].annotate(strategy[:6], (x_values[i], y_values[i]), 
                                       xytext=(5, 5), textcoords='offset points', fontsize=8)
            
            # 3. 关键建议重要性
            if 'key_recommendations' in pruning_results:
                recommendations = pruning_results['key_recommendations']
                
                # 创建词云风格的重要性展示（简化版）
                importance_scores = [len(rec) / 100 for rec in recommendations]  # 基于长度的简单评分
                
                y_positions = range(len(recommendations))
                bars = axes[1, 0].barh(y_positions, importance_scores, alpha=0.7, color='orange')
                axes[1, 0].set_title('关键建议重要性')
                axes[1, 0].set_xlabel('重要性评分')
                axes[1, 0].set_yticks(y_positions)
                axes[1, 0].set_yticklabels([rec[:20] + '...' if len(rec) > 20 else rec 
                                          for rec in recommendations])
            
            # 4. 风险评估仪表盘
            if 'risk_assessment' in pruning_results:
                risk_level = pruning_results['risk_assessment']
                
                # 创建风险等级仪表盘
                risk_map = {'low': 0.2, 'medium': 0.5, 'high': 0.8}
                risk_value = risk_map.get(risk_level, 0.5)
                
                theta = np.linspace(0, np.pi, 100)  # 半圆
                r = np.ones_like(theta)
                
                ax_gauge = plt.subplot(2, 2, 4, projection='polar')
                ax_gauge.fill_between(theta, 0, r, alpha=0.3, color='lightgray')
                
                # 根据风险等级着色
                if risk_level == 'low':
                    color = 'green'
                elif risk_level == 'medium':
                    color = 'orange'
                else:
                    color = 'red'
                
                risk_theta = np.linspace(0, np.pi * risk_value, 50)
                ax_gauge.fill_between(risk_theta, 0, r[:len(risk_theta)], alpha=0.7, color=color)
                
                ax_gauge.set_ylim(0, 1)
                ax_gauge.set_title(f'风险评估: {risk_level.upper()}', pad=20)
                ax_gauge.set_theta_zero_location('W')
                ax_gauge.set_theta_direction(1)
                ax_gauge.set_thetagrids([0, 45, 90, 135, 180], ['低', '', '中', '', '高'])
        
        except Exception as e:
            logger.error(f"剪枝可视化创建失败: {e}")
            fig.text(0.5, 0.5, f'可视化创建失败: {str(e)}', 
                    ha='center', va='center', fontsize=12)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"剪枝分析可视化已保存到: {filepath}")
        return filepath
    
    def create_comprehensive_dashboard(self, all_results: Dict[str, Any], 
                                     filename: str = 'comprehensive_dashboard.png') -> str:
        """
        创建综合分析仪表盘
        
        Args:
            all_results: 所有分析结果
            filename: 输出文件名
            
        Returns:
            保存的文件路径
        """
        fig = plt.figure(figsize=(20, 16))
        fig.suptitle('全排列路径算法综合分析仪表盘', fontsize=20, fontweight='bold')
        
        try:
            # 创建网格布局
            gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
            
            # 1. 总体概览 (1x2)
            ax1 = fig.add_subplot(gs[0, :2])
            self._create_overview_section(ax1, all_results)
            
            # 2. 数据质量评估 (1x1)
            ax2 = fig.add_subplot(gs[0, 2])
            self._create_data_quality_gauge(ax2, all_results.get('statistics', {}))
            
            # 3. 算法效果评估 (1x1)
            ax3 = fig.add_subplot(gs[0, 3])
            self._create_algorithm_effectiveness_gauge(ax3, all_results.get('quality', {}))
            
            # 4. 请求类型分布 (1x2)
            ax4 = fig.add_subplot(gs[1, :2])
            self._create_request_type_distribution(ax4, all_results.get('clustering', {}))
            
            # 5. 优化潜力分析 (1x2)
            ax5 = fig.add_subplot(gs[1, 2:])
            self._create_optimization_potential(ax5, all_results.get('pruning', {}))
            
            # 6. 关键指标趋势 (1x4)
            ax6 = fig.add_subplot(gs[2, :])
            self._create_key_metrics_trend(ax6, all_results)
        
        except Exception as e:
            logger.error(f"综合仪表盘创建失败: {e}")
            fig.text(0.5, 0.5, f'仪表盘创建失败: {str(e)}', 
                    ha='center', va='center', fontsize=16)
        
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"综合分析仪表盘已保存到: {filepath}")
        return filepath
    
    def _create_overview_section(self, ax, all_results: Dict[str, Any]):
        """创建总体概览部分"""
        ax.axis('off')
        
        # 提取关键信息
        stats_info = all_results.get('statistics', {})
        basic_info = stats_info.get('basic_info', {})
        
        overview_text = f"""
        📊 数据概览
        • 总请求数: {basic_info.get('总请求数', 'N/A')}
        • 总路径数: {basic_info.get('总路径数', 'N/A')}
        • 平均每请求路径数: {basic_info.get('平均每请求路径数', 'N/A')}
        
        🎯 关键发现
        """
        
        # 添加关键发现
        key_findings = stats_info.get('key_findings', [])
        for finding in key_findings[:3]:
            overview_text += f"\n        • {finding}"
        
        ax.text(0.05, 0.95, overview_text, transform=ax.transAxes, 
               fontsize=12, verticalalignment='top', fontfamily='monospace')
    
    def _create_data_quality_gauge(self, ax, statistics_results: Dict[str, Any]):
        """创建数据质量仪表盘"""
        quality_score = statistics_results.get('data_quality_score', 0.5)
        
        # 创建环形仪表盘
        theta = np.linspace(0, 2*np.pi, 100)
        r_outer = 1
        r_inner = 0.7
        
        # 背景环
        ax.fill_between(theta, r_inner, r_outer, alpha=0.3, color='lightgray')
        
        # 质量环
        quality_theta = np.linspace(0, 2*np.pi * quality_score, int(100 * quality_score))
        color = 'green' if quality_score > 0.8 else 'orange' if quality_score > 0.6 else 'red'
        ax.fill_between(quality_theta, r_inner, r_outer, alpha=0.8, color=color)
        
        # 中心文本
        ax.text(0, 0, f'{quality_score:.1%}\n数据质量', ha='center', va='center', 
               fontsize=14, fontweight='bold')
        
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title('数据质量评估', fontweight='bold')
    
    def _create_algorithm_effectiveness_gauge(self, ax, quality_results: Dict[str, Any]):
        """创建算法效果仪表盘"""
        effectiveness_grade = quality_results.get('algorithm_effectiveness_grade', 'Fair')
        
        # 等级映射
        grade_map = {'Excellent': 0.9, 'Good': 0.7, 'Fair': 0.5, 'Poor': 0.3}
        effectiveness_score = grade_map.get(effectiveness_grade, 0.5)
        
        # 创建条形仪表盘
        categories = ['差', '一般', '良好', '优秀']
        values = [0.25, 0.5, 0.75, 1.0]
        colors = ['red', 'orange', 'yellow', 'green']
        
        bars = ax.barh(categories, values, alpha=0.3, color=colors)
        
        # 当前等级高亮
        current_index = min(3, int(effectiveness_score * 4))
        bars[current_index].set_alpha(0.8)
        
        ax.set_xlim(0, 1)
        ax.set_title('算法有效性评估', fontweight='bold')
        ax.text(effectiveness_score, current_index, effectiveness_grade, 
               ha='center', va='center', fontweight='bold', color='white')
    
    def _create_request_type_distribution(self, ax, clustering_results: Dict[str, Any]):
        """创建请求类型分布图"""
        if 'cluster_descriptions' in clustering_results:
            cluster_desc = clustering_results['cluster_descriptions']
            
            labels = [f"类型{cid}\n({data['description']})" 
                     for cid, data in cluster_desc.items()]
            sizes = [data['size'] for data in cluster_desc.values()]
            
            # 创建饼图
            colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                            colors=colors, startangle=90)
            
            ax.set_title('请求类型分布', fontweight='bold')
        else:
            ax.text(0.5, 0.5, '暂无聚类数据', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
            ax.set_title('请求类型分布', fontweight='bold')
    
    def _create_optimization_potential(self, ax, pruning_results: Dict[str, Any]):
        """创建优化潜力分析图"""
        if 'implementation_priority' in pruning_results:
            priorities = pruning_results['implementation_priority']
            
            strategies = [p['strategy'] for p in priorities]
            timelines = [p['timeline'] for p in priorities]
            benefits = [p['benefit'] for p in priorities]
            
            # 创建甘特图风格的优化路线图
            y_pos = np.arange(len(strategies))
            
            # 时间线映射（简化处理）
            timeline_map = {'1周': 1, '1-2周': 1.5, '2-3周': 2.5, '3-4周': 3.5}
            durations = [timeline_map.get(timeline, 2) for timeline in timelines]
            
            # 收益颜色映射
            benefit_colors = {'high': 'green', 'medium': 'orange', 'low': 'red'}
            colors = [benefit_colors.get(benefit, 'gray') for benefit in benefits]
            
            bars = ax.barh(y_pos, durations, color=colors, alpha=0.7)
            
            ax.set_yticks(y_pos)
            ax.set_yticklabels(strategies)
            ax.set_xlabel('预计实施时间(周)')
            ax.set_title('优化策略实施路线图', fontweight='bold')
            
            # 添加图例
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor='green', alpha=0.7, label='高收益'),
                             Patch(facecolor='orange', alpha=0.7, label='中收益'),
                             Patch(facecolor='red', alpha=0.7, label='低收益')]
            ax.legend(handles=legend_elements, loc='lower right')
        else:
            ax.text(0.5, 0.5, '暂无剪枝数据', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
            ax.set_title('优化潜力分析', fontweight='bold')
    
    def _create_key_metrics_trend(self, ax, all_results: Dict[str, Any]):
        """创建关键指标趋势图"""
        # 模拟趋势数据（实际应用中应该从历史数据获取）
        metrics = ['计算效率', '解质量', '算法稳定性', '资源利用率']
        
        # 基于分析结果生成模拟趋势
        baseline = [0.6, 0.7, 0.8, 0.5]  # 基线值
        
        # 根据分析结果调整趋势
        stats_quality = all_results.get('statistics', {}).get('data_quality_score', 0.7)
        quality_grade = all_results.get('quality', {}).get('algorithm_effectiveness_grade', 'Fair')
        
        grade_multiplier = {'Excellent': 1.2, 'Good': 1.1, 'Fair': 1.0, 'Poor': 0.9}
        multiplier = grade_multiplier.get(quality_grade, 1.0)
        
        current_values = [b * multiplier * stats_quality for b in baseline]
        
        # 创建雷达图
        angles = np.linspace(0, 2*np.pi, len(metrics), endpoint=False)
        current_values += [current_values[0]]  # 闭合图形
        angles = np.concatenate([angles, [angles[0]]])
        
        ax.plot(angles, current_values, 'o-', linewidth=2, label='当前状态', color='blue')
        ax.fill(angles, current_values, alpha=0.25, color='blue')
        
        # 预期改进后的值
        improved_values = [min(1.0, v * 1.3) for v in current_values[:-1]] + [current_values[0]]
        ax.plot(angles, improved_values, 'o--', linewidth=2, label='优化后预期', color='green')
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics)
        ax.set_ylim(0, 1)
        ax.set_title('关键指标对比', fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        ax.grid(True) 