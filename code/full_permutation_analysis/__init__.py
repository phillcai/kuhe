"""
全排列路径算法有效性分析包

包含以下模块：
- analyzer: 核心分析器类
- statistics: 统计分析模块
- quality: 解质量分析模块
- clustering: 请求分类分析模块
- pruning: 剪枝策略模块
- visualization: 可视化模块
- utils: 工具函数模块
"""

from .analyzer import FullPermutationAnalyzer
from .stats_analyzer import StatisticsAnalyzer
from .quality import QualityAnalyzer
from .clustering import RequestClusteringAnalyzer
from .pruning import PruningStrategyAnalyzer
from .visualization import VisualizationManager
from .utils import DataProcessor, ReportGenerator

__version__ = "1.0.0"
__author__ = "智能配送调度系统开发团队"

__all__ = [
    'FullPermutationAnalyzer',
    'StatisticsAnalyzer', 
    'QualityAnalyzer',
    'RequestClusteringAnalyzer',
    'PruningStrategyAnalyzer',
    'VisualizationManager',
    'DataProcessor',
    'ReportGenerator'
] 