#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆回CK时间分析脚本（修复版）
分析CSV数据，提取每个车辆每次回CK的完整时间序列
使用标准库csv模块避免pandas兼容性问题
"""

import csv
from datetime import datetime
import sys

def parse_datetime(time_str):
    """
    解析时间字符串
    
    Args:
        time_str: 时间字符串，格式为 'YYYY-MM-DD, HH:MM'
    
    Returns:
        datetime对象或None
    """
    if not time_str or time_str.strip() == '':
        return None
    
    try:
        return datetime.strptime(time_str.strip(), '%Y-%m-%d, %H:%M')
    except ValueError:
        return None

def analyze_ck_trips(csv_file):
    """
    分析车辆回CK的时间序列
    
    Args:
        csv_file: CSV文件路径
    
    Returns:
        list: 包含每个车辆每次回CK时间信息的列表
    """
    # 读取CSV数据
    data = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)  # 跳过标题行
        
        for row in reader:
            if len(row) >= 5:  # 确保有足够的列
                data.append({
                    'car_id': int(row[0]),
                    'point_id': int(row[1]),
                    'task_type': int(row[2]),
                    'outset_time': parse_datetime(row[3]),
                    'arrive_time': parse_datetime(row[4])
                })
    
    # 按车辆ID和时间排序
    data.sort(key=lambda x: (x['car_id'], x['outset_time'] or datetime.min))
    
    ck_trips = []
    
    # 按车辆分组处理
    current_car_id = None
    car_trips = []
    current_trip = None
    
    for row in data:
        car_id = row['car_id']
        
        # 如果切换到新车辆，保存当前车辆的行程
        if current_car_id != car_id:
            if current_trip is not None:
                car_trips.append(current_trip)
            ck_trips.extend(car_trips)
            car_trips = []
            current_trip = None
            current_car_id = car_id
        
        # 检查是否是回CK的任务
        if row['point_id'] == 0 and row['task_type'] == 8:  # 回CK任务
            if current_trip is None:
                # 开始新的回CK行程
                current_trip = {
                    'car_id': car_id,
                    'departure_time': row['outset_time'],
                    'arrival_time': row['arrive_time'],
                    'departure_from_ck_time': None
                }
            else:
                # 如果已经有未完成的行程，先保存它
                if current_trip['departure_from_ck_time'] is None:
                    car_trips.append(current_trip)
                current_trip = {
                    'car_id': car_id,
                    'departure_time': row['outset_time'],
                    'arrival_time': row['arrive_time'],
                    'departure_from_ck_time': None
                }
        
        # 检查是否是离开CK去执行任务（point_id!=0且task_type=4）
        elif row['point_id'] != 0 and row['task_type'] == 4:
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
    
    # 写入CSV文件
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        if csv_data:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
    
    print(f"结果已保存到 {output_file}")
    print(f"总计 {len(trips)} 次车辆回CK记录")
    
    # 显示前几行预览
    print("\n前10行预览:")
    for i, row in enumerate(csv_data[:10]):
        stay_time = str(row['在CK停留时长(分钟)'])
        print(f"{i+1:2d}. 车辆ID:{row['车辆ID']:2d} 出发:{row['出发回CK时间']:16s} 到达:{row['到达CK时间']:16s} 离开:{row['离开CK时间']:16s} 停留:{stay_time:3s}分钟")

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
