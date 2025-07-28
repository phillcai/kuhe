"""
请求分类分析模块

实现第三层请求类型特征分析功能：
- 基于数据特征的请求聚类
- 不同类型请求的算法表现分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import logging
from .utils import DataProcessor

logger = logging.getLogger(__name__)


class RequestClusteringAnalyzer:
    """请求聚类分析器"""
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化请求聚类分析器
        
        Args:
            df: 包含路径数据的DataFrame
        """
        self.df = DataProcessor.clean_and_validate_data(df)
        self.df = DataProcessor.extract_path_features(self.df)
        
        # 计算每个请求的特征
        self.request_features = self._extract_request_features()
        
        logger.info(f"请求聚类分析器初始化完成，共{len(self.request_features)}个请求")
    
    def _extract_request_features(self) -> pd.DataFrame:
        """
        提取每个请求的特征用于聚类
        
        Returns:
            请求特征DataFrame
        """
        features_list = []
        
        for req_id, group in self.df.groupby('req_id'):
            features = {
                'req_id': req_id,
                # 基础统计特征
                'path_count': len(group),
                'avg_loss': group['path_sale_loss'].mean(),
                'std_loss': group['path_sale_loss'].std(),
                'avg_time': group['path_duration'].mean(),
                'std_time': group['path_duration'].std(),
                'avg_length': group['path_length'].mean(),
                'std_length': group['path_length'].std(),
                
                # 分布特征
                'loss_cv': group['path_sale_loss'].std() / group['path_sale_loss'].mean() if group['path_sale_loss'].mean() > 0 else 0,
                'time_cv': group['path_duration'].std() / group['path_duration'].mean() if group['path_duration'].mean() > 0 else 0,
                'loss_skewness': group['path_sale_loss'].skew(),
                'time_skewness': group['path_duration'].skew(),
                
                # 极值特征
                'max_loss': group['path_sale_loss'].max(),
                'min_loss': group['path_sale_loss'].min(),
                'loss_range': group['path_sale_loss'].max() - group['path_sale_loss'].min(),
                'max_time': group['path_duration'].max(),
                'min_time': group['path_duration'].min(),
                'time_range': group['path_duration'].max() - group['path_duration'].min(),
                
                # 效率特征
                'avg_time_per_point': group['time_per_point'].mean(),
                'avg_loss_per_point': group['loss_per_point'].mean(),
                'complexity_score': group['path_complexity'].mean(),
                
                # 质量特征（如果存在评分）
                'avg_score': group['total_score'].mean() if 'total_score' in group.columns else 0,
                'best_score': group['total_score'].max() if 'total_score' in group.columns else 0,
                'score_range': (group['total_score'].max() - group['total_score'].min()) if 'total_score' in group.columns else 0,
                
                # 补货特征
                'avg_replenish_rate': group['补货率'].mean() if '补货率' in group.columns else 1.0
            }
            
            features_list.append(features)
        
        return pd.DataFrame(features_list)
    
    def analyze_request_types(self, n_clusters: int = None) -> Dict[str, Any]:
        """
        分析请求类型
        
        Args:
            n_clusters: 聚类数量，如果为None则自动确定
            
        Returns:
            请求类型分析结果
        """
        logger.info("开始请求类型分析...")
        
        results = {
            'clustering_results': {},
            'cluster_characteristics': {},
            'algorithm_performance_by_type': {},
            'type_recommendations': {}
        }
        
        # 执行聚类分析
        results['clustering_results'] = self._perform_clustering(n_clusters)
        
        # 分析各聚类特征
        results['cluster_characteristics'] = self._analyze_cluster_characteristics(
            results['clustering_results']
        )
        
        # 分析算法在不同类型上的表现
        results['algorithm_performance_by_type'] = self._analyze_performance_by_type(
            results['clustering_results']
        )
        
        # 生成类型化建议
        results['type_recommendations'] = self._generate_type_recommendations(
            results['cluster_characteristics'],
            results['algorithm_performance_by_type']
        )
        
        logger.info("请求类型分析完成")
        return results
    
    def _perform_clustering(self, n_clusters: int = None) -> Dict[str, Any]:
        """
        执行聚类分析
        
        Args:
            n_clusters: 聚类数量
            
        Returns:
            聚类结果
        """
        # 选择用于聚类的特征
        clustering_features = [
            'avg_loss', 'std_loss', 'avg_time', 'std_time', 
            'avg_length', 'path_count', 'loss_cv', 'time_cv',
            'avg_time_per_point', 'avg_loss_per_point'
        ]
        
        # 过滤存在的特征
        available_features = [f for f in clustering_features if f in self.request_features.columns]
        
        if len(available_features) < 3:
            return {'error': '可用于聚类的特征不足'}
        
        # 准备聚类数据
        clustering_data = self.request_features[available_features].fillna(0)
        
        # 数据标准化
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(clustering_data)
        
        # 确定最优聚类数
        if n_clusters is None:
            n_clusters = self._determine_optimal_clusters(scaled_data)
        
        # 执行K-means聚类
        try:
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(scaled_data)
            
            # 添加聚类标签到特征数据
            self.request_features['cluster'] = cluster_labels
            
            # 计算聚类质量指标
            from sklearn.metrics import silhouette_score, calinski_harabasz_score
            silhouette_avg = silhouette_score(scaled_data, cluster_labels)
            calinski_score = calinski_harabasz_score(scaled_data, cluster_labels)
            
            clustering_results = {
                'n_clusters': n_clusters,
                'cluster_labels': cluster_labels.tolist(),
                'cluster_centers': kmeans.cluster_centers_.tolist(),
                'features_used': available_features,
                'silhouette_score': silhouette_avg,
                'calinski_harabasz_score': calinski_score,
                'inertia': kmeans.inertia_,
                'scaler': scaler  # 保存标准化器
            }
            
            return clustering_results
            
        except ImportError:
            logger.warning("sklearn未安装，使用简单的基于规则的分类")
            return self._rule_based_classification()
    
    def _determine_optimal_clusters(self, data: np.ndarray, max_clusters: int = 8) -> int:
        """
        使用肘部法确定最优聚类数
        
        Args:
            data: 标准化后的聚类数据
            max_clusters: 最大聚类数
            
        Returns:
            最优聚类数
        """
        try:
            from sklearn.cluster import KMeans
            
            inertias = []
            K_range = range(2, min(max_clusters + 1, len(data) + 1))
            
            for k in K_range:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                kmeans.fit(data)
                inertias.append(kmeans.inertia_)
            
            # 计算肘部点
            if len(inertias) < 2:
                return 3  # 默认值
            
            # 简单的肘部检测：寻找惯性下降最大的点
            decreases = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
            optimal_k = K_range[decreases.index(max(decreases))]
            
            return min(optimal_k, 5)  # 限制最大聚类数为5
            
        except Exception as e:
            logger.warning(f"自动确定聚类数失败: {e}，使用默认值3")
            return 3
    
    def _rule_based_classification(self) -> Dict[str, Any]:
        """
        基于规则的请求分类（当sklearn不可用时）
        
        Returns:
            基于规则的分类结果
        """
        logger.info("使用基于规则的请求分类")
        
        # 定义分类规则
        cluster_labels = []
        
        for _, row in self.request_features.iterrows():
            if row['avg_loss'] == 0:
                cluster_labels.append(0)  # 零损失型
            elif row['avg_loss'] > self.request_features['avg_loss'].quantile(0.75):
                cluster_labels.append(1)  # 高损失型
            elif row['avg_time'] > self.request_features['avg_time'].quantile(0.75):
                cluster_labels.append(2)  # 时间敏感型
            else:
                cluster_labels.append(3)  # 平衡型
        
        self.request_features['cluster'] = cluster_labels
        
        return {
            'n_clusters': 4,
            'cluster_labels': cluster_labels,
            'method': 'rule_based',
            'features_used': ['avg_loss', 'avg_time'],
            'cluster_names': {
                0: '零损失型',
                1: '高损失型', 
                2: '时间敏感型',
                3: '平衡型'
            }
        }
    
    def _analyze_cluster_characteristics(self, clustering_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析各聚类的特征
        
        Args:
            clustering_results: 聚类结果
            
        Returns:
            聚类特征分析结果
        """
        characteristics = {}
        
        for cluster_id in range(clustering_results['n_clusters']):
            cluster_data = self.request_features[self.request_features['cluster'] == cluster_id]
            
            if len(cluster_data) == 0:
                continue
            
            # 基础统计特征
            characteristics[cluster_id] = {
                'size': len(cluster_data),
                'req_ids': cluster_data['req_id'].tolist(),
                'feature_means': {},
                'feature_stds': {},
                'distinguishing_features': {}
            }
            
            # 计算各特征的均值和标准差
            numeric_columns = cluster_data.select_dtypes(include=[np.number]).columns
            numeric_columns = [col for col in numeric_columns if col != 'cluster']
            
            for feature in numeric_columns:
                characteristics[cluster_id]['feature_means'][feature] = cluster_data[feature].mean()
                characteristics[cluster_id]['feature_stds'][feature] = cluster_data[feature].std()
            
            # 识别区分性特征
            characteristics[cluster_id]['distinguishing_features'] = self._identify_distinguishing_features(
                cluster_data, cluster_id
            )
            
            # 生成聚类描述
            characteristics[cluster_id]['description'] = self._generate_cluster_description(
                cluster_data, cluster_id
            )
        
        # 聚类间对比分析
        characteristics['cluster_comparison'] = self._compare_clusters(characteristics)
        
        return characteristics
    
    def _identify_distinguishing_features(self, cluster_data: pd.DataFrame, cluster_id: int) -> Dict[str, Any]:
        """
        识别聚类的区分性特征
        
        Args:
            cluster_data: 聚类数据
            cluster_id: 聚类ID
            
        Returns:
            区分性特征分析结果
        """
        distinguishing = {}
        
        # 与全局平均值比较
        numeric_columns = cluster_data.select_dtypes(include=[np.number]).columns
        numeric_columns = [col for col in numeric_columns if col != 'cluster']
        
        for feature in numeric_columns:
            cluster_mean = cluster_data[feature].mean()
            global_mean = self.request_features[feature].mean()
            global_std = self.request_features[feature].std()
            
            if global_std > 0:
                # 计算标准化差异
                z_score = (cluster_mean - global_mean) / global_std
                
                if abs(z_score) > 1:  # 显著差异
                    distinguishing[feature] = {
                        'cluster_mean': cluster_mean,
                        'global_mean': global_mean,
                        'z_score': z_score,
                        'significance': 'high' if abs(z_score) > 2 else 'moderate'
                    }
        
        return distinguishing
    
    def _generate_cluster_description(self, cluster_data: pd.DataFrame, cluster_id: int) -> str:
        """
        生成聚类描述
        
        Args:
            cluster_data: 聚类数据
            cluster_id: 聚类ID
            
        Returns:
            聚类描述字符串
        """
        # 分析主要特征
        avg_loss = cluster_data['avg_loss'].mean()
        avg_time = cluster_data['avg_time'].mean()
        avg_length = cluster_data['avg_length'].mean()
        path_count = cluster_data['path_count'].mean()
        
        # 与全局比较
        global_avg_loss = self.request_features['avg_loss'].mean()
        global_avg_time = self.request_features['avg_time'].mean()
        
        description_parts = []
        
        # 损失特征
        if avg_loss == 0:
            description_parts.append("零损失")
        elif avg_loss > global_avg_loss * 1.5:
            description_parts.append("高损失")
        elif avg_loss < global_avg_loss * 0.5:
            description_parts.append("低损失")
        
        # 时间特征
        if avg_time > global_avg_time * 1.5:
            description_parts.append("长时间")
        elif avg_time < global_avg_time * 0.5:
            description_parts.append("短时间")
        
        # 复杂度特征
        if path_count > self.request_features['path_count'].quantile(0.75):
            description_parts.append("高复杂度")
        elif path_count < self.request_features['path_count'].quantile(0.25):
            description_parts.append("低复杂度")
        
        # 路径长度特征
        if avg_length > self.request_features['avg_length'].quantile(0.75):
            description_parts.append("长路径")
        elif avg_length < self.request_features['avg_length'].quantile(0.25):
            description_parts.append("短路径")
        
        if not description_parts:
            description_parts.append("平衡型")
        
        return "、".join(description_parts) + "请求"
    
    def _compare_clusters(self, characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """
        聚类间对比分析
        
        Args:
            characteristics: 聚类特征
            
        Returns:
            聚类对比结果
        """
        comparison = {
            'size_distribution': {},
            'feature_differences': {},
            'cluster_separation': {}
        }
        
        # 大小分布
        cluster_sizes = {}
        for cluster_id in characteristics:
            if isinstance(cluster_id, int):
                cluster_sizes[cluster_id] = characteristics[cluster_id]['size']
        
        comparison['size_distribution'] = {
            'sizes': cluster_sizes,
            'largest_cluster': max(cluster_sizes.keys(), key=lambda x: cluster_sizes[x]) if cluster_sizes else None,
            'smallest_cluster': min(cluster_sizes.keys(), key=lambda x: cluster_sizes[x]) if cluster_sizes else None,
            'size_balance': min(cluster_sizes.values()) / max(cluster_sizes.values()) if cluster_sizes and max(cluster_sizes.values()) > 0 else 0
        }
        
        # 特征差异分析
        if len(cluster_sizes) >= 2:
            feature_differences = {}
            cluster_ids = list(cluster_sizes.keys())
            
            for feature in ['avg_loss', 'avg_time', 'avg_length', 'path_count']:
                if feature in self.request_features.columns:
                    feature_values = []
                    for cid in cluster_ids:
                        if cid in characteristics and 'feature_means' in characteristics[cid]:
                            feature_values.append(characteristics[cid]['feature_means'].get(feature, 0))
                    
                    if feature_values:
                        feature_differences[feature] = {
                            'max_value': max(feature_values),
                            'min_value': min(feature_values),
                            'range': max(feature_values) - min(feature_values),
                            'coefficient_of_variation': np.std(feature_values) / np.mean(feature_values) if np.mean(feature_values) > 0 else 0
                        }
            
            comparison['feature_differences'] = feature_differences
        
        return comparison
    
    def _analyze_performance_by_type(self, clustering_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析算法在不同类型上的表现
        
        Args:
            clustering_results: 聚类结果
            
        Returns:
            按类型的性能分析结果
        """
        performance_by_type = {}
        
        # 为每个聚类计算性能指标
        for cluster_id in range(clustering_results['n_clusters']):
            cluster_requests = self.request_features[
                self.request_features['cluster'] == cluster_id
            ]['req_id'].tolist()
            
            if not cluster_requests:
                continue
            
            # 获取该聚类的所有路径数据
            cluster_paths = self.df[self.df['req_id'].isin(cluster_requests)]
            
            performance_by_type[cluster_id] = {
                'request_count': len(cluster_requests),
                'total_paths': len(cluster_paths),
                'avg_paths_per_request': len(cluster_paths) / len(cluster_requests),
                'performance_metrics': self._calculate_cluster_performance_metrics(cluster_paths),
                'optimization_potential': self._assess_optimization_potential(cluster_paths),
                'algorithm_suitability': self._assess_algorithm_suitability(cluster_paths)
            }
        
        # 跨类型性能对比
        performance_by_type['cross_type_comparison'] = self._compare_performance_across_types(
            performance_by_type
        )
        
        return performance_by_type
    
    def _calculate_cluster_performance_metrics(self, cluster_paths: pd.DataFrame) -> Dict[str, Any]:
        """
        计算聚类的性能指标
        
        Args:
            cluster_paths: 聚类的路径数据
            
        Returns:
            性能指标
        """
        metrics = {
            'avg_loss': cluster_paths['path_sale_loss'].mean(),
            'loss_std': cluster_paths['path_sale_loss'].std(),
            'avg_time': cluster_paths['path_duration'].mean(),
            'time_std': cluster_paths['path_duration'].std(),
            'avg_length': cluster_paths['path_length'].mean(),
            'length_std': cluster_paths['path_length'].std()
        }
        
        # 如果有评分数据，计算质量指标
        if 'total_score' in cluster_paths.columns:
            metrics.update({
                'avg_score': cluster_paths['total_score'].mean(),
                'score_std': cluster_paths['total_score'].std(),
                'best_score': cluster_paths['total_score'].max(),
                'worst_score': cluster_paths['total_score'].min(),
                'score_range': cluster_paths['total_score'].max() - cluster_paths['total_score'].min()
            })
            
            # 按请求计算最优解质量
            request_best_scores = cluster_paths.groupby('req_id')['total_score'].max()
            metrics.update({
                'avg_best_score_per_request': request_best_scores.mean(),
                'best_score_consistency': request_best_scores.std()
            })
        
        return metrics
    
    def _assess_optimization_potential(self, cluster_paths: pd.DataFrame) -> Dict[str, Any]:
        """
        评估优化潜力
        
        Args:
            cluster_paths: 聚类的路径数据
            
        Returns:
            优化潜力评估结果
        """
        potential = {}
        
        # 基于分布特征评估优化潜力
        loss_cv = cluster_paths['path_sale_loss'].std() / cluster_paths['path_sale_loss'].mean() if cluster_paths['path_sale_loss'].mean() > 0 else 0
        time_cv = cluster_paths['path_duration'].std() / cluster_paths['path_duration'].mean() if cluster_paths['path_duration'].mean() > 0 else 0
        
        potential['variability_based'] = {
            'loss_optimization_potential': min(1.0, loss_cv),  # 变异系数越大，优化潜力越大
            'time_optimization_potential': min(1.0, time_cv),
            'overall_potential': (min(1.0, loss_cv) + min(1.0, time_cv)) / 2
        }
        
        # 基于极值差异评估优化潜力
        if len(cluster_paths) > 1:
            loss_range = cluster_paths['path_sale_loss'].max() - cluster_paths['path_sale_loss'].min()
            time_range = cluster_paths['path_duration'].max() - cluster_paths['path_duration'].min()
            
            # 标准化范围（相对于均值）
            loss_range_ratio = loss_range / cluster_paths['path_sale_loss'].mean() if cluster_paths['path_sale_loss'].mean() > 0 else 0
            time_range_ratio = time_range / cluster_paths['path_duration'].mean() if cluster_paths['path_duration'].mean() > 0 else 0
            
            potential['range_based'] = {
                'loss_range_potential': min(1.0, loss_range_ratio),
                'time_range_potential': min(1.0, time_range_ratio),
                'overall_range_potential': (min(1.0, loss_range_ratio) + min(1.0, time_range_ratio)) / 2
            }
        
        # 综合优化潜力评分
        if 'range_based' in potential:
            potential['overall_optimization_potential'] = (
                potential['variability_based']['overall_potential'] * 0.6 +
                potential['range_based']['overall_range_potential'] * 0.4
            )
        else:
            potential['overall_optimization_potential'] = potential['variability_based']['overall_potential']
        
        return potential
    
    def _assess_algorithm_suitability(self, cluster_paths: pd.DataFrame) -> Dict[str, Any]:
        """
        评估算法适用性
        
        Args:
            cluster_paths: 聚类的路径数据
            
        Returns:
            算法适用性评估结果
        """
        suitability = {}
        
        # 基于路径数量评估全排列算法的适用性
        unique_requests = cluster_paths['req_id'].nunique()
        total_paths = len(cluster_paths)
        avg_paths_per_request = total_paths / unique_requests
        
        # 计算计算复杂度指标
        complexity_score = np.log(avg_paths_per_request + 1)  # 对数复杂度
        
        if avg_paths_per_request < 100:
            complexity_level = 'low'
            suitability_score = 1.0
        elif avg_paths_per_request < 1000:
            complexity_level = 'medium'
            suitability_score = 0.8
        elif avg_paths_per_request < 5000:
            complexity_level = 'high'
            suitability_score = 0.6
        else:
            complexity_level = 'very_high'
            suitability_score = 0.4
        
        suitability['computational_suitability'] = {
            'avg_paths_per_request': avg_paths_per_request,
            'complexity_level': complexity_level,
            'complexity_score': complexity_score,
            'suitability_score': suitability_score
        }
        
        # 基于解质量分布评估算法价值
        if 'total_score' in cluster_paths.columns:
            # 计算最优解与平均解的差距
            request_improvements = []
            for req_id, req_group in cluster_paths.groupby('req_id'):
                best_score = req_group['total_score'].max()
                avg_score = req_group['total_score'].mean()
                improvement = (best_score - avg_score) / avg_score if avg_score > 0 else 0
                request_improvements.append(improvement)
            
            avg_improvement = np.mean(request_improvements)
            
            if avg_improvement > 0.2:
                value_level = 'high'
                value_score = 1.0
            elif avg_improvement > 0.1:
                value_level = 'medium'
                value_score = 0.8
            elif avg_improvement > 0.05:
                value_level = 'low'
                value_score = 0.6
            else:
                value_level = 'minimal'
                value_score = 0.4
            
            suitability['value_suitability'] = {
                'avg_improvement_ratio': avg_improvement,
                'value_level': value_level,
                'value_score': value_score
            }
            
            # 综合适用性评分
            suitability['overall_suitability'] = {
                'score': (suitability_score * 0.6 + value_score * 0.4),
                'recommendation': self._generate_suitability_recommendation(
                    complexity_level, value_level, suitability_score * 0.6 + value_score * 0.4
                )
            }
        else:
            suitability['overall_suitability'] = {
                'score': suitability_score,
                'recommendation': self._generate_suitability_recommendation(
                    complexity_level, 'unknown', suitability_score
                )
            }
        
        return suitability
    
    def _generate_suitability_recommendation(self, complexity_level: str, value_level: str, overall_score: float) -> str:
        """
        生成适用性建议
        
        Args:
            complexity_level: 复杂度等级
            value_level: 价值等级
            overall_score: 综合评分
            
        Returns:
            适用性建议
        """
        if overall_score >= 0.8:
            return f"高度适用：{complexity_level}复杂度，{value_level}价值，建议继续使用全排列算法"
        elif overall_score >= 0.6:
            return f"适度适用：{complexity_level}复杂度，{value_level}价值，可考虑优化或替代算法"
        elif overall_score >= 0.4:
            return f"有限适用：{complexity_level}复杂度，{value_level}价值，建议考虑启发式算法"
        else:
            return f"不适用：{complexity_level}复杂度，{value_level}价值，强烈建议使用其他算法"
    
    def _compare_performance_across_types(self, performance_by_type: Dict[str, Any]) -> Dict[str, Any]:
        """
        跨类型性能对比
        
        Args:
            performance_by_type: 按类型的性能数据
            
        Returns:
            跨类型对比结果
        """
        comparison = {
            'best_performing_type': None,
            'worst_performing_type': None,
            'performance_variance': {},
            'suitability_ranking': []
        }
        
        # 收集各类型的关键指标
        type_scores = {}
        suitability_scores = {}
        
        for cluster_id, data in performance_by_type.items():
            if isinstance(cluster_id, int) and 'algorithm_suitability' in data:
                suitability_scores[cluster_id] = data['algorithm_suitability']['overall_suitability']['score']
                
                # 计算综合性能评分
                if 'performance_metrics' in data and 'avg_score' in data['performance_metrics']:
                    type_scores[cluster_id] = data['performance_metrics']['avg_score']
        
        # 找出最佳和最差类型
        if suitability_scores:
            comparison['best_performing_type'] = max(suitability_scores.keys(), 
                                                   key=lambda x: suitability_scores[x])
            comparison['worst_performing_type'] = min(suitability_scores.keys(), 
                                                    key=lambda x: suitability_scores[x])
            
            # 适用性排名
            comparison['suitability_ranking'] = sorted(suitability_scores.items(), 
                                                     key=lambda x: x[1], reverse=True)
        
        # 性能方差分析
        if type_scores:
            comparison['performance_variance'] = {
                'score_variance': np.var(list(type_scores.values())),
                'score_range': max(type_scores.values()) - min(type_scores.values()),
                'consistency': 1 - (np.std(list(type_scores.values())) / np.mean(list(type_scores.values()))) if np.mean(list(type_scores.values())) > 0 else 0
            }
        
        return comparison
    
    def _generate_type_recommendations(self, cluster_characteristics: Dict[str, Any], 
                                     performance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成针对不同类型的建议
        
        Args:
            cluster_characteristics: 聚类特征
            performance_analysis: 性能分析结果
            
        Returns:
            类型化建议
        """
        recommendations = {}
        
        for cluster_id in cluster_characteristics:
            if not isinstance(cluster_id, int):
                continue
            
            cluster_data = cluster_characteristics[cluster_id]
            performance_data = performance_analysis.get(cluster_id, {})
            
            # 生成针对该类型的建议
            recommendations[cluster_id] = {
                'type_description': cluster_data.get('description', f'聚类{cluster_id}'),
                'request_count': cluster_data.get('size', 0),
                'key_characteristics': self._extract_key_characteristics(cluster_data),
                'optimization_suggestions': self._generate_optimization_suggestions(
                    cluster_data, performance_data
                ),
                'algorithm_recommendations': self._generate_algorithm_recommendations(
                    performance_data
                ),
                'priority_level': self._assess_optimization_priority(
                    cluster_data, performance_data
                )
            }
        
        # 生成总体建议
        recommendations['overall_strategy'] = self._generate_overall_strategy(
            cluster_characteristics, performance_analysis
        )
        
        return recommendations
    
    def _extract_key_characteristics(self, cluster_data: Dict[str, Any]) -> List[str]:
        """
        提取关键特征
        
        Args:
            cluster_data: 聚类数据
            
        Returns:
            关键特征列表
        """
        characteristics = []
        
        distinguishing_features = cluster_data.get('distinguishing_features', {})
        
        for feature, data in distinguishing_features.items():
            if data['significance'] == 'high':
                if data['z_score'] > 2:
                    characteristics.append(f"{feature}显著高于平均水平")
                elif data['z_score'] < -2:
                    characteristics.append(f"{feature}显著低于平均水平")
        
        return characteristics[:5]  # 返回前5个关键特征
    
    def _generate_optimization_suggestions(self, cluster_data: Dict[str, Any], 
                                         performance_data: Dict[str, Any]) -> List[str]:
        """
        生成优化建议
        
        Args:
            cluster_data: 聚类数据
            performance_data: 性能数据
            
        Returns:
            优化建议列表
        """
        suggestions = []
        
        # 基于优化潜力生成建议
        if 'optimization_potential' in performance_data:
            potential = performance_data['optimization_potential']
            overall_potential = potential.get('overall_optimization_potential', 0)
            
            if overall_potential > 0.7:
                suggestions.append("具有高优化潜力，建议重点关注")
            elif overall_potential > 0.4:
                suggestions.append("具有中等优化潜力，可考虑优化")
            else:
                suggestions.append("优化潜力有限，维持现状即可")
        
        # 基于特征生成具体建议
        distinguishing_features = cluster_data.get('distinguishing_features', {})
        
        if 'avg_loss' in distinguishing_features:
            loss_data = distinguishing_features['avg_loss']
            if loss_data['z_score'] > 1:
                suggestions.append("损失较高，建议优化路径选择策略")
        
        if 'avg_time' in distinguishing_features:
            time_data = distinguishing_features['avg_time']
            if time_data['z_score'] > 1:
                suggestions.append("时间较长，建议优化路径规划算法")
        
        if 'path_count' in distinguishing_features:
            count_data = distinguishing_features['path_count']
            if count_data['z_score'] > 1:
                suggestions.append("路径数量较多，建议实施剪枝策略")
        
        return suggestions[:3]  # 返回前3个建议
    
    def _generate_algorithm_recommendations(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成算法建议
        
        Args:
            performance_data: 性能数据
            
        Returns:
            算法建议
        """
        if 'algorithm_suitability' not in performance_data:
            return {'recommendation': '数据不足，无法给出算法建议'}
        
        suitability = performance_data['algorithm_suitability']
        overall_suitability = suitability.get('overall_suitability', {})
        
        return {
            'current_algorithm_suitability': overall_suitability.get('score', 0),
            'recommendation': overall_suitability.get('recommendation', '无建议'),
            'alternative_algorithms': self._suggest_alternative_algorithms(suitability)
        }
    
    def _suggest_alternative_algorithms(self, suitability_data: Dict[str, Any]) -> List[str]:
        """
        建议替代算法
        
        Args:
            suitability_data: 适用性数据
            
        Returns:
            替代算法建议列表
        """
        alternatives = []
        
        computational = suitability_data.get('computational_suitability', {})
        complexity_level = computational.get('complexity_level', 'unknown')
        
        if complexity_level == 'very_high':
            alternatives.extend(['遗传算法', '模拟退火', '粒子群优化'])
        elif complexity_level == 'high':
            alternatives.extend(['贪心算法', 'A*算法', '动态规划'])
        elif complexity_level == 'medium':
            alternatives.extend(['贪心算法', '局部搜索'])
        
        value_data = suitability_data.get('value_suitability', {})
        if value_data and value_data.get('value_level') == 'minimal':
            alternatives.append('简单启发式算法')
        
        return alternatives[:3]  # 返回前3个替代算法
    
    def _assess_optimization_priority(self, cluster_data: Dict[str, Any], 
                                    performance_data: Dict[str, Any]) -> str:
        """
        评估优化优先级
        
        Args:
            cluster_data: 聚类数据
            performance_data: 性能数据
            
        Returns:
            优先级等级
        """
        # 基于多个因素确定优先级
        priority_score = 0
        
        # 请求数量权重
        size = cluster_data.get('size', 0)
        if size > 3:
            priority_score += 0.3
        elif size > 1:
            priority_score += 0.2
        
        # 优化潜力权重
        if 'optimization_potential' in performance_data:
            potential = performance_data['optimization_potential'].get('overall_optimization_potential', 0)
            priority_score += potential * 0.4
        
        # 算法适用性权重
        if 'algorithm_suitability' in performance_data:
            suitability = performance_data['algorithm_suitability']['overall_suitability'].get('score', 0)
            priority_score += (1 - suitability) * 0.3  # 适用性越低，优化优先级越高
        
        if priority_score >= 0.7:
            return 'high'
        elif priority_score >= 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _generate_overall_strategy(self, cluster_characteristics: Dict[str, Any], 
                                 performance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成总体策略建议
        
        Args:
            cluster_characteristics: 聚类特征
            performance_analysis: 性能分析
            
        Returns:
            总体策略建议
        """
        strategy = {
            'cluster_count': len([k for k in cluster_characteristics.keys() if isinstance(k, int)]),
            'diversity_assessment': '',
            'optimization_priorities': [],
            'resource_allocation_suggestions': [],
            'algorithm_strategy': ''
        }
        
        # 评估请求多样性
        cluster_sizes = []
        for cluster_id in cluster_characteristics:
            if isinstance(cluster_id, int):
                cluster_sizes.append(cluster_characteristics[cluster_id].get('size', 0))
        
        if cluster_sizes:
            size_cv = np.std(cluster_sizes) / np.mean(cluster_sizes) if np.mean(cluster_sizes) > 0 else 0
            if size_cv > 0.5:
                strategy['diversity_assessment'] = '请求类型多样性高，需要差异化策略'
            else:
                strategy['diversity_assessment'] = '请求类型相对集中，可采用统一策略'
        
        # 确定优化优先级
        priority_clusters = []
        for cluster_id in cluster_characteristics:
            if isinstance(cluster_id, int) and cluster_id in performance_analysis:
                perf_data = performance_analysis[cluster_id]
                if 'optimization_potential' in perf_data:
                    potential = perf_data['optimization_potential'].get('overall_optimization_potential', 0)
                    size = cluster_characteristics[cluster_id].get('size', 0)
                    priority_score = potential * size  # 潜力 × 规模
                    priority_clusters.append((cluster_id, priority_score))
        
        priority_clusters.sort(key=lambda x: x[1], reverse=True)
        strategy['optimization_priorities'] = [f'聚类{cid}' for cid, _ in priority_clusters[:3]]
        
        # 资源分配建议
        total_requests = sum(cluster_sizes)
        for cluster_id, size in enumerate(cluster_sizes):
            if size > 0:
                resource_ratio = size / total_requests
                if resource_ratio > 0.3:
                    strategy['resource_allocation_suggestions'].append(
                        f'聚类{cluster_id}占比{resource_ratio:.1%}，建议重点投入资源'
                    )
        
        # 算法策略建议
        high_suitability_count = 0
        low_suitability_count = 0
        
        for cluster_id in performance_analysis:
            if isinstance(cluster_id, int) and 'algorithm_suitability' in performance_analysis[cluster_id]:
                score = performance_analysis[cluster_id]['algorithm_suitability']['overall_suitability'].get('score', 0)
                if score >= 0.7:
                    high_suitability_count += 1
                elif score < 0.5:
                    low_suitability_count += 1
        
        total_clusters = len([k for k in performance_analysis.keys() if isinstance(k, int)])
        if low_suitability_count > total_clusters * 0.5:
            strategy['algorithm_strategy'] = '多数请求类型不适合全排列算法，建议考虑混合算法策略'
        elif high_suitability_count > total_clusters * 0.7:
            strategy['algorithm_strategy'] = '全排列算法整体适用性良好，建议继续优化现有算法'
        else:
            strategy['algorithm_strategy'] = '不同请求类型适用性差异较大，建议采用分类处理策略'
        
        return strategy
    
    def get_clustering_analysis_summary(self) -> Dict[str, Any]:
        """
        获取聚类分析摘要
        
        Returns:
            聚类分析摘要
        """
        # 执行完整分析
        analysis_results = self.analyze_request_types()
        
        # 提取关键信息
        clustering_results = analysis_results['clustering_results']
        cluster_characteristics = analysis_results['cluster_characteristics']
        performance_analysis = analysis_results['algorithm_performance_by_type']
        recommendations = analysis_results['type_recommendations']
        
        # 生成摘要
        summary = {
            'cluster_count': clustering_results.get('n_clusters', 0),
            'clustering_quality': {
                'silhouette_score': clustering_results.get('silhouette_score', 0),
                'method': clustering_results.get('method', 'kmeans')
            },
            'cluster_descriptions': {},
            'key_findings': [],
            'optimization_priorities': recommendations.get('overall_strategy', {}).get('optimization_priorities', []),
            'algorithm_strategy': recommendations.get('overall_strategy', {}).get('algorithm_strategy', ''),
            'detailed_results': analysis_results
        }
        
        # 聚类描述
        for cluster_id in cluster_characteristics:
            if isinstance(cluster_id, int):
                summary['cluster_descriptions'][cluster_id] = {
                    'description': cluster_characteristics[cluster_id].get('description', ''),
                    'size': cluster_characteristics[cluster_id].get('size', 0),
                    'suitability_score': performance_analysis.get(cluster_id, {}).get(
                        'algorithm_suitability', {}
                    ).get('overall_suitability', {}).get('score', 0)
                }
        
        # 关键发现
        total_requests = sum([data['size'] for cluster_id, data in cluster_characteristics.items() 
                            if isinstance(cluster_id, int)])
        
        summary['key_findings'].append(f'识别出{clustering_results.get("n_clusters", 0)}种不同类型的请求')
        
        # 找出最大和最小的聚类
        if cluster_characteristics:
            largest_cluster = max([cluster_id for cluster_id in cluster_characteristics.keys() if isinstance(cluster_id, int)], 
                                key=lambda x: cluster_characteristics[x].get('size', 0))
            largest_size = cluster_characteristics[largest_cluster].get('size', 0)
            
            summary['key_findings'].append(
                f'最大聚类包含{largest_size}个请求({largest_size/total_requests:.1%})'
            )
        
        # 算法适用性总结
        if performance_analysis:
            suitable_clusters = 0
            for cluster_id in performance_analysis:
                if isinstance(cluster_id, int):
                    suitability = performance_analysis[cluster_id].get('algorithm_suitability', {})
                    score = suitability.get('overall_suitability', {}).get('score', 0)
                    if score >= 0.6:
                        suitable_clusters += 1
            
            total_clusters = len([k for k in performance_analysis.keys() if isinstance(k, int)])
            summary['key_findings'].append(
                f'{suitable_clusters}/{total_clusters}种请求类型适合使用全排列算法'
            )
        
        return summary 