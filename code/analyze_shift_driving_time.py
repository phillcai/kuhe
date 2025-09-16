#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
早晚班车辆行驶时长分析脚本
分析早晚班不同车辆的行驶时长差异
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def analyze_shift_driving_time(df):
    """
    分析早晚班不同车辆的行驶时长
    """
    print("=" * 60)
    print("⏰ 早晚班车辆行驶时长分析")
    print("=" * 60)
    
    # 检查必要列是否存在
    required_columns = ['car_number', '班次', '行驶时间']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"⚠️ 缺少必要列: {missing_columns}")
        return
    
    print(f"✅ 找到必要列: {required_columns}")
    
    # 车辆分类
    real_vehicles = ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A']
    df['车辆类型'] = df['car_number'].apply(lambda x: '真实车辆' if x in real_vehicles else '虚拟车')
    
    # 基本统计
    print(f"\n📊 基本统计:")
    print(f"   总记录数: {len(df)}")
    print(f"   车辆数量: {df['car_number'].nunique()}")
    print(f"   真实车辆: {df[df['车辆类型'] == '真实车辆']['car_number'].nunique()}辆")
    print(f"   虚拟车: {df[df['车辆类型'] == '虚拟车']['car_number'].nunique()}辆")
    
    return df

def analyze_driving_time_by_shift(df):
    """
    按班次分析行驶时长
    """
    print("\n" + "=" * 60)
    print("📈 班次行驶时长分析")
    print("=" * 60)
    
    # 班次基本统计
    shift_stats = df.groupby('班次')['行驶时间'].agg([
        'count', 'mean', 'median', 'std', 'min', 'max'
    ]).round(2)
    
    print(f"\n📊 班次行驶时长统计:")
    print(shift_stats)
    
    # 班次差异分析
    print(f"\n📊 班次差异分析:")
    for shift in ['早班', '晚班']:
        shift_data = df[df['班次'] == shift]
        print(f"   {shift}:")
        print(f"     记录数: {len(shift_data)}")
        print(f"     平均行驶时长: {shift_data['行驶时间'].mean():.2f}分钟")
        print(f"     中位数行驶时长: {shift_data['行驶时间'].median():.2f}分钟")
        print(f"     标准差: {shift_data['行驶时间'].std():.2f}分钟")
        print(f"     最短行驶时长: {shift_data['行驶时间'].min():.2f}分钟")
        print(f"     最长行驶时长: {shift_data['行驶时间'].max():.2f}分钟")
    
    # 班次差异检验
    morning_data = df[df['班次'] == '早班']['行驶时间']
    night_data = df[df['班次'] == '晚班']['行驶时间']
    
    diff = morning_data.mean() - night_data.mean()
    print(f"\n📊 班次差异:")
    print(f"   早班平均行驶时长: {morning_data.mean():.2f}分钟")
    print(f"   晚班平均行驶时长: {night_data.mean():.2f}分钟")
    print(f"   差异: {diff:.2f}分钟 ({'早班更长' if diff > 0 else '晚班更长'})")
    print(f"   差异百分比: {abs(diff)/morning_data.mean()*100:.1f}%")

def analyze_driving_time_by_vehicle(df):
    """
    按车辆分析行驶时长
    """
    print("\n" + "=" * 60)
    print("🚗 车辆行驶时长分析")
    print("=" * 60)
    
    # 各车辆行驶时长统计
    vehicle_stats = df.groupby('car_number')['行驶时间'].agg([
        'count', 'mean', 'median', 'std', 'min', 'max'
    ]).round(2)
    
    print(f"\n📊 各车辆行驶时长统计:")
    print(vehicle_stats)
    
    # 车辆行驶时长排名
    print(f"\n🏆 车辆行驶时长排名 (平均时长，越低越好):")
    avg_driving_time = vehicle_stats['mean'].sort_values()
    for i, (vehicle, time) in enumerate(avg_driving_time.items(), 1):
        print(f"   {i}. {vehicle}: {time:.2f}分钟")
    
    # 真实车辆 vs 虚拟车对比
    print(f"\n📊 车辆类型对比:")
    real_vehicles_data = df[df['车辆类型'] == '真实车辆']
    virtual_vehicles_data = df[df['车辆类型'] == '虚拟车']
    
    print(f"   真实车辆:")
    print(f"     平均行驶时长: {real_vehicles_data['行驶时间'].mean():.2f}分钟")
    print(f"     中位数行驶时长: {real_vehicles_data['行驶时间'].median():.2f}分钟")
    print(f"     标准差: {real_vehicles_data['行驶时间'].std():.2f}分钟")
    
    print(f"   虚拟车:")
    print(f"     平均行驶时长: {virtual_vehicles_data['行驶时间'].mean():.2f}分钟")
    print(f"     中位数行驶时长: {virtual_vehicles_data['行驶时间'].median():.2f}分钟")
    print(f"     标准差: {virtual_vehicles_data['行驶时间'].std():.2f}分钟")
    
    type_diff = real_vehicles_data['行驶时间'].mean() - virtual_vehicles_data['行驶时间'].mean()
    print(f"   差异: {type_diff:.2f}分钟 ({'真实车辆更长' if type_diff > 0 else '虚拟车更长'})")

def analyze_shift_vehicle_interaction(df):
    """
    分析班次与车辆的交互作用
    """
    print("\n" + "=" * 60)
    print("🔄 班次与车辆交互分析")
    print("=" * 60)
    
    # 各车辆早晚班行驶时长对比
    print(f"\n📊 各车辆早晚班行驶时长对比:")
    
    for vehicle in df['car_number'].unique():
        vehicle_data = df[df['car_number'] == vehicle]
        if len(vehicle_data) > 5:  # 只分析有足够数据的车辆
            print(f"\n   {vehicle}:")
            
            for shift in ['早班', '晚班']:
                shift_data = vehicle_data[vehicle_data['班次'] == shift]
                if len(shift_data) > 0:
                    print(f"     {shift}: {len(shift_data)}条记录, 平均{shift_data['行驶时间'].mean():.2f}分钟")
                else:
                    print(f"     {shift}: 无数据")
    
    # 真实车辆早晚班对比
    print(f"\n📊 真实车辆早晚班对比:")
    real_vehicles = ['GBH 5351 M', 'YQ 5378 S', 'YQ 441 A']
    
    for vehicle in real_vehicles:
        vehicle_data = df[df['car_number'] == vehicle]
        if len(vehicle_data) > 0:
            morning_data = vehicle_data[vehicle_data['班次'] == '早班']['行驶时间']
            night_data = vehicle_data[vehicle_data['班次'] == '晚班']['行驶时间']
            
            print(f"\n   {vehicle}:")
            if len(morning_data) > 0:
                print(f"     早班: {len(morning_data)}条, 平均{morning_data.mean():.2f}分钟")
            if len(night_data) > 0:
                print(f"     晚班: {len(night_data)}条, 平均{night_data.mean():.2f}分钟")
            
            if len(morning_data) > 0 and len(night_data) > 0:
                diff = morning_data.mean() - night_data.mean()
                print(f"     差异: {diff:.2f}分钟 ({'早班更长' if diff > 0 else '晚班更长'})")

def analyze_driving_time_outliers(df):
    """
    分析行驶时长异常值
    """
    print("\n" + "=" * 60)
    print("🚨 行驶时长异常值分析")
    print("=" * 60)
    
    # 整体异常值分析
    Q1 = df['行驶时间'].quantile(0.25)
    Q3 = df['行驶时间'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = df[(df['行驶时间'] < lower_bound) | (df['行驶时间'] > upper_bound)]
    
    print(f"\n📊 整体异常值分析:")
    print(f"   异常值标准: < {lower_bound:.2f} 或 > {upper_bound:.2f}")
    print(f"   异常值数量: {len(outliers)}条 ({len(outliers)/len(df)*100:.1f}%)")
    
    # 按班次统计异常值
    print(f"\n📊 班次异常值统计:")
    for shift in ['早班', '晚班']:
        shift_data = df[df['班次'] == shift]
        shift_outliers = shift_data[(shift_data['行驶时间'] < lower_bound) | (shift_data['行驶时间'] > upper_bound)]
        print(f"   {shift}: {len(shift_outliers)}条异常记录 ({len(shift_outliers)/len(shift_data)*100:.1f}%)")
    
    # 按车辆统计异常值
    print(f"\n📊 车辆异常值统计:")
    for vehicle in df['car_number'].unique():
        vehicle_data = df[df['car_number'] == vehicle]
        vehicle_outliers = vehicle_data[(vehicle_data['行驶时间'] < lower_bound) | (vehicle_data['行驶时间'] > upper_bound)]
        if len(vehicle_outliers) > 0:
            print(f"   {vehicle}: {len(vehicle_outliers)}条异常记录 ({len(vehicle_outliers)/len(vehicle_data)*100:.1f}%)")

def analyze_driving_time_factors(df):
    """
    分析影响行驶时长的因素
    """
    print("\n" + "=" * 60)
    print("🔍 行驶时长影响因素分析")
    print("=" * 60)
    
    # 行驶时长与总耗时的关系
    if '总耗时' in df.columns:
        driving_total_corr = df['行驶时间'].corr(df['总耗时'])
        print(f"\n📊 行驶时长与总耗时关系:")
        print(f"   相关系数: {driving_total_corr:.3f}")
        
        # 行驶时长占比
        df['行驶时长占比'] = df['行驶时间'] / df['总耗时']
        avg_driving_ratio = df['行驶时长占比'].mean()
        print(f"   平均行驶时长占比: {avg_driving_ratio:.2%}")
        
        # 按班次分析行驶时长占比
        print(f"\n📊 班次行驶时长占比:")
        for shift in ['早班', '晚班']:
            shift_data = df[df['班次'] == shift]
            shift_ratio = shift_data['行驶时长占比'].mean()
            print(f"   {shift}: {shift_ratio:.2%}")
    
    # 行驶时长与货物数量的关系
    if '总分拣数' in df.columns:
        driving_cargo_corr = df['行驶时间'].corr(df['总分拣数'])
        print(f"\n📊 行驶时长与货物数量关系:")
        print(f"   相关系数: {driving_cargo_corr:.3f}")
        
        # 按货物数量区间分析
        df['货物数量区间'] = pd.cut(df['总分拣数'], 
                                   bins=[0, 50, 100, 150, 1000], 
                                   labels=['0-50件', '50-100件', '100-150件', '150+件'])
        
        print(f"\n📊 不同货物数量区间的行驶时长:")
        for interval in df['货物数量区间'].unique():
            if pd.notna(interval):
                interval_data = df[df['货物数量区间'] == interval]
                if len(interval_data) > 0:
                    print(f"   {interval}: {len(interval_data)}条, 平均{interval_data['行驶时间'].mean():.2f}分钟")

def save_driving_time_analysis(df, file_path):
    """
    保存行驶时长分析结果
    """
    print("\n" + "=" * 60)
    print("💾 保存行驶时长分析结果")
    print("=" * 60)
    
    # 创建结果文件名
    result_path = file_path.replace('.xlsx', '_driving_time_analysis.xlsx')
    
    try:
        # 保存分析结果
        df.to_excel(result_path, index=False)
        print(f"✅ 成功保存行驶时长分析结果到: {result_path}")
        print(f"📊 数据形状: {df.shape}")
        
        return result_path
        
    except Exception as e:
        print(f"❌ 保存数据时出错: {e}")
        return None

def main():
    """
    主函数
    """
    # 文件路径
    file_path = "data/点位耗时_with_shifts.xlsx"
    
    # 检查文件是否存在
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        return
    
    try:
        # 读取Excel文件
        print("📖 读取数据...")
        df = pd.read_excel(file_path)
        print(f"✅ 成功读取数据: {df.shape}")
        
        # 处理缺失值
        df = df.dropna(subset=['car_number', '班次', '行驶时间'])
        print(f"📈 处理后数据形状: {df.shape}")
        
        # 分析早晚班车辆行驶时长
        df = analyze_shift_driving_time(df)
        
        # 按班次分析行驶时长
        analyze_driving_time_by_shift(df)
        
        # 按车辆分析行驶时长
        analyze_driving_time_by_vehicle(df)
        
        # 分析班次与车辆的交互作用
        analyze_shift_vehicle_interaction(df)
        
        # 分析行驶时长异常值
        analyze_driving_time_outliers(df)
        
        # 分析影响行驶时长的因素
        analyze_driving_time_factors(df)
        
        # 保存分析结果
        result_path = save_driving_time_analysis(df, file_path)
        
        if result_path:
            print("\n" + "=" * 60)
            print("🎯 总结")
            print("=" * 60)
            print("早晚班车辆行驶时长分析完成:")
            print("1. 分析了早晚班行驶时长差异")
            print("2. 比较了不同车辆的行驶时长")
            print("3. 分析了班次与车辆的交互作用")
            print("4. 识别了行驶时长异常值")
            print("5. 分析了影响行驶时长的因素")
            print("6. 保存了详细的分析结果")
        
    except Exception as e:
        print(f"❌ 处理数据时出错: {e}")

if __name__ == "__main__":
    main()
