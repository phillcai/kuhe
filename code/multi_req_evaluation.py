import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import json

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class MultiReqPathEvaluator:
    """多请求路径综合评价器"""
    
    def __init__(self, 
                 loss_weight: float = 0.6,
                 time_weight: float = 0.3, 
                 replenish_weight: float = 0.1):
        """
        初始化路径评价器
        
        Args:
            loss_weight: 销量损失权重
            time_weight: 时间效率权重  
            replenish_weight: 补货效率权重
        """
        self.loss_weight = loss_weight
        self.time_weight = time_weight
        self.replenish_weight = replenish_weight
        
        # 验证权重和为1
        total_weight = loss_weight + time_weight + replenish_weight
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(f"权重之和必须为1，当前为{total_weight}")
    
    def normalize_score(self, values: np.ndarray, is_min_better: bool = True) -> np.ndarray:
        """
        使用Min-Max归一化方法计算评分
        
        Args:
            values: 待归一化的值数组
            is_min_better: True表示越小越好，False表示越大越好
            
        Returns:
            归一化后的评分数组(0-1范围)
        """
        if len(values) == 0:
            return np.array([])
        
        min_val = np.min(values)
        max_val = np.max(values)
        
        # 避免除零错误
        if max_val == min_val:
            return np.ones_like(values)
        
        if is_min_better:
            # 越小越好的指标：损失、时间
            scores = (max_val - values) / (max_val - min_val)
        else:
            # 越大越好的指标：补货效率
            scores = (values - min_val) / (max_val - min_val)
        
        return scores
    
    def evaluate_paths(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        评价所有路径
        
        Args:
            df: 包含路径数据的DataFrame
            
        Returns:
            添加评价指标的DataFrame
        """
        # 数据预处理
        df = df.copy()
        
        # 转换数据类型
        df['path_duration'] = df['path_duration'].str.replace(',', '').astype(float)
        df['path_sale_loss'] = df['path_sale_loss'].astype(float)
        df['补货率'] = df['补货率'].astype(float)
        
        # 按req_id分组计算评分
        evaluated_dfs = []
        
        for req_id, group in df.groupby('req_id'):
            # 计算各项评分
            loss_scores = self.normalize_score(group['path_sale_loss'].values, is_min_better=True)
            time_scores = self.normalize_score(group['path_duration'].values, is_min_better=True)
            replenish_scores = self.normalize_score(group['补货率'].values, is_min_better=False)
            
            # 计算综合评分
            total_scores = (self.loss_weight * loss_scores + 
                           self.time_weight * time_scores + 
                           self.replenish_weight * replenish_scores)
            
            # 创建结果DataFrame
            result_df = group.copy()
            result_df['loss_score'] = loss_scores
            result_df['time_score'] = time_scores
            result_df['replenish_score'] = replenish_scores
            result_df['total_score'] = total_scores
            
            # 添加排名
            result_df['rank'] = result_df['total_score'].rank(ascending=False, method='min')
            
            evaluated_dfs.append(result_df)
        
        return pd.concat(evaluated_dfs, ignore_index=True)
    
    def analyze_multi_req_results(self, df: pd.DataFrame) -> Dict:
        """分析多请求评价结果"""
        analysis = {}
        
        # 基本统计
        analysis['总请求数'] = df['req_id'].nunique()
        analysis['总路径数'] = len(df)
        analysis['平均每请求路径数'] = len(df) / df['req_id'].nunique()
        
        # 按req_id的统计
        req_stats = df.groupby('req_id').agg({
            'path_sale_loss': ['mean', 'std', 'min', 'max'],
            'path_duration': ['mean', 'std', 'min', 'max'],
            '补货率': ['mean', 'std', 'min', 'max'],
            'total_score': ['mean', 'std', 'min', 'max'],
            'loss_score': ['mean', 'std'],
            'time_score': ['mean', 'std'],
            'replenish_score': ['mean', 'std']
        }).round(3)
        
        analysis['各请求统计'] = req_stats
        
        # 最优路径分析
        best_paths = []
        for req_id, group in df.groupby('req_id'):
            best_path = group.loc[group['total_score'].idxmax()]
            best_paths.append({
                'req_id': req_id,
                'path': best_path['path'],
                'total_score': best_path['total_score'],
                'loss_score': best_path['loss_score'],
                'time_score': best_path['time_score'],
                'replenish_score': best_path['replenish_score'],
                'path_sale_loss': best_path['path_sale_loss'],
                'path_duration': best_path['path_duration'],
                '补货率': best_path['补货率'],
                'rank': best_path['rank']
            })
        
        analysis['各请求最优路径'] = best_paths
        
        # 权重合理性分析
        weight_analysis = self.analyze_weight_reasonableness(df)
        analysis['权重合理性分析'] = weight_analysis
        
        return analysis
    
    def analyze_weight_reasonableness(self, df: pd.DataFrame) -> Dict:
        """分析权重设置的合理性"""
        analysis = {}
        
        # 计算各指标的区分度
        loss_discrimination = df.groupby('req_id')['loss_score'].std().mean()
        time_discrimination = df.groupby('req_id')['time_score'].std().mean()
        replenish_discrimination = df.groupby('req_id')['replenish_score'].std().mean()
        
        analysis['指标区分度'] = {
            '损失评分区分度': loss_discrimination,
            '时间评分区分度': time_discrimination,
            '补货评分区分度': replenish_discrimination
        }
        
        # 计算权重贡献度
        weighted_loss_contribution = self.loss_weight * loss_discrimination
        weighted_time_contribution = self.time_weight * time_discrimination
        weighted_replenish_contribution = self.replenish_weight * replenish_discrimination
        
        analysis['权重贡献度'] = {
            '损失权重贡献': weighted_loss_contribution,
            '时间权重贡献': weighted_time_contribution,
            '补货权重贡献': weighted_replenish_contribution
        }
        
        # 计算权重效率（贡献度/权重）
        analysis['权重效率'] = {
            '损失权重效率': weighted_loss_contribution / self.loss_weight if self.loss_weight > 0 else 0,
            '时间权重效率': weighted_time_contribution / self.time_weight if self.time_weight > 0 else 0,
            '补货权重效率': weighted_replenish_contribution / self.replenish_weight if self.replenish_weight > 0 else 0
        }
        
        return analysis

def generate_multi_req_sample_data() -> pd.DataFrame:
    """生成多req_id的示例数据用于演示"""
    np.random.seed(42)
    
    sample_data = []
    req_ids = ['req_001', 'req_002', 'req_003', 'req_004', 'req_005']
    
    for req_id in req_ids:
        # 为每个req_id生成不同特征的路径数据
        n_paths = np.random.randint(100, 500)
        
        for i in range(n_paths):
            # 根据req_id调整数据特征
            if req_id == 'req_001':  # 损失敏感型
                loss = np.random.exponential(8) + 2
                duration = np.random.normal(30000, 5000)
            elif req_id == 'req_002':  # 时间敏感型
                loss = np.random.exponential(12) + 4
                duration = np.random.normal(25000, 3000)
            elif req_id == 'req_003':  # 平衡型
                loss = np.random.exponential(10) + 3
                duration = np.random.normal(32000, 4000)
            elif req_id == 'req_004':  # 高损失型
                loss = np.random.exponential(15) + 6
                duration = np.random.normal(35000, 6000)
            else:  # req_005: 高效率型
                loss = np.random.exponential(6) + 1
                duration = np.random.normal(20000, 2000)
            
            # 生成路径
            path = f"{np.random.randint(100,200)}_{np.random.randint(100,200)}_{np.random.randint(100,200)}"
            
            sample_data.append({
                'req_id': req_id,
                'path': path,
                'path_duration': f"{duration:.0f}",
                'path_sale_loss': loss,
                '总点位数': np.random.randint(5, 10),
                '补货点位数': np.random.randint(5, 10),
                '补货率': 1.0
            })
    
    return pd.DataFrame(sample_data)

def load_and_evaluate_multi_req(file_path: str = 'data/multi_all_path.csv') -> Tuple[pd.DataFrame, Dict]:
    """
    加载多请求路径数据并进行评价
    
    Args:
        file_path: 路径数据文件路径，如果为None则使用示例数据
        
    Returns:
        评价后的DataFrame和分析结果
    """
    if file_path is None:
        print("=== 使用示例数据演示多请求分析 ===")
        df = generate_multi_req_sample_data()
    else:
        print("=== 加载多请求路径数据 ===")
        df = pd.read_csv(file_path)
    
    print(f"总记录数: {len(df)}")
    print(f"唯一req_id数: {df['req_id'].nunique()}")
    print(f"req_id列表: {sorted(df['req_id'].unique())}")
    
    # 创建评价器
    evaluator = MultiReqPathEvaluator(
        loss_weight=0.6,
        time_weight=0.35,
        replenish_weight=0.05
    )
    
    print(f"\n=== 开始多请求路径评价 ===")
    print(f"权重配置: 损失={evaluator.loss_weight}, 时间={evaluator.time_weight}, 补货={evaluator.replenish_weight}")
    
    # 评价路径
    evaluated_df = evaluator.evaluate_paths(df)
    
    # 分析结果
    analysis = evaluator.analyze_multi_req_results(evaluated_df)
    
    return evaluated_df, analysis

def print_multi_req_analysis(analysis: Dict):
    """打印多请求分析结果"""
    print("\n=== 多请求评价结果分析 ===")
    print(f"总请求数: {analysis['总请求数']}")
    print(f"总路径数: {analysis['总路径数']}")
    print(f"平均每请求路径数: {analysis['平均每请求路径数']:.1f}")
    
    print("\n=== 各请求统计概览 ===")
    req_stats = analysis['各请求统计']
    print(req_stats[('path_sale_loss', 'mean')].to_string())
    
    print("\n=== 各请求最优路径 ===")
    for best_path in analysis['各请求最优路径']:
        print(f"req_id: {best_path['req_id']}")
        print(f"  路径: {best_path['path']}")
        print(f"  综合评分: {best_path['total_score']:.3f}")
        print(f"  损失评分: {best_path['loss_score']:.3f}")
        print(f"  时间评分: {best_path['time_score']:.3f}")
        print(f"  实际损失: {best_path['path_sale_loss']:.2f}")
        print(f"  实际耗时: {(best_path['path_duration'] / 60):.1f}分钟")
        print()
    
    print("\n=== 权重合理性分析 ===")
    weight_analysis = analysis['权重合理性分析']
    
    print("指标区分度:")
    for key, value in weight_analysis['指标区分度'].items():
        print(f"  {key}: {value:.3f}")
    
    print("\n权重贡献度:")
    for key, value in weight_analysis['权重贡献度'].items():
        print(f"  {key}: {value:.3f}")
    
    print("\n权重效率:")
    for key, value in weight_analysis['权重效率'].items():
        print(f"  {key}: {value:.3f}")

def create_multi_req_visualizations(df: pd.DataFrame, output_dir: str = 'output'):
    """创建多请求评价结果可视化图表"""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # 设置图表样式
    plt.style.use('default')
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Multi-Request Path Evaluation Analysis', fontsize=16, fontweight='bold')
    
    # 1. 各请求最优路径评分对比
    req_best_scores = df.groupby('req_id')['total_score'].max()
    axes[0, 0].bar(req_best_scores.index, req_best_scores.values, color='skyblue', alpha=0.7)
    axes[0, 0].set_title('Best Path Score by Request')
    axes[0, 0].set_xlabel('Request ID')
    axes[0, 0].set_ylabel('Best Total Score')
    axes[0, 0].tick_params(axis='x', rotation=45)
    
    # 2. 各请求平均损失对比
    req_avg_loss = df.groupby('req_id')['path_sale_loss'].mean()
    axes[0, 1].bar(req_avg_loss.index, req_avg_loss.values, color='lightcoral', alpha=0.7)
    axes[0, 1].set_title('Average Sales Loss by Request')
    axes[0, 1].set_xlabel('Request ID')
    axes[0, 1].set_ylabel('Average Sales Loss')
    axes[0, 1].tick_params(axis='x', rotation=45)
    
    # 3. 各请求平均耗时对比
    req_avg_duration = df.groupby('req_id')['path_duration'].mean()
    axes[1, 0].bar(req_avg_duration.index, req_avg_duration.values, color='lightgreen', alpha=0.7)
    axes[1, 0].set_title('Average Path Duration by Request')
    axes[1, 0].set_xlabel('Request ID')
    axes[1, 0].set_ylabel('Average Duration')
    axes[1, 0].tick_params(axis='x', rotation=45)
    
    # 4. 评分分布箱线图
    df.boxplot(column='total_score', by='req_id', ax=axes[1, 1])
    axes[1, 1].set_title('Total Score Distribution by Request')
    axes[1, 1].set_xlabel('Request ID')
    axes[1, 1].set_ylabel('Total Score')
    axes[1, 1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/multi_req_evaluation_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 保存评价结果
    df.to_csv(f'{output_dir}/multi_req_evaluated_paths.csv', index=False)
    print(f"多请求评价结果已保存到 {output_dir}/")

def main():
    """主函数"""
    print("=== 多请求智能配送路径综合评价系统 ===")
    
    # 加载和评价多请求路径
    evaluated_df, analysis = load_and_evaluate_multi_req()
    
    # 打印分析结果
    print_multi_req_analysis(analysis)
    
    # 显示各请求前3个最优路径
    print("\n=== 各请求前3个最优路径 ===")
    for req_id in sorted(evaluated_df['req_id'].unique()):
        req_data = evaluated_df[evaluated_df['req_id'] == req_id]
        top_3 = req_data.nlargest(3, 'total_score')
        print(f"\n{req_id}:")
        
        # 转换path_duration从秒到分钟
        display_df = top_3[['path', 'total_score', 'path_sale_loss', 'path_duration']].copy()
        display_df['path_duration'] = (display_df['path_duration'] / 60).round(1)
        display_df = display_df.rename(columns={'path_duration': 'path_duration(min)'})
        
        print(display_df.to_string(index=False))
    
    # 创建可视化
    #create_multi_req_visualizations(evaluated_df)
    
    print("\n=== 多请求评价完成 ===")

if __name__ == "__main__":
    main() 