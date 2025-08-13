#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补货量优化分析 - 目标：将平均补货量从57.56盒提升到70盒
分析具体的实施策略和动作方案
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def analyze_current_situation(df):
    """
    分析当前情况，识别提升空间
    """
    print("="*60)
    print("当前补货情况分析 - 目标：平均补货量提升到70盒")
    print("="*60)
    
    current_avg = df['盒菜数量'].mean()
    target_avg = 70
    improvement_needed = target_avg - current_avg
    improvement_pct = (improvement_needed / current_avg) * 100
    
    print(f"📊 基础数据:")
    print(f"   当前平均补货量: {current_avg:.2f} 盒")
    print(f"   目标平均补货量: {target_avg} 盒") 
    print(f"   需要提升: {improvement_needed:.2f} 盒 ({improvement_pct:.1f}%)")
    
    return current_avg, target_avg, improvement_needed

def identify_optimization_opportunities(df):
    """
    识别优化机会点
    """
    print(f"\n🎯 优化机会识别:")
    
    # 1. 低补货量点位分析
    low_quantity_threshold = 50
    low_quantity_records = df[df['盒菜数量'] < low_quantity_threshold]
    
    print(f"\n1️⃣ 低补货量记录分析 (<{low_quantity_threshold}盒):")
    print(f"   记录数: {len(low_quantity_records)} ({len(low_quantity_records)/len(df)*100:.1f}%)")
    print(f"   平均补货量: {low_quantity_records['盒菜数量'].mean():.1f} 盒")
    print(f"   提升潜力: 如果这些记录提升到50盒，整体平均可增加 {(len(low_quantity_records) * (50 - low_quantity_records['盒菜数量'].mean())) / len(df):.2f} 盒")
    
    # 2. 高频低量点位
    location_stats = df.groupby('当前点位')['盒菜数量'].agg(['count', 'mean']).round(2)
    high_freq_low_qty = location_stats[(location_stats['count'] >= 10) & (location_stats['mean'] < 55)]
    
    print(f"\n2️⃣ 高频低量点位 (≥10次补货且平均<55盒):")
    print(f"   点位数量: {len(high_freq_low_qty)}")
    if len(high_freq_low_qty) > 0:
        print("   重点优化点位:")
        for idx, (location, data) in enumerate(high_freq_low_qty.head(5).iterrows()):
            potential_increase = (60 - data['mean']) * data['count'] / len(df)
            print(f"   {idx+1}. {location[:40]}... - 补货{data['count']}次, 平均{data['mean']}盒")
            print(f"      提升到60盒可增加整体平均: {potential_increase:.2f} 盒")
    
    # 3. 车辆效率分析
    vehicle_stats = df.groupby('car_number')['盒菜数量'].agg(['count', 'mean']).round(2)
    low_efficiency_vehicles = vehicle_stats[(vehicle_stats['count'] >= 50) & (vehicle_stats['mean'] < 60)]
    
    print(f"\n3️⃣ 低效率车辆 (≥50次补货且平均<60盒):")
    if len(low_efficiency_vehicles) > 0:
        for idx, (vehicle, data) in enumerate(low_efficiency_vehicles.iterrows()):
            potential_increase = (65 - data['mean']) * data['count'] / len(df)
            print(f"   {idx+1}. {vehicle} - 补货{data['count']}次, 平均{data['mean']}盒")
            print(f"      提升到65盒可增加整体平均: {potential_increase:.2f} 盒")
    
    return low_quantity_records, high_freq_low_qty, low_efficiency_vehicles

def calculate_specific_actions(df, low_quantity_records, high_freq_low_qty, low_efficiency_vehicles):
    """
    计算具体的实施动作和预期效果
    """
    print(f"\n📋 具体实施动作方案:")
    
    total_potential_increase = 0
    
    # 动作1: 提升低补货量记录
    if len(low_quantity_records) > 0:
        action1_target = 55  # 将<50盒的记录提升到55盒
        action1_increase = (len(low_quantity_records) * (action1_target - low_quantity_records['盒菜数量'].mean())) / len(df)
        total_potential_increase += action1_increase
        
        print(f"\n🎯 动作1: 提升低补货量记录")
        print(f"   目标: 将{len(low_quantity_records)}个<50盒的记录提升到{action1_target}盒")
        print(f"   预期效果: 整体平均增加 {action1_increase:.2f} 盒")
        print(f"   实施要点:")
        print(f"   • 分析低补货量原因（库存不足、需求预测偏低、运输限制等）")
        print(f"   • 优化库存管理，确保充足库存")
        print(f"   • 调整需求预测模型，避免低估")
    
    # 动作2: 优化高频低量点位
    if len(high_freq_low_qty) > 0:
        action2_target = 65  # 将高频低量点位提升到65盒
        action2_records = df[df['当前点位'].isin(high_freq_low_qty.index)]
        action2_increase = (len(action2_records) * (action2_target - action2_records['盒菜数量'].mean())) / len(df)
        total_potential_increase += action2_increase
        
        print(f"\n🎯 动作2: 优化高频低量点位")
        print(f"   目标: 将{len(high_freq_low_qty)}个高频点位平均补货量提升到{action2_target}盒")
        print(f"   预期效果: 整体平均增加 {action2_increase:.2f} 盒")
        print(f"   实施要点:")
        print(f"   • 深度调研这些点位的实际需求容量")
        print(f"   • 分析是否存在设备或空间限制")
        print(f"   • 考虑增加补货频次，减少缺货风险")
    
    # 动作3: 车辆路线优化
    if len(low_efficiency_vehicles) > 0:
        action3_target = 65  # 将低效车辆平均补货量提升到65盒
        action3_records = df[df['car_number'].isin(low_efficiency_vehicles.index)]
        action3_increase = (len(action3_records) * (action3_target - action3_records['盒菜数量'].mean())) / len(df)
        total_potential_increase += action3_increase
        
        print(f"\n🎯 动作3: 车辆路线优化")
        print(f"   目标: 将低效车辆平均补货量提升到{action3_target}盒")
        print(f"   预期效果: 整体平均增加 {action3_increase:.2f} 盒")
        print(f"   实施要点:")
        print(f"   • 重新规划车辆路线，优化高低需求点位搭配")
        print(f"   • 调整车辆载货策略，提高单次配送效率")
        print(f"   • 培训司机，提升操作效率")
    
    # 动作4: 时段优化
    try:
        # 提取小时并处理缺失值
        hour_extracted = df['出发时间'].str.extract(r'(\d+):')[0]
        hour_extracted = pd.to_numeric(hour_extracted, errors='coerce')
        valid_hours = ~hour_extracted.isna()
        
        if valid_hours.sum() > 0:
            hourly_stats = df[valid_hours].groupby(hour_extracted[valid_hours].astype(int))['盒菜数量'].mean()
            low_hour_avg = hourly_stats[hourly_stats < 55]
            
            if len(low_hour_avg) > 0:
                action4_records = df[valid_hours & hour_extracted.astype(int).isin(low_hour_avg.index)]
                if len(action4_records) > 0:
                    action4_increase = (len(action4_records) * (60 - action4_records['盒菜数量'].mean())) / len(df)
                    total_potential_increase += action4_increase
                    
                    print(f"\n🎯 动作4: 时段优化")
                    print(f"   目标: 优化低效时段的补货策略")
                    print(f"   预期效果: 整体平均增加 {action4_increase:.2f} 盒")
                    print(f"   实施要点:")
                    print(f"   • 将高需求点位安排到高效时段")
                    print(f"   • 低效时段重点服务高容量点位")
                    print(f"   • 调整作业时间，避开交通高峰")
    except Exception as e:
        print(f"\n⚠️  时段分析跳过（数据格式问题）: {str(e)}")
    
    return total_potential_increase

def create_optimization_roadmap():
    """
    创建优化路线图
    """
    print(f"\n🗺️  优化实施路线图:")
    
    phases = [
        {
            "阶段": "第1阶段 (1-2个月)",
            "目标": "快速提升到62盒",
            "动作": [
                "• 立即调整明显偏低的补货量记录",
                "• 优化库存管理，减少缺货情况", 
                "• 培训团队，提高补货标准意识",
                "• 建立补货量监控机制"
            ]
        },
        {
            "阶段": "第2阶段 (3-4个月)", 
            "目标": "稳步提升到66盒",
            "动作": [
                "• 深度优化高频低量点位",
                "• 重新规划车辆路线",
                "• 引入数据驱动的需求预测",
                "• 优化时段分配策略"
            ]
        },
        {
            "阶段": "第3阶段 (5-6个月)",
            "目标": "达成目标70盒",
            "动作": [
                "• 精细化运营管理",
                "• 建立智能补货系统",
                "• 持续优化和调整",
                "• 建立长期监控机制"
            ]
        }
    ]
    
    for phase in phases:
        print(f"\n📅 {phase['阶段']}")
        print(f"   🎯 {phase['目标']}")
        for action in phase['动作']:
            print(f"   {action}")

def risk_analysis():
    """
    风险分析和应对策略
    """
    print(f"\n⚠️  风险分析与应对:")
    
    risks = [
        {
            "风险": "库存压力增加",
            "影响": "补货量增加可能导致库存积压",
            "应对": "• 优化库存周转管理\n   • 建立动态库存预警机制\n   • 加强需求预测精度"
        },
        {
            "风险": "运输成本上升", 
            "影响": "单次补货量增加可能增加运输成本",
            "应对": "• 优化路线规划，提高配送效率\n   • 平衡补货频次与单次补货量\n   • 考虑规模效应降低单位成本"
        },
        {
            "风险": "点位容量限制",
            "影响": "部分点位可能无法承受更大补货量", 
            "应对": "• 实地调研点位实际容量\n   • 差异化补货策略\n   • 考虑设备升级或扩容"
        },
        {
            "风险": "需求波动",
            "影响": "补货量增加后可能面临需求不足风险",
            "应对": "• 建立弹性补货机制\n   • 加强市场需求监控\n   • 建立快速调整机制"
        }
    ]
    
    for risk in risks:
        print(f"\n🚨 {risk['风险']}")
        print(f"   影响: {risk['影响']}")
        print(f"   应对策略:")
        print(f"   {risk['应对']}")

def main():
    """
    主函数
    """
    print("开始分析补货量优化策略...")
    
    # 加载数据
    df = pd.read_csv('/Users/admin/Code/MyCode/kuhe/data/点位补货.csv')
    
    # 分析当前情况
    current_avg, target_avg, improvement_needed = analyze_current_situation(df)
    
    # 识别优化机会
    low_quantity_records, high_freq_low_qty, low_efficiency_vehicles = identify_optimization_opportunities(df)
    
    # 计算具体动作
    total_potential_increase = calculate_specific_actions(df, low_quantity_records, high_freq_low_qty, low_efficiency_vehicles)
    
    # 评估可行性
    print(f"\n✅ 可行性评估:")
    print(f"   通过以上动作，预期可增加平均补货量: {total_potential_increase:.2f} 盒")
    print(f"   预期达成平均补货量: {current_avg + total_potential_increase:.2f} 盒")
    
    if current_avg + total_potential_increase >= target_avg:
        print(f"   🎉 目标可以达成！")
    else:
        gap = target_avg - (current_avg + total_potential_increase)
        print(f"   ⚠️  仍有 {gap:.2f} 盒的差距，需要额外措施")
    
    # 实施路线图
    create_optimization_roadmap()
    
    # 风险分析
    risk_analysis()
    
    print(f"\n📊 总结:")
    print(f"   当前平均: {current_avg:.2f} 盒")
    print(f"   目标平均: {target_avg} 盒")
    print(f"   预期达成: {current_avg + total_potential_increase:.2f} 盒")
    print(f"   成功概率: {'高' if current_avg + total_potential_increase >= target_avg else '中等'}")

if __name__ == "__main__":
    main()
