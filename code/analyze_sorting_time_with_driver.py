#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
点位分拣耗时数据分析脚本 - 包含司机信息
分析货车到点位分拣的完整流程耗时，包括司机维度分析
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def load_and_explore_data(file_path):
    """
    加载并探索Excel数据
    """
    print("=" * 60)
    print("📊 数据加载与探索")
    print("=" * 60)
    
    try:
        # 读取Excel文件
        df = pd.read_excel(file_path)
        print(f"✅ 成功加载数据文件: {file_path}")
        print(f"📈 数据形状: {df.shape}")
        print(f"📋 列名: {list(df.columns)}")
        
        # 显示前几行数据
        print("\n🔍 数据预览:")
        print(df.head())
        
        # 数据类型信息
        print("\n📊 数据类型信息:")
        print(df.dtypes)
        
        # 基本统计信息
        print("\n📈 数值列基本统计:")
        print(df.describe())
        
        # 检查缺失值
        print("\n❓ 缺失值检查:")
        missing_data = df.isnull().sum()
        if missing_data.sum() > 0:
            print(missing_data[missing_data > 0])
        else:
            print("✅ 无缺失值")
        
        return df
        
    except Exception as e:
        print(f"❌ 加载数据时出错: {e}")
        return None

def analyze_driver_performance(df):
    """
    分析司机绩效
    """
    print("\n" + "=" * 60)
    print("🚗 司机绩效分析")
    print("=" * 60)
    
    # 检查是否有司机列
    driver_columns = [col for col in df.columns if '司机' in col or 'driver' in col.lower()]
    
    if not driver_columns:
        print("⚠️ 未找到司机相关列")
        return
    
    driver_col = driver_columns[0]
    print(f"✅ 找到司机列: {driver_col}")
    
    # 司机基本信息
    print(f"\n📊 司机基本信息:")
    print(f"   司机总数: {df[driver_col].nunique()}")
    print(f"   司机列表: {df[driver_col].unique()}")
    
    # 各司机的工作量统计
    print(f"\n📈 各司机工作量统计:")
    driver_stats = df.groupby(driver_col).agg({
        'point_id': 'count',
        '总耗时': ['mean', 'median', 'min', 'max'],
        '点位耗时': ['mean', 'median'],
        '盒菜数量': 'sum',
        '饮料数量': 'sum',
        '甜品数量': 'sum',
        '总分拣数': 'sum'
    }).round(2)
    
    driver_stats.columns = ['点位数量', '平均总耗时', '中位数总耗时', '最短总耗时', '最长总耗时', 
                           '平均点位耗时', '中位数点位耗时', '总盒菜数', '总饮料数', '总甜品数', '总分拣数']
    
    print(driver_stats)
    
    # 司机效率排名
    print(f"\n🏆 司机效率排名 (按平均总耗时):")
    efficiency_ranking = driver_stats.sort_values('平均总耗时')
    for i, (driver, stats) in enumerate(efficiency_ranking.iterrows(), 1):
        print(f"   {i}. {driver}: {stats['平均总耗时']:.2f}分钟 (处理{stats['点位数量']}个点位)")
    
    # 司机异常值分析
    print(f"\n🚨 司机异常值分析:")
    for driver in df[driver_col].unique():
        driver_data = df[df[driver_col] == driver]
        
        # 总耗时异常值
        total_time = driver_data['总耗时']
        Q1 = total_time.quantile(0.25)
        Q3 = total_time.quantile(0.75)
        IQR = Q3 - Q1
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = driver_data[driver_data['总耗时'] > upper_bound]
        if len(outliers) > 0:
            print(f"   {driver}: {len(outliers)}条异常记录 (总耗时 > {upper_bound:.2f}分钟)")
            for _, row in outliers.head(3).iterrows():
                print(f"     - 点位{row['point_id']}: {row['当前点位']} - {row['总耗时']:.2f}分钟")

def analyze_data_structure(df):
    """
    分析数据结构
    """
    print("\n" + "=" * 60)
    print("🏗️ 数据结构分析")
    print("=" * 60)
    
    # 分析每列的含义和分布
    for col in df.columns:
        print(f"\n📋 列名: {col}")
        print(f"   数据类型: {df[col].dtype}")
        
        if df[col].dtype in ['object', 'string']:
            # 字符串列分析
            unique_values = df[col].nunique()
            print(f"   唯一值数量: {unique_values}")
            if unique_values <= 10:
                print(f"   唯一值: {df[col].unique()}")
            else:
                print(f"   前5个唯一值: {df[col].unique()[:5]}")
        elif df[col].dtype == 'datetime64[ns]':
            # datetime列分析
            print(f"   最小值: {df[col].min()}")
            print(f"   最大值: {df[col].max()}")
            print(f"   时间跨度: {df[col].max() - df[col].min()}")
        else:
            # 数值列分析
            print(f"   最小值: {df[col].min()}")
            print(f"   最大值: {df[col].max()}")
            print(f"   平均值: {df[col].mean():.2f}")
            print(f"   中位数: {df[col].median():.2f}")

def identify_time_columns(df):
    """
    识别时间相关的列
    """
    print("\n" + "=" * 60)
    print("⏱️ 时间列识别与分析")
    print("=" * 60)
    
    time_columns = []
    for col in df.columns:
        col_lower = col.lower()
        # 检查是否包含时间相关关键词
        time_keywords = ['时间', '耗时', '分钟', '秒', 'time', 'duration', 'minute', 'second']
        if any(keyword in col_lower for keyword in time_keywords):
            time_columns.append(col)
    
    if time_columns:
        print(f"🔍 识别到的时间相关列: {time_columns}")
        
        for col in time_columns:
            print(f"\n📊 {col} 分析:")
            print(f"   数据类型: {df[col].dtype}")
            
            if df[col].dtype == 'datetime64[ns]':
                # 处理datetime类型
                print(f"   最小值: {df[col].min()}")
                print(f"   最大值: {df[col].max()}")
                print(f"   时间跨度: {df[col].max() - df[col].min()}")
            else:
                # 处理数值类型
                print(f"   最小值: {df[col].min()}")
                print(f"   最大值: {df[col].max()}")
                print(f"   平均值: {df[col].mean():.2f}")
                print(f"   中位数: {df[col].median():.2f}")
                print(f"   标准差: {df[col].std():.2f}")
                
                # 检查异常值
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
                print(f"   异常值数量: {len(outliers)} ({len(outliers)/len(df)*100:.1f}%)")
    else:
        print("⚠️ 未识别到明显的时间相关列")
        print("请检查列名是否包含时间相关关键词")

def identify_process_steps(df):
    """
    识别分拣流程的各个步骤
    """
    print("\n" + "=" * 60)
    print("🔄 分拣流程步骤识别")
    print("=" * 60)
    
    # 预期的分拣流程步骤
    expected_steps = [
        "停车", "停车时间", "parking",
        "分拣", "分拣时间", "sorting", 
        "步行", "走路", "walking",
        "上架", "上架时间", "shelving",
        "返回", "返回时间", "return"
    ]
    
    identified_steps = []
    for col in df.columns:
        col_lower = col.lower()
        for step in expected_steps:
            if step in col_lower:
                identified_steps.append((col, step))
                break
    
    if identified_steps:
        print("✅ 识别到的流程步骤:")
        for col, step in identified_steps:
            print(f"   {col} -> {step}")
    else:
        print("⚠️ 未识别到明显的流程步骤列")
        print("请检查列名是否包含流程相关关键词")

def analyze_key_metrics(df):
    """
    分析关键指标
    """
    print("\n" + "=" * 60)
    print("📊 关键指标分析")
    print("=" * 60)
    
    # 分析总耗时分布
    print("\n📈 总耗时分析:")
    print(f"   平均总耗时: {df['总耗时'].mean():.2f} 分钟")
    print(f"   中位数总耗时: {df['总耗时'].median():.2f} 分钟")
    print(f"   最短总耗时: {df['总耗时'].min():.2f} 分钟")
    print(f"   最长总耗时: {df['总耗时'].max():.2f} 分钟")
    
    # 分析点位耗时分布
    print("\n📈 点位耗时分析:")
    print(f"   平均点位耗时: {df['点位耗时'].mean():.2f} 分钟")
    print(f"   中位数点位耗时: {df['点位耗时'].median():.2f} 分钟")
    print(f"   最短点位耗时: {df['点位耗时'].min():.2f} 分钟")
    print(f"   最长点位耗时: {df['点位耗时'].max():.2f} 分钟")
    
    # 分析各环节耗时占比
    print("\n📈 各环节耗时占比:")
    total_time = df['总耗时'].sum()
    driving_time = df['行驶时间'].sum()
    sorting_time = df['分拣时长(完成分拣时间-开始分拣时间)'].sum()
    walking_time = df['货车步行至点位时长*2'].sum()
    shelving_time = df['点位上架时长(点位完成上架时间-点位开始上架时间)'].sum()
    
    print(f"   行驶时间占比: {driving_time/total_time*100:.1f}%")
    print(f"   分拣时间占比: {sorting_time/total_time*100:.1f}%")
    print(f"   步行时间占比: {walking_time/total_time*100:.1f}%")
    print(f"   上架时间占比: {shelving_time/total_time*100:.1f}%")
    
    # 分析货物数量与耗时的关系
    print("\n📈 货物数量分析:")
    print(f"   平均盒菜数量: {df['盒菜数量'].mean():.1f}")
    print(f"   平均饮料数量: {df['饮料数量'].mean():.1f}")
    print(f"   平均甜品数量: {df['甜品数量'].mean():.1f}")
    print(f"   平均总分拣数: {df['总分拣数'].mean():.1f}")

def propose_analysis_plan():
    """
    提出分析计划
    """
    print("\n" + "=" * 60)
    print("🎯 分析思路与计划")
    print("=" * 60)
    
    analysis_dimensions = {
        "时间维度分析": [
            "各环节耗时分布分析",
            "总耗时与各环节耗时关系",
            "耗时异常值识别",
            "耗时趋势分析（如果有时间序列）"
        ],
        "空间维度分析": [
            "不同点位的耗时差异",
            "点位地理位置对耗时的影响",
            "点位类型（如机器数量、布局）对耗时的影响"
        ],
        "人员维度分析": [
            "不同司机的效率差异",
            "司机操作习惯对耗时的影响",
            "司机培训需求识别"
        ],
        "货物维度分析": [
            "盒菜、甜品、饮料数量与耗时的关系",
            "货物种类组合对耗时的影响",
            "单件货物处理时间分析"
        ],
        "流程优化分析": [
            "各环节耗时占比分析",
            "瓶颈环节识别",
            "并行操作可能性分析",
            "路径优化建议"
        ],
        "效率提升建议": [
            "基于数据的最优操作顺序",
            "设备配置优化建议",
            "人员操作标准化建议",
            "技术改进方向"
        ]
    }
    
    for dimension, items in analysis_dimensions.items():
        print(f"\n🔍 {dimension}:")
        for i, item in enumerate(items, 1):
            print(f"   {i}. {item}")
    
    print("\n" + "=" * 60)
    print("💡 优化方向预期")
    print("=" * 60)
    
    optimization_areas = [
        "🚚 货车停车位置优化 - 减少步行距离",
        "📦 货物分拣顺序优化 - 提高分拣效率", 
        "🏃 人员路径规划优化 - 减少无效移动",
        "🤖 机器布局优化 - 减少上架时间",
        "⏱️ 操作流程标准化 - 减少操作时间",
        "📊 货物预分拣 - 减少现场分拣时间",
        "🔄 并行操作设计 - 同时进行多个环节",
        "👨‍💼 司机培训优化 - 提升操作效率"
    ]
    
    for area in optimization_areas:
        print(f"   {area}")

def main():
    """
    主函数
    """
    # 文件路径
    file_path = "data/点位耗时.xlsx"
    
    # 检查文件是否存在
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        return
    
    # 加载数据
    df = load_and_explore_data(file_path)
    
    if df is not None:
        # 分析数据结构
        analyze_data_structure(df)
        
        # 识别时间相关列
        identify_time_columns(df)
        
        # 识别流程步骤
        identify_process_steps(df)
        
        # 分析关键指标
        analyze_key_metrics(df)
        
        # 分析司机绩效
        analyze_driver_performance(df)
        
        # 提出分析计划
        propose_analysis_plan()
        
        print("\n" + "=" * 60)
        print("🎯 下一步行动")
        print("=" * 60)
        print("基于以上分析，我们可以:")
        print("1. 根据实际数据结构调整分析维度")
        print("2. 针对关键环节进行深入分析")
        print("3. 识别具体的优化机会")
        print("4. 提出可执行的改进建议")
        print("5. 分析司机绩效差异和培训需求")

if __name__ == "__main__":
    main()
