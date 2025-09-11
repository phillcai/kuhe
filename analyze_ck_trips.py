#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆回CK时间分析脚本
分析CSV数据，提取每个车辆每次回CK的完整时间序列
"""

import pandas as pd
from datetime import datetime
import sys

def analyze_ck_trips(csv_file):
    """
    分析车辆回CK的时间序列
    
    Args:
        csv_file: CSV文件路径
    
    Returns:
        list: 包含每个车辆每次回CK时间信息的列表
    """
    # 读取CSV数据
    df = pd.read_csv(csv_file)
    
    # 转换时间格式
    df['outset_time'] = pd.to_datetime(df['outset_time'], format='%Y-%m-%d, %H:%M')
    df['arrive_time'] = pd.to_datetime(df['arrive_time'], format='%Y-%m-%d, %H:%M', errors='coerce')
    
    # 按车辆ID和时间排序
    df = df.sort_values(['car_id', 'outset_time'])
    
    ck_trips = []
    
    # 按车辆分组处理
    for car_id, car_data in df.groupby('car_id'):
        car_trips = []
        current_trip = None
        
        for _, row in car_data.iterrows():
            # 检查是否是回CK的任务
            if row['point_id'] == 0 and row['task_type'] == 8:  # 回CK任务
                if current_trip is None:
                    # 开始新的回CK行程
                    current_trip = {
                        'car_id': car_id,
                        'departure_time': row['outset_time'],
                        'arrival_time': row['arrive_time'] if pd.notna(row['arrive_time']) else None,
                        'departure_from_ck_time': None
                    }
                else:
                    # 如果已经有未完成的行程，先保存它
                    if current_trip['departure_from_ck_time'] is None:
                        car_trips.append(current_trip)
                    current_trip = {
                        'car_id': car_id,
                        'departure_time': row['outset_time'],
                        'arrival_time': row['arrive_time'] if pd.notna(row['arrive_time']) else None,
                        'departure_from_ck_time': None
                    }
            
            # 检查是否是离开CK的任务
            elif row['point_id'] == 0 and row['task_type'] in [2, 3]:  # 离开CK任务
                if current_trip is not None and current_trip['departure_from_ck_time'] is None:
                    current_trip['departure_from_ck_time'] = row['outset_time']
                    car_trips.append(current_trip)
                    current_trip = None
        
        # 处理最后一个未完成的行程
        if current_trip is not None:
            car_trips.append(current_trip)
        
        ck_trips.extend(car_trips)
    
    return ck_trips

def format_output(trips, output_file='ck_trips_analysis.csv'):
    """
    格式化输出结果为CSV格式
    
    Args:
        trips: 车辆回CK时间信息列表
        output_file: 输出CSV文件名
    """
    # 准备CSV数据
    csv_data = []
    for trip in trips:
        # 计算在CK停留时长（分钟）
        stay_duration = None
        if trip['arrival_time'] and trip['departure_from_ck_time']:
            duration = trip['departure_from_ck_time'] - trip['arrival_time']
            stay_duration = int(duration.total_seconds() / 60)  # 转换为分钟
        
        csv_data.append({
            '车辆ID': trip['car_id'],
            '出发回CK时间': trip['departure_time'].strftime('%Y-%m-%d %H:%M') if trip['departure_time'] else 'N/A',
            '到达CK时间': trip['arrival_time'].strftime('%Y-%m-%d %H:%M') if trip['arrival_time'] else 'N/A',
            '离开CK时间': trip['departure_from_ck_time'].strftime('%Y-%m-%d %H:%M') if trip['departure_from_ck_time'] else 'N/A',
            '在CK停留时长(分钟)': stay_duration if stay_duration is not None else 'N/A'
        })
    
    # 创建DataFrame并保存为CSV
    df_output = pd.DataFrame(csv_data)
    df_output.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"结果已保存到 {output_file}")
    print(f"总计 {len(trips)} 次车辆回CK记录")
    
    # 同时显示前几行预览
    print("\n前10行预览:")
    print(df_output.head(10).to_string(index=False))

def main():
    """主函数"""
    csv_file = 'data/ck.csv'
    
    try:
        trips = analyze_ck_trips(csv_file)
        format_output(trips)
        
        print(f"\n总计找到 {len(trips)} 次车辆回CK记录")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
