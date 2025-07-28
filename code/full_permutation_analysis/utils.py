"""
工具函数模块

包含数据处理和报告生成的通用功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataProcessor:
    """数据处理工具类"""
    
    @staticmethod
    def clean_and_validate_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        清理和验证数据
        
        Args:
            df: 原始数据DataFrame
            
        Returns:
            清理后的DataFrame
        """
        logger.info("开始数据清理和验证...")
        
        # 复制数据避免修改原始数据
        cleaned_df = df.copy()
        
        # 数据类型转换
        if 'path_duration' in cleaned_df.columns:
            # 处理带逗号的数字字符串
            cleaned_df['path_duration'] = cleaned_df['path_duration'].astype(str).str.replace(',', '').astype(float)
        
        if 'path_sale_loss' in cleaned_df.columns:
            cleaned_df['path_sale_loss'] = cleaned_df['path_sale_loss'].astype(float)
        
        if '补货率' in cleaned_df.columns:
            cleaned_df['补货率'] = cleaned_df['补货率'].astype(float)
        
        # 数据验证
        DataProcessor._validate_data_quality(cleaned_df)
        
        logger.info(f"数据清理完成，共处理 {len(cleaned_df)} 条记录")
        return cleaned_df
    
    @staticmethod
    def _validate_data_quality(df: pd.DataFrame) -> None:
        """验证数据质量"""
        # 检查必要列是否存在
        required_columns = ['req_id', 'path', 'path_duration', 'path_sale_loss']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"缺少必要列: {missing_columns}")
        
        # 检查空值
        null_counts = df.isnull().sum()
        if null_counts.any():
            logger.warning(f"发现空值: {null_counts[null_counts > 0].to_dict()}")
        
        # 检查数据范围
        if 'path_duration' in df.columns:
            if (df['path_duration'] < 0).any():
                logger.warning("发现负数路径时长")
        
        if 'path_sale_loss' in df.columns:
            if (df['path_sale_loss'] < 0).any():
                logger.warning("发现负数销量损失")
    
    @staticmethod
    def calculate_path_length(path: str) -> int:
        """
        计算路径长度（点位数量）
        
        Args:
            path: 路径字符串，如 "113_143_107_103"
            
        Returns:
            路径长度
        """
        if pd.isna(path) or path == '':
            return 0
        return len(str(path).split('_'))
    
    @staticmethod
    def extract_path_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        提取路径特征
        
        Args:
            df: 包含路径数据的DataFrame
            
        Returns:
            添加了特征列的DataFrame
        """
        result_df = df.copy()
        
        # 计算路径长度
        result_df['path_length'] = result_df['path'].apply(DataProcessor.calculate_path_length)
        
        # 计算路径复杂度（点位数量的平方，模拟组合复杂度）
        result_df['path_complexity'] = result_df['path_length'] ** 2
        
        # 计算平均每点位时间
        result_df['time_per_point'] = result_df['path_duration'] / result_df['path_length']
        result_df['time_per_point'] = result_df['time_per_point'].fillna(0)
        
        # 计算平均每点位损失
        result_df['loss_per_point'] = result_df['path_sale_loss'] / result_df['path_length']
        result_df['loss_per_point'] = result_df['loss_per_point'].fillna(0)
        
        return result_df
    
    @staticmethod
    def get_descriptive_statistics(series: pd.Series, percentiles: List[float] = None) -> Dict[str, float]:
        """
        获取描述性统计信息
        
        Args:
            series: 数据序列
            percentiles: 分位数列表，默认为[0.25, 0.5, 0.75]
            
        Returns:
            统计信息字典
        """
        if percentiles is None:
            percentiles = [0.25, 0.5, 0.75]
        
        stats = {
            'count': len(series),
            'mean': series.mean(),
            'std': series.std(),
            'min': series.min(),
            'max': series.max(),
            'range': series.max() - series.min(),
            'cv': series.std() / series.mean() if series.mean() != 0 else 0,  # 变异系数
        }
        
        # 添加分位数
        for p in percentiles:
            stats[f'p{int(p*100)}'] = series.quantile(p)
        
        # 添加偏度和峰度
        try:
            from scipy import stats as scipy_stats
            import warnings
            
            # 检查数据变异性，避免数值精度问题
            clean_series = series.dropna()
            if len(clean_series) > 1 and clean_series.std() > 1e-10:
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=RuntimeWarning, 
                                          message='Precision loss occurred in moment calculation')
                    stats['skewness'] = scipy_stats.skew(clean_series)
                    stats['kurtosis'] = scipy_stats.kurtosis(clean_series)
            else:
                # 数据几乎没有变异性，设置默认值
                stats['skewness'] = 0.0
                stats['kurtosis'] = 0.0
        except ImportError:
            logger.warning("scipy未安装，跳过偏度和峰度计算")
        except Exception as e:
            logger.warning(f"计算偏度和峰度时出错: {e}")
            stats['skewness'] = 0.0
            stats['kurtosis'] = 0.0
        
        return stats


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = 'output'):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self.reports_dir = os.path.join(output_dir, 'reports')
        self.data_dir = os.path.join(output_dir, 'data')
        self.viz_dir = os.path.join(output_dir, 'visualizations')
        
        # 创建目录
        for dir_path in [self.output_dir, self.reports_dir, self.data_dir, self.viz_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def save_statistics_report(self, analysis_results: Dict[str, Any], filename: str = None) -> str:
        """
        保存统计分析报告
        
        Args:
            analysis_results: 分析结果字典
            filename: 文件名，如果为None则自动生成
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"statistics_report_{timestamp}.md"
        
        filepath = os.path.join(self.reports_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# 全排列路径算法统计分析报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 基础信息
            if 'basic_info' in analysis_results:
                f.write("## 基础信息\n\n")
                basic_info = analysis_results['basic_info']
                for key, value in basic_info.items():
                    f.write(f"- **{key}**: {value}\n")
                f.write("\n")
            
            # 单请求统计
            if 'single_request_stats' in analysis_results:
                f.write("## 单请求统计分析\n\n")
                self._write_single_request_stats(f, analysis_results['single_request_stats'])
            
            # 全局统计
            if 'global_stats' in analysis_results:
                f.write("## 全局统计分析\n\n")
                self._write_global_stats(f, analysis_results['global_stats'])
        
        logger.info(f"统计分析报告已保存到: {filepath}")
        return filepath
    
    def _write_single_request_stats(self, file_handle, stats_data: Dict) -> None:
        """写入单请求统计信息"""
        file_handle.write("### 各请求统计概览\n\n")
        
        if 'summary_table' in stats_data:
            file_handle.write("| 请求ID | 路径数量 | 平均损失 | 平均时间(分钟) | 平均补货率 |\n")
            file_handle.write("|--------|----------|----------|----------------|------------|\n")
            
            for req_id, data in stats_data['summary_table'].items():
                file_handle.write(f"| {req_id} | {data.get('path_count', 'N/A')} | "
                                f"{data.get('avg_loss', 'N/A'):.2f} | "
                                f"{data.get('avg_time_minutes', 'N/A'):.1f} | "
                                f"{data.get('avg_replenish_rate', 'N/A'):.3f} |\n")
        
        file_handle.write("\n")
    
    def _write_global_stats(self, file_handle, stats_data: Dict) -> None:
        """写入全局统计信息"""
        file_handle.write("### 全局指标统计\n\n")
        
        for metric_name, metric_stats in stats_data.items():
            if isinstance(metric_stats, dict):
                file_handle.write(f"#### {metric_name}\n\n")
                file_handle.write("| 统计量 | 数值 |\n")
                file_handle.write("|--------|------|\n")
                
                for stat_name, stat_value in metric_stats.items():
                    if isinstance(stat_value, (int, float)):
                        file_handle.write(f"| {stat_name} | {stat_value:.3f} |\n")
                    else:
                        file_handle.write(f"| {stat_name} | {stat_value} |\n")
                
                file_handle.write("\n")
    
    def save_json_data(self, data: Dict[str, Any], filename: str) -> str:
        """
        保存JSON格式数据
        
        Args:
            data: 要保存的数据
            filename: 文件名
            
        Returns:
            保存的文件路径
        """
        filepath = os.path.join(self.data_dir, filename)
        
        # 处理numpy数据类型
        def convert_numpy_types(obj):
            import pandas as pd
            
            if isinstance(obj, (np.integer, pd.Int64Dtype, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, pd.Float64Dtype, np.float64)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (pd.Series, pd.Index)):
                return obj.tolist()
            elif isinstance(obj, pd.DataFrame):
                return obj.to_dict('records')
            elif hasattr(obj, 'item'):  # 处理pandas标量类型
                return obj.item()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            else:
                return obj
        
        converted_data = convert_numpy_types(data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON数据已保存到: {filepath}")
        return filepath
    
    def save_csv_data(self, df: pd.DataFrame, filename: str) -> str:
        """
        保存CSV格式数据
        
        Args:
            df: DataFrame数据
            filename: 文件名
            
        Returns:
            保存的文件路径
        """
        filepath = os.path.join(self.data_dir, filename)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"CSV数据已保存到: {filepath}")
        return filepath
    
    def generate_comprehensive_report(self, all_results: Dict[str, Any]) -> str:
        """
        生成综合分析报告
        
        Args:
            all_results: 所有分析结果
            
        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_analysis_report_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# 全排列路径算法有效性综合分析报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 执行摘要
            f.write("## 执行摘要\n\n")
            if 'summary' in all_results:
                for key, value in all_results['summary'].items():
                    f.write(f"- **{key}**: {value}\n")
            f.write("\n")
            
            # 各部分分析结果
            sections = [
                ('statistics', '统计分析结果'),
                ('quality', '解质量分析结果'),
                ('clustering', '请求分类分析结果'),
                ('pruning', '剪枝策略建议')
            ]
            
            for section_key, section_title in sections:
                if section_key in all_results:
                    f.write(f"## {section_title}\n\n")
                    f.write(f"详细结果请参见: `reports/{section_key}_report.md`\n\n")
        
        logger.info(f"综合分析报告已保存到: {filepath}")
        return filepath 