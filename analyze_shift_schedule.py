#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
早晚班分析脚本
根据出发时间计算早晚班，并更新到Excel文件中
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def calculate_shift_schedule(df):
    """
    根据车辆和出发时间计算早晚班
    """
    print("=" * 60)
    print("⏰ 早晚班分析")
    print("=" * 60)
    
    # 定义早晚班时间规则
    shift_rules = {
        'YQ 441 A': {
            '早班': {'start': '09:00', 'end': '20:59'},
            '晚班': {'start': '21:00', 'end': '08:59'}
        },
        'GBH 5351 M': {
            '早班': {'start': '08:00', 'end': '19:59'},
            '晚班': {'start': '20:00', 'end': '07:59'}
        },
        'YQ 5378 S': {
            '早班': {'start': '08:00', 'end': '19:59'},
            '晚班': {'start': '20:00', 'end': '07:59'}
        }
    }
    
    def determine_shift(row):
        """
        根据车辆和出发时间确定班次
        """
        car_number = row['car_number']
        departure_time = pd.to_datetime(row['出发时间'])
        hour = departure_time.hour
        
        # 虚拟车都是晚班
        if car_number not in shift_rules:
            return '晚班'
        
        # 真实车辆根据时间规则判断
        if car_number == 'YQ 441 A':
            if 9 <= hour <= 20:
                return '早班'
            else:
                return '晚班'
        else:  # GBH 5351 M 和 YQ 5378 S
            if 8 <= hour <= 19:
                return '早班'
            else:
                return '晚班'
    
    # 添加早晚班列
    df['班次'] = df.apply(determine_shift, axis=1)
    
    # 统计早晚班分布
    print("\n📊 早晚班分布统计:")
    shift_stats = df.groupby(['车辆类型', '班次']).size().unstack(fill_value=0)
    print(shift_stats)
    
    # 各车辆早晚班统计
    print("\n📈 各车辆早晚班统计:")
    vehicle_shift_stats = df.groupby(['car_number', '班次']).size().unstack(fill_value=0)
    print(vehicle_shift_stats)
    
    # 早晚班效率对比
    print("\n⚡ 早晚班效率对比:")
    shift_efficiency = df.groupby('班次').agg({
        '总耗时': ['mean', 'median', 'count'],
        '点位耗时': ['mean', 'median'],
        '总分拣数': ['mean', 'sum']
    }).round(2)
    print(shift_efficiency)
    
    # 各车辆早晚班效率对比
    print("\n🚗 各车辆早晚班效率对比:")
    for vehicle in df['car_number'].unique():
        if vehicle in ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A']:
            vehicle_data = df[df['car_number'] == vehicle]
            shift_efficiency = vehicle_data.groupby('班次')['总耗时'].mean()
            print(f"   {vehicle}:")
            for shift, avg_time in shift_efficiency.items():
                print(f"     {shift}: {avg_time:.2f}分钟")
    
    return df

def analyze_shift_patterns(df):
    """
    分析早晚班模式
    """
    print("\n" + "=" * 60)
    print("📊 早晚班模式分析")
    print("=" * 60)
    
    # 早晚班时间分布
    print("\n⏰ 早晚班时间分布:")
    df['出发小时'] = pd.to_datetime(df['出发时间']).dt.hour
    
    # 真实车辆早晚班时间分布
    real_vehicles = df[df['车辆类型'] == '真实车辆']
    print("\n📈 真实车辆早晚班时间分布:")
    for vehicle in real_vehicles['car_number'].unique():
        vehicle_data = real_vehicles[real_vehicles['car_number'] == vehicle]
        print(f"   {vehicle}:")
        for shift in ['早班', '晚班']:
            shift_data = vehicle_data[vehicle_data['班次'] == shift]
            if len(shift_data) > 0:
                hours = shift_data['出发小时'].value_counts().sort_index()
                print(f"     {shift}: {dict(hours)}")
    
    # 虚拟车时间分布
    virtual_data = df[df['车辆类型'] == '虚拟车']
    print(f"\n📈 虚拟车时间分布:")
    hours = virtual_data['出发小时'].value_counts().sort_index()
    print(f"   晚班: {dict(hours)}")

def save_updated_data(df, file_path):
    """
    保存更新后的数据到Excel文件
    """
    print("\n" + "=" * 60)
    print("💾 保存更新后的数据")
    print("=" * 60)
    
    # 创建备份文件名
    backup_path = file_path.replace('.xlsx', '_with_shifts.xlsx')
    
    try:
        # 保存更新后的数据
        df.to_excel(backup_path, index=False)
        print(f"✅ 成功保存更新后的数据到: {backup_path}")
        print(f"📊 数据形状: {df.shape}")
        print(f"📋 新增列: 班次")
        
        # 显示班次列的基本信息
        print(f"\n📈 班次列统计:")
        print(df['班次'].value_counts())
        
        return backup_path
        
    except Exception as e:
        print(f"❌ 保存数据时出错: {e}")
        return None

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
    
    try:
        # 读取Excel文件
        print("📖 读取原始数据...")
        df = pd.read_excel(file_path)
        print(f"✅ 成功读取数据: {df.shape}")
        
        # 处理缺失值
        df = df.dropna(subset=['car_number', '总耗时', '点位耗时', '出发时间'])
        print(f"📈 处理后数据形状: {df.shape}")
        
        # 车辆分类
        real_vehicles = ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A']
        df['车辆类型'] = df['car_number'].apply(lambda x: '真实车辆' if x in real_vehicles else '虚拟车')
        
        # 计算早晚班
        df = calculate_shift_schedule(df)
        
        # 分析早晚班模式
        analyze_shift_patterns(df)
        
        # 保存更新后的数据
        backup_path = save_updated_data(df, file_path)
        
        if backup_path:
            print("\n" + "=" * 60)
            print("🎯 总结")
            print("=" * 60)
            print("早晚班分析完成:")
            print("1. 成功添加班次列")
            print("2. 分析了早晚班分布和效率")
            print("3. 保存了更新后的数据文件")
            print("4. 为后续分析提供了时间维度")
        
    except Exception as e:
        print(f"❌ 处理数据时出错: {e}")

if __name__ == "__main__":
    main()
