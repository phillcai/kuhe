"""
主分析器模块

整合所有分析功能的核心类
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging
import os
from datetime import datetime

from .stats_analyzer import StatisticsAnalyzer
from .quality import QualityAnalyzer
from .clustering import RequestClusteringAnalyzer
from .pruning import PruningStrategyAnalyzer
from .visualization import VisualizationManager
from .utils import DataProcessor, ReportGenerator

logger = logging.getLogger(__name__)


class FullPermutationAnalyzer:
    """全排列路径算法有效性分析器"""
    
    def __init__(self, df: pd.DataFrame, output_dir: str = 'output'):
        """
        初始化全排列分析器
        
        Args:
            df: 包含路径数据的DataFrame
            output_dir: 输出目录
        """
        self.df = DataProcessor.clean_and_validate_data(df)
        self.output_dir = output_dir
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 初始化各个分析器
        self.statistics_analyzer = StatisticsAnalyzer(self.df)
        self.quality_analyzer = QualityAnalyzer(self.df)
        self.clustering_analyzer = RequestClusteringAnalyzer(self.df)
        self.pruning_analyzer = PruningStrategyAnalyzer(self.df)
        
        # 初始化可视化和报告生成器
        self.visualization_manager = VisualizationManager(
            os.path.join(output_dir, 'visualizations')
        )
        self.report_generator = ReportGenerator(output_dir)
        
        # 存储分析结果
        self.analysis_results = {}
        
        logger.info(f"全排列分析器初始化完成，数据规模: {len(self.df)}条路径")
    
    def run_full_analysis(self, save_results: bool = True) -> Dict[str, Any]:
        """
        运行完整分析
        
        Args:
            save_results: 是否保存分析结果
            
        Returns:
            完整分析结果
        """
        logger.info("开始执行全排列路径算法有效性分析...")
        
        start_time = datetime.now()
        
        try:
            # 第一层：基础统计分析
            logger.info("执行第一层：基础统计分析...")
            self.analysis_results['statistics'] = self.statistics_analyzer.get_analysis_summary()
            
            # 第二层：解质量分析
            logger.info("执行第二层：解质量分析...")
            self.analysis_results['quality'] = self.quality_analyzer.get_quality_analysis_summary()
            
            # 第三层：请求分类分析
            logger.info("执行第三层：请求分类分析...")
            self.analysis_results['clustering'] = self.clustering_analyzer.get_clustering_analysis_summary()
            
            # 第四层：剪枝策略建议
            logger.info("执行第四层：剪枝策略分析...")
            self.analysis_results['pruning'] = self.pruning_analyzer.get_pruning_analysis_summary()
            
            # 生成综合摘要
            self.analysis_results['summary'] = self._generate_comprehensive_summary()
            
            # 保存结果
            if save_results:
                self._save_analysis_results()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"全排列分析完成，耗时: {duration:.2f}秒")
            
            return self.analysis_results
            
        except Exception as e:
            logger.error(f"分析过程中发生错误: {e}")
            raise
    
    def run_statistics_analysis(self) -> Dict[str, Any]:
        """
        运行统计分析（第一层）
        
        Returns:
            统计分析结果
        """
        logger.info("执行基础统计分析...")
        return self.statistics_analyzer.get_analysis_summary()
    
    def run_quality_analysis(self) -> Dict[str, Any]:
        """
        运行解质量分析（第二层）
        
        Returns:
            解质量分析结果
        """
        logger.info("执行解质量分析...")
        return self.quality_analyzer.get_quality_analysis_summary()
    
    def run_clustering_analysis(self) -> Dict[str, Any]:
        """
        运行请求分类分析（第三层）
        
        Returns:
            请求分类分析结果
        """
        logger.info("执行请求分类分析...")
        return self.clustering_analyzer.get_clustering_analysis_summary()
    
    def run_pruning_analysis(self) -> Dict[str, Any]:
        """
        运行剪枝策略分析（第四层）
        
        Returns:
            剪枝策略分析结果
        """
        logger.info("执行剪枝策略分析...")
        return self.pruning_analyzer.get_pruning_analysis_summary()
    
    def create_visualizations(self, results: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        创建可视化图表
        
        Args:
            results: 分析结果，如果为None则使用已存储的结果
            
        Returns:
            生成的图表文件路径字典
        """
        if results is None:
            results = self.analysis_results
        
        if not results:
            logger.warning("没有可用的分析结果，请先运行分析")
            return {}
        
        logger.info("开始生成可视化图表...")
        
        visualization_files = {}
        
        try:
            # 统计分析可视化
            if 'statistics' in results:
                filepath = self.visualization_manager.create_statistics_visualizations(
                    results['statistics']
                )
                visualization_files['statistics'] = filepath
            
            # 解质量分析可视化
            if 'quality' in results:
                filepath = self.visualization_manager.create_quality_visualizations(
                    results['quality']
                )
                visualization_files['quality'] = filepath
            
            # 聚类分析可视化
            if 'clustering' in results:
                filepath = self.visualization_manager.create_clustering_visualizations(
                    results['clustering']
                )
                visualization_files['clustering'] = filepath
            
            # 剪枝策略可视化
            if 'pruning' in results:
                filepath = self.visualization_manager.create_pruning_visualizations(
                    results['pruning']
                )
                visualization_files['pruning'] = filepath
            
            # 综合仪表盘
            filepath = self.visualization_manager.create_comprehensive_dashboard(results)
            visualization_files['dashboard'] = filepath
            
            logger.info(f"可视化图表生成完成，共{len(visualization_files)}个文件")
            
        except Exception as e:
            logger.error(f"可视化生成过程中发生错误: {e}")
        
        return visualization_files
    
    def generate_reports(self, results: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        生成分析报告
        
        Args:
            results: 分析结果，如果为None则使用已存储的结果
            
        Returns:
            生成的报告文件路径字典
        """
        if results is None:
            results = self.analysis_results
        
        if not results:
            logger.warning("没有可用的分析结果，请先运行分析")
            return {}
        
        logger.info("开始生成分析报告...")
        
        report_files = {}
        
        try:
            # 统计分析报告
            if 'statistics' in results:
                filepath = self.report_generator.save_statistics_report(
                    results['statistics'], 'basic_statistics_report.md'
                )
                report_files['statistics'] = filepath
            
            # 保存详细数据
            filepath = self.report_generator.save_json_data(
                results, 'complete_analysis_results.json'
            )
            report_files['json_data'] = filepath
            
            # 保存处理后的数据
            filepath = self.report_generator.save_csv_data(
                self.df, 'analyzed_path_data.csv'
            )
            report_files['csv_data'] = filepath
            
            # 综合报告
            filepath = self.report_generator.generate_comprehensive_report(results)
            report_files['comprehensive'] = filepath
            
            logger.info(f"分析报告生成完成，共{len(report_files)}个文件")
            
        except Exception as e:
            logger.error(f"报告生成过程中发生错误: {e}")
        
        return report_files
    
    def _generate_comprehensive_summary(self) -> Dict[str, Any]:
        """
        生成综合分析摘要
        
        Returns:
            综合摘要
        """
        summary = {
            'analysis_timestamp': datetime.now().isoformat(),
            'data_overview': {},
            'key_findings': [],
            'recommendations': [],
            'overall_assessment': {},
            'next_steps': []
        }
        
        # 数据概览
        if 'statistics' in self.analysis_results:
            stats = self.analysis_results['statistics']
            summary['data_overview'] = stats.get('basic_info', {})
        
        # 关键发现汇总
        key_findings = []
        
        # 从各层分析中提取关键发现
        if 'statistics' in self.analysis_results:
            key_findings.extend(self.analysis_results['statistics'].get('key_findings', []))
        
        if 'quality' in self.analysis_results:
            key_findings.extend(self.analysis_results['quality'].get('key_findings', []))
        
        if 'clustering' in self.analysis_results:
            key_findings.extend(self.analysis_results['clustering'].get('key_findings', []))
        
        summary['key_findings'] = key_findings[:10]  # 限制为前10个关键发现
        
        # 生成建议
        recommendations = []
        
        # 基于数据质量的建议
        if 'statistics' in self.analysis_results:
            data_quality = self.analysis_results['statistics'].get('data_quality_score', 0)
            if data_quality < 0.7:
                recommendations.append("建议改善数据质量，提高分析结果的可靠性")
        
        # 基于算法效果的建议
        if 'quality' in self.analysis_results:
            effectiveness = self.analysis_results['quality'].get('algorithm_effectiveness_grade', 'Fair')
            if effectiveness in ['Poor', 'Fair']:
                recommendations.append("当前算法效果有限，建议考虑优化或替代方案")
            elif effectiveness == 'Good':
                recommendations.append("算法效果良好，可进一步优化以提升性能")
            else:
                recommendations.append("算法效果优秀，建议维持现有策略并持续监控")
        
        # 基于聚类分析的建议
        if 'clustering' in self.analysis_results:
            cluster_count = self.analysis_results['clustering'].get('cluster_count', 0)
            if cluster_count > 1:
                recommendations.append(f"识别出{cluster_count}种请求类型，建议采用差异化处理策略")
        
        # 基于剪枝分析的建议
        if 'pruning' in self.analysis_results:
            pruning_recs = self.analysis_results['pruning'].get('key_recommendations', [])
            recommendations.extend(pruning_recs[:3])  # 添加前3个剪枝建议
        
        summary['recommendations'] = recommendations
        
        # 整体评估
        summary['overall_assessment'] = self._generate_overall_assessment()
        
        # 下一步行动
        summary['next_steps'] = self._generate_next_steps()
        
        return summary
    
    def _generate_overall_assessment(self) -> Dict[str, Any]:
        """
        生成整体评估
        
        Returns:
            整体评估结果
        """
        assessment = {
            'algorithm_suitability': 'unknown',
            'optimization_priority': 'medium',
            'implementation_readiness': 'partial',
            'risk_level': 'medium',
            'expected_roi': 'moderate'
        }
        
        # 基于各层分析结果评估算法适用性
        suitability_factors = []
        
        if 'quality' in self.analysis_results:
            effectiveness = self.analysis_results['quality'].get('algorithm_effectiveness_grade', 'Fair')
            if effectiveness == 'Excellent':
                suitability_factors.append(1.0)
            elif effectiveness == 'Good':
                suitability_factors.append(0.8)
            elif effectiveness == 'Fair':
                suitability_factors.append(0.6)
            else:
                suitability_factors.append(0.4)
        
        if 'clustering' in self.analysis_results:
            # 如果大多数聚类适合全排列算法
            detailed_results = self.analysis_results['clustering'].get('detailed_results', {})
            if 'algorithm_performance_by_type' in detailed_results:
                performance_data = detailed_results['algorithm_performance_by_type']
                suitable_clusters = 0
                total_clusters = 0
                
                for cluster_id, data in performance_data.items():
                    if isinstance(cluster_id, int):
                        total_clusters += 1
                        suitability = data.get('algorithm_suitability', {}).get('overall_suitability', {}).get('score', 0)
                        if suitability >= 0.6:
                            suitable_clusters += 1
                
                if total_clusters > 0:
                    suitability_ratio = suitable_clusters / total_clusters
                    suitability_factors.append(suitability_ratio)
        
        # 计算综合适用性
        if suitability_factors:
            avg_suitability = np.mean(suitability_factors)
            if avg_suitability >= 0.8:
                assessment['algorithm_suitability'] = 'high'
            elif avg_suitability >= 0.6:
                assessment['algorithm_suitability'] = 'medium'
            else:
                assessment['algorithm_suitability'] = 'low'
        
        # 基于剪枝分析评估优化优先级
        if 'pruning' in self.analysis_results:
            expected_benefits = self.analysis_results['pruning'].get('expected_benefits', {})
            computational_savings = expected_benefits.get('computational_savings', '0%')
            
            savings_value = float(computational_savings.rstrip('%')) / 100 if isinstance(computational_savings, str) else 0
            
            if savings_value >= 0.3:
                assessment['optimization_priority'] = 'high'
            elif savings_value >= 0.15:
                assessment['optimization_priority'] = 'medium'
            else:
                assessment['optimization_priority'] = 'low'
        
        # 评估实施准备度
        if 'pruning' in self.analysis_results:
            implementation_priority = self.analysis_results['pruning'].get('implementation_priority', [])
            quick_wins = [p for p in implementation_priority if p.get('effort') == 'low']
            
            if len(quick_wins) >= 2:
                assessment['implementation_readiness'] = 'high'
            elif len(quick_wins) >= 1:
                assessment['implementation_readiness'] = 'medium'
            else:
                assessment['implementation_readiness'] = 'low'
        
        # 评估风险水平
        if 'pruning' in self.analysis_results:
            risk_level = self.analysis_results['pruning'].get('risk_assessment', 'medium')
            assessment['risk_level'] = risk_level
        
        # 评估预期ROI
        if 'pruning' in self.analysis_results:
            expected_benefits = self.analysis_results['pruning'].get('expected_benefits', {})
            roi_assessment = expected_benefits.get('roi_assessment', 'moderate')
            
            if roi_assessment == 'excellent':
                assessment['expected_roi'] = 'high'
            elif roi_assessment == 'good':
                assessment['expected_roi'] = 'moderate'
            else:
                assessment['expected_roi'] = 'low'
        
        return assessment
    
    def _generate_next_steps(self) -> List[str]:
        """
        生成下一步行动建议
        
        Returns:
            行动建议列表
        """
        next_steps = []
        
        # 基于整体评估生成行动建议
        overall_assessment = self._generate_overall_assessment()
        
        # 基于算法适用性的建议
        suitability = overall_assessment.get('algorithm_suitability', 'unknown')
        if suitability == 'high':
            next_steps.append("继续使用全排列算法，重点进行性能优化")
        elif suitability == 'medium':
            next_steps.append("评估全排列算法的适用场景，考虑混合策略")
        else:
            next_steps.append("考虑替代算法方案，如启发式或近似算法")
        
        # 基于优化优先级的建议
        priority = overall_assessment.get('optimization_priority', 'medium')
        if priority == 'high':
            next_steps.append("立即启动算法优化项目，实施剪枝策略")
        elif priority == 'medium':
            next_steps.append("制定优化计划，分阶段实施改进措施")
        else:
            next_steps.append("维持现状，定期监控算法性能")
        
        # 基于实施准备度的建议
        readiness = overall_assessment.get('implementation_readiness', 'partial')
        if readiness == 'high':
            next_steps.append("可以立即开始实施优化方案")
        elif readiness == 'medium':
            next_steps.append("完善实施方案，准备必要资源")
        else:
            next_steps.append("进行更详细的可行性分析和准备工作")
        
        # 基于风险水平的建议
        risk_level = overall_assessment.get('risk_level', 'medium')
        if risk_level == 'high':
            next_steps.append("制定详细的风险缓解计划")
        elif risk_level == 'medium':
            next_steps.append("建立监控机制，及时识别和应对风险")
        else:
            next_steps.append("保持常规监控，风险可控")
        
        # 通用建议
        next_steps.extend([
            "建立持续监控和评估机制",
            "定期更新分析模型和参数",
            "收集更多历史数据以提高分析准确性"
        ])
        
        return next_steps[:8]  # 限制为前8个建议
    
    def _save_analysis_results(self):
        """保存分析结果"""
        try:
            # 生成可视化图表
            self.create_visualizations()
            
            # 生成分析报告
            self.generate_reports()
            
            logger.info("分析结果保存完成")
            
        except Exception as e:
            logger.error(f"保存分析结果时发生错误: {e}")
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """
        获取分析状态
        
        Returns:
            分析状态信息
        """
        status = {
            'data_loaded': len(self.df) > 0,
            'data_size': len(self.df),
            'analysis_completed': len(self.analysis_results) > 0,
            'available_analyses': list(self.analysis_results.keys()),
            'output_directory': self.output_dir
        }
        
        return status
    
    def print_summary(self):
        """打印分析摘要"""
        if not self.analysis_results:
            print("尚未执行分析，请先调用 run_full_analysis() 方法")
            return
        
        summary = self.analysis_results.get('summary', {})
        
        print("\n" + "="*60)
        print("全排列路径算法有效性分析摘要")
        print("="*60)
        
        # 数据概览
        if 'data_overview' in summary:
            print("\n📊 数据概览:")
            for key, value in summary['data_overview'].items():
                print(f"  • {key}: {value}")
        
        # 关键发现
        if 'key_findings' in summary:
            print("\n🔍 关键发现:")
            for i, finding in enumerate(summary['key_findings'][:5], 1):
                print(f"  {i}. {finding}")
        
        # 核心建议
        if 'recommendations' in summary:
            print("\n💡 核心建议:")
            for i, rec in enumerate(summary['recommendations'][:5], 1):
                print(f"  {i}. {rec}")
        
        # 整体评估
        if 'overall_assessment' in summary:
            print("\n📈 整体评估:")
            assessment = summary['overall_assessment']
            print(f"  • 算法适用性: {assessment.get('algorithm_suitability', 'unknown')}")
            print(f"  • 优化优先级: {assessment.get('optimization_priority', 'medium')}")
            print(f"  • 实施准备度: {assessment.get('implementation_readiness', 'partial')}")
            print(f"  • 风险水平: {assessment.get('risk_level', 'medium')}")
            print(f"  • 预期ROI: {assessment.get('expected_roi', 'moderate')}")
        
        # 下一步行动
        if 'next_steps' in summary:
            print("\n🎯 下一步行动:")
            for i, step in enumerate(summary['next_steps'][:5], 1):
                print(f"  {i}. {step}")
        
        print("\n" + "="*60)
        print(f"详细结果已保存到: {self.output_dir}")
        print("="*60) 