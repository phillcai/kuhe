import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import json

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class PathEvaluator:
    """路径综合评价器"""
    
    def __init__(self, 
                 loss_weight: float = 0.6,
                 time_weight: float = 0.25, 
                 replenish_weight: float = 0.15):
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
    
    def calculate_loss_score(self, path_sale_loss: np.ndarray) -> np.ndarray:
        """计算销量损失评分"""
        return self.normalize_score(path_sale_loss, is_min_better=True)
    
    def calculate_time_score(self, path_duration: np.ndarray) -> np.ndarray:
        """计算时间效率评分"""
        return self.normalize_score(path_duration, is_min_better=True)
    
    def calculate_replenish_score(self, replenish_rate: np.ndarray) -> np.ndarray:
        """计算补货效率评分"""
        return self.normalize_score(replenish_rate, is_min_better=False)
    
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
        
        # 转换数据类型 - 处理可能的字符串格式
        if df['path_duration'].dtype == 'object':
            df['path_duration'] = df['path_duration'].str.replace(',', '').astype(float)
        else:
            df['path_duration'] = df['path_duration'].astype(float)
        df['path_sale_loss'] = df['path_sale_loss'].astype(float)
        df['补货率'] = df['补货率'].astype(float)
        
        # 计算各项评分
        loss_scores = self.calculate_loss_score(df['path_sale_loss'].values)
        time_scores = self.calculate_time_score(df['path_duration'].values)
        replenish_scores = self.calculate_replenish_score(df['补货率'].values)
        
        # 计算综合评分
        total_scores = (self.loss_weight * loss_scores + 
                       self.time_weight * time_scores + 
                       self.replenish_weight * replenish_scores)
        
        # 添加评分列
        df['loss_score'] = loss_scores
        df['time_score'] = time_scores
        df['replenish_score'] = replenish_scores
        df['total_score'] = total_scores
        
        # 添加排名
        df['rank'] = df['total_score'].rank(ascending=False, method='min')
        
        return df
    
    def get_best_paths(self, df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """获取最优路径"""
        return df.nlargest(top_n, 'total_score')
    
    def get_optimal_path_with_priority(self, df: pd.DataFrame, priority_file: str = 'data/priority.csv') -> pd.DataFrame:
        """
        根据优先级获取最优路径
        
        筛选逻辑：
        1. 先筛选首个点优先级最高的路径集合
        2. 然后在这个集合中筛选满足以下条件的路径：
           - loss 不大于 best+5
           - 补货点位数量大于等于 best
           - 时间小于等于 best 的 1.1 倍，但不超过 best+30 分钟
        3. 最后取综合评分最高的路径
        
        Args:
            df: 评价后的DataFrame
            priority_file: 点位优先级文件路径
            
        Returns:
            最优路径的DataFrame
        """
        # 加载点位优先级数据
        try:
            priority_df = pd.read_csv(priority_file)
            # 创建点位优先级映射
            priority_map = dict(zip(priority_df['point_id'], priority_df['priority']))
        except Exception as e:
            print(f"警告：无法加载优先级文件 {priority_file}: {e}")
            # 如果没有优先级文件，直接返回最优路径
            return df.nlargest(1, 'total_score')
        
        # 获取初始最优路径（best）作为基准
        best_path = df.loc[df['total_score'].idxmax()]
        best_loss = best_path['path_sale_loss']
        best_replenish_count = best_path['补货点位数']
        best_time = best_path['path_duration']
        
        print(f"=== 基准路径信息 ===")
        print(f"基准损失: {best_loss}")
        print(f"基准补货点位数: {best_replenish_count}")
        print(f"基准时间: {best_time}")
        
        # 为所有路径添加首个点位优先级
        def get_first_point_priority(row):
            """获取首个点位的优先级"""
            try:
                if pd.isna(row['first_valid_point_id']):
                    return 0
                first_point_id = int(row['first_valid_point_id'])
                return priority_map.get(first_point_id, 0)
            except:
                return 0
        
        df_with_priority = df.copy()
        df_with_priority['first_point_priority'] = df_with_priority.apply(get_first_point_priority, axis=1)
        
        # 第一步：筛选首个点优先级最高的路径集合
        max_priority = df_with_priority['first_point_priority'].max()
        high_priority_df = df_with_priority[df_with_priority['first_point_priority'] == max_priority].copy()
        
        print(f"=== 第一步筛选：首个点优先级最高的路径 ===")
        print(f"最高优先级: {max_priority}")
        print(f"符合最高优先级的路径数量: {len(high_priority_df)}")
        
        if len(high_priority_df) == 0:
            print("警告：没有路径有有效的首个点位优先级，返回原始最优路径")
            return df.nlargest(1, 'total_score')
        
        # 第二步：在高优先级路径中应用筛选条件
        loss_threshold = best_loss + 5  # loss 不大于 best+5
        time_threshold_1 = best_time * 1.1  # best 的 1.1 倍
        time_threshold_2 = best_time + 30 * 60  # best + 30分钟（转换为秒）
        time_threshold = min(time_threshold_1, time_threshold_2)  # 取较小值，即"不超过 best+30 分钟"
        
        print(f"=== 第二步筛选条件 ===")
        print(f"损失上限: {loss_threshold:.2f} (best + 5)")
        print(f"补货点位数下限: {best_replenish_count} (>= best)")
        print(f"时间上限1: {time_threshold_1:.2f} (best * 1.1)")
        print(f"时间上限2: {time_threshold_2:.2f} (best + 30分钟)")
        print(f"最终时间上限: {time_threshold:.2f} (取较小值)")
        
        # 在高优先级路径中筛选符合条件的路径
        filtered_df = high_priority_df[
            (high_priority_df['path_sale_loss'] <= loss_threshold) &
            (high_priority_df['补货点位数'] >= best_replenish_count) &
            (high_priority_df['path_duration'] <= time_threshold)
        ].copy()
        
        print(f"符合所有筛选条件的路径数量: {len(filtered_df)}")
        
        if len(filtered_df) == 0:
            print("警告：高优先级路径中没有满足筛选条件的，返回高优先级中综合评分最高的路径")
            optimal_path = high_priority_df.nlargest(1, 'total_score')
        else:
            # 第三步：在符合条件的路径中选择综合评分最高的
            optimal_path = filtered_df.nlargest(1, 'total_score')
        
        print(f"=== 最终选择的最优路径 ===")
        print(f"req_id: {optimal_path['req_id'].iloc[0]}")
        print(f"路径: {optimal_path['path'].iloc[0]}")
        print(f"优化路径: {optimal_path['path_opt'].iloc[0]}")
        print(f"首个点位ID: {optimal_path['first_valid_point_id'].iloc[0]}")
        print(f"首个点位优先级: {optimal_path['first_point_priority'].iloc[0]}")
        print(f"综合评分: {optimal_path['total_score'].iloc[0]:.3f}")
        print(f"销量损失: {optimal_path['path_sale_loss'].iloc[0]:.2f}")
        print(f"路径时长: {optimal_path['path_duration'].iloc[0]:.2f}")
        print(f"补货点位数: {optimal_path['补货点位数'].iloc[0]}")
        print(f"补货率: {optimal_path['补货率'].iloc[0]:.3f}")
        
        return optimal_path
    
    def analyze_evaluation_results(self, df: pd.DataFrame) -> Dict:
        """分析评价结果"""
        analysis = {}
        
        # 基本统计
        analysis['总路径数'] = len(df)
        analysis['平均损失'] = df['path_sale_loss'].mean()
        analysis['平均耗时'] = df['path_duration'].mean()
        analysis['平均补货率'] = df['补货率'].mean()
        analysis['平均综合评分'] = df['total_score'].mean()
        
        # 评分分布
        analysis['损失评分分布'] = {
            'min': df['loss_score'].min(),
            'max': df['loss_score'].max(),
            'mean': df['loss_score'].mean(),
            'std': df['loss_score'].std()
        }
        
        analysis['时间评分分布'] = {
            'min': df['time_score'].min(),
            'max': df['time_score'].max(),
            'mean': df['time_score'].mean(),
            'std': df['time_score'].std()
        }
        
        analysis['补货评分分布'] = {
            'min': df['replenish_score'].min(),
            'max': df['replenish_score'].max(),
            'mean': df['replenish_score'].mean(),
            'std': df['replenish_score'].std()
        }
        
        # 最优路径分析
        best_path = df.loc[df['total_score'].idxmax()]
        analysis['最优路径'] = {
            'req_id': best_path['req_id'],
            'path': best_path['path'],
            'total_score': best_path['total_score'],
            'loss_score': best_path['loss_score'],
            'time_score': best_path['time_score'],
            'replenish_score': best_path['replenish_score'],
            'path_sale_loss': best_path['path_sale_loss'],
            'path_duration': best_path['path_duration'],
            '补货率': best_path['补货率']
        }
        
        return analysis

def load_and_evaluate_paths(file_path: str = 'data/all_path.csv') -> Tuple[pd.DataFrame, Dict]:
    """
    加载路径数据并进行评价
    
    Args:
        file_path: 路径数据文件路径
        
    Returns:
        评价后的DataFrame和分析结果
    """
    print("=== 加载路径数据 ===")
    df = pd.read_csv(file_path)
    
    print(f"总记录数: {len(df)}")
    print(f"唯一req_id数: {df['req_id'].nunique()}")
    
    # 创建评价器
    evaluator = PathEvaluator(
        loss_weight=0.7,
        time_weight=0.2,
        replenish_weight=0.1
    )
    
    print("\n=== 开始路径评价 ===")
    print(f"权重配置: 损失={evaluator.loss_weight}, 时间={evaluator.time_weight}, 补货={evaluator.replenish_weight}")
    
    # 评价路径
    evaluated_df = evaluator.evaluate_paths(df)
    
    # 分析结果
    analysis = evaluator.analyze_evaluation_results(evaluated_df)
    
    return evaluated_df, analysis

def print_analysis_results(analysis: Dict):
    """打印分析结果"""
    print("\n=== 评价结果分析 ===")
    print(f"总路径数: {analysis['总路径数']}")
    print(f"平均损失: {analysis['平均损失']:.2f}")
    print(f"平均耗时: {analysis['平均耗时']:.2f}")
    print(f"平均补货率: {analysis['平均补货率']:.3f}")
    print(f"平均综合评分: {analysis['平均综合评分']:.3f}")
    
    print("\n=== 评分分布 ===")
    print("损失评分分布:")
    for key, value in analysis['损失评分分布'].items():
        print(f"  {key}: {value:.3f}")
    
    print("时间评分分布:")
    for key, value in analysis['时间评分分布'].items():
        print(f"  {key}: {value:.3f}")
    
    print("补货评分分布:")
    for key, value in analysis['补货评分分布'].items():
        print(f"  {key}: {value:.3f}")
    
    print("\n=== 最优路径 ===")
    best = analysis['最优路径']
    print(f"req_id: {best['req_id']}")
    print(f"路径: {best['path']}")
    print(f"综合评分: {best['total_score']:.3f}")
    print(f"损失评分: {best['loss_score']:.3f}")
    print(f"时间评分: {best['time_score']:.3f}")
    print(f"补货评分: {best['replenish_score']:.3f}")
    print(f"实际损失: {best['path_sale_loss']:.2f}")
    print(f"实际耗时: {best['path_duration']:.2f}")
    print(f"实际补货率: {best['补货率']:.3f}")

def create_evaluation_visualizations(df: pd.DataFrame, output_dir: str = 'output'):
    """创建评价结果可视化图表"""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # 设置图表样式
    plt.style.use('default')
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Path Evaluation Analysis Results', fontsize=16, fontweight='bold')
    
    # 1. 综合评分分布
    axes[0, 0].hist(df['total_score'], bins=30, alpha=0.7, color='skyblue', edgecolor='black')
    axes[0, 0].set_title('Final Score Distribution')
    axes[0, 0].set_xlabel('Final Score')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].axvline(df['total_score'].mean(), color='red', linestyle='--', 
                       label=f'Mean: {df["total_score"].mean():.3f}')
    axes[0, 0].legend()
    
    # 2. 三项评分对比
    scores_data = [df['loss_score'], df['time_score'], df['replenish_score']]
    labels = ['Loss Score', 'Time Score', 'Replenish Score']
    box_plot = axes[0, 1].boxplot(scores_data, tick_labels=labels, patch_artist=True)
    colors = ['lightcoral', 'lightgreen', 'lightblue']
    for patch, color in zip(box_plot['boxes'], colors):
        patch.set_facecolor(color)
    axes[0, 1].set_title('Three Score Components Comparison')
    axes[0, 1].set_ylabel('Score')
    
    # 3. 损失vs时间散点图
    scatter = axes[1, 0].scatter(df['path_sale_loss'], df['path_duration'], 
                                c=df['total_score'], cmap='viridis', alpha=0.6)
    axes[1, 0].set_xlabel('Sales Loss')
    axes[1, 0].set_ylabel('Path Duration')
    axes[1, 0].set_title('Loss vs Time Scatter Plot (Color: Final Score)')
    plt.colorbar(scatter, ax=axes[1, 0], label='Final Score')
    
    # 4. 补货率vs综合评分
    axes[1, 1].scatter(df['补货率'], df['total_score'], alpha=0.6, color='orange')
    axes[1, 1].set_xlabel('Replenish Rate')
    axes[1, 1].set_ylabel('Final Score')
    axes[1, 1].set_title('Replenish Rate vs Final Score')
    
    # 添加趋势线
    z = np.polyfit(df['补货率'], df['total_score'], 1)
    p = np.poly1d(z)
    axes[1, 1].plot(df['补货率'], p(df['补货率']), "r--", alpha=0.8)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/path_evaluation_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 保存评价结果
    df.to_csv(f'{output_dir}/evaluated_paths.csv', index=False)
    print(f"评价结果已保存到 {output_dir}/")

def main():
    """主函数"""
    print("=== 智能配送路径综合评价系统 ===")
    
    # 加载和评价路径
    evaluated_df, analysis = load_and_evaluate_paths()
    
    # 打印分析结果
    print_analysis_results(analysis)
    
    # 显示前10个最优路径
    print("\n=== 前10个最优路径 ===")
    top_paths = evaluated_df.nlargest(10, 'total_score')
    print(top_paths[['req_id', 'path', 'path_opt', 'total_score', 'path_sale_loss', 'path_duration', '补货率']].to_string(index=False))
    
    # 创建评价器实例并获取基于优先级的最优路径
    evaluator = PathEvaluator()
    print("\n=== 基于优先级的最优路径选择 ===")
    optimal_path = evaluator.get_optimal_path_with_priority(evaluated_df)
    
    # 创建可视化
    #create_evaluation_visualizations(evaluated_df)
    
    print("\n=== 评价完成 ===")

if __name__ == "__main__":
    main() 