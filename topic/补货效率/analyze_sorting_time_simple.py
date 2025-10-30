#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
点位分拣耗时数据分析脚本 - 简化版
分析货车到点位分拣的完整流程耗时
"""

import os
import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


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
    
    # 分析各环节耗时统计
    print("\n📈 各环节耗时统计:")
    print(f"   行驶时间 - 平均: {df['行驶时间'].mean():.2f} 分钟, 中位数: {df['行驶时间'].median():.2f} 分钟")
    print(f"   分拣时长 - 平均: {df['分拣时长(完成分拣时间-开始分拣时间)'].mean():.2f} 分钟, 中位数: {df['分拣时长(完成分拣时间-开始分拣时间)'].median():.2f} 分钟")
    print(f"   步行时长 - 平均: {df['货车步行至点位时长*2'].mean():.2f} 分钟, 中位数: {df['货车步行至点位时长*2'].median():.2f} 分钟")
    print(f"   上架时长 - 平均: {df['点位上架时长(点位完成上架时间-点位开始上架时间)'].mean():.2f} 分钟, 中位数: {df['点位上架时长(点位完成上架时间-点位开始上架时间)'].median():.2f} 分钟")
    
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
    if '盒菜数量' in df.columns:
        print(f"   平均盒菜数量: {df['盒菜数量'].mean():.1f}")
    if '饮料数量' in df.columns:
        print(f"   平均饮料数量: {df['饮料数量'].mean():.1f}")
    if '甜品数量' in df.columns:
        print(f"   平均甜品数量: {df['甜品数量'].mean():.1f}")
    if '总分拣数' in df.columns:
        print(f"   平均总分拣数: {df['总分拣数'].mean():.1f}")


def main():
    """
    主函数
    """
    # 文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "点位耗时_cleaned.csv")
    
    # 检查文件是否存在
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        return
    
    # 加载数据
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        analyze_key_metrics(df)
    except Exception as e:
        print(f"❌ 加载或分析数据时出错: {e}")


if __name__ == "__main__":
    main()
