#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析近一个月不同司机补货效率
基于 sorting_tasks 表
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add code directory to path to import lib
sys.path.append(os.path.join(os.getcwd(), 'code'))

from lib import create_db_connection

def analyze_driver_replenishment():
    print("正在连接数据库...")
    try:
        db = create_db_connection(mysql_database='smart_cooker_sg')
    except Exception as e:
        print(f"连接数据库失败: {e}")
        return

    print("正在查询最近30天的补货任务数据...")
    
    # Query for last 30 days
    # Note: using COALESCE to handle NULLs
    sql = """
        SELECT 
            op_name,
            sorting_start_time,
            sorting_duration_minutes,
            shelving_duration_minutes,
            veg_box_count,
            drink_count,
            dessert_count,
            point_id
        FROM sorting_tasks
        WHERE sorting_start_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
          AND op_name IS NOT NULL
          AND op_name != ''
    """
    
    results = db.execute_query(sql)
    
    if not results:
        print("未查询到数据。")
        return

    df = pd.DataFrame(results)
    
    print(f"查询到 {len(df)} 条记录。")
    
    # Data Preprocessing
    # Fill NaNs with 0 for counts and times
    cols_to_fill = ['sorting_duration_minutes', 'shelving_duration_minutes', 'veg_box_count', 'drink_count', 'dessert_count']
    for col in cols_to_fill:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    # Filter out invalid durations (negative values)
    # This usually indicates data errors
    initial_count = len(df)
    df = df[(df['sorting_duration_minutes'] >= 0) & (df['shelving_duration_minutes'] >= 0)]
    if len(df) < initial_count:
        print(f"⚠️ 已过滤 {initial_count - len(df)} 条时间异常(负数)的记录")

    # Calculate total items per task
    df['total_items'] = df['veg_box_count'] + df['drink_count'] + df['dessert_count']
    
    # Calculate total operation time per task
    df['total_time_minutes'] = df['sorting_duration_minutes'] + df['shelving_duration_minutes']
    
    # Avoid division by zero for efficiency calculation per task (if needed)
    # But we will aggregate first
    
    print("\n正在按司机聚合分析...")
    
    # Aggregation
    driver_stats = df.groupby('op_name').agg(
        working_days=('sorting_start_time', lambda x: x.dt.date.nunique()),
        total_tasks=('point_id', 'count'),
        total_items=('total_items', 'sum'),
        total_veg=('veg_box_count', 'sum'),
        total_drink=('drink_count', 'sum'),
        total_dessert=('dessert_count', 'sum'),
        total_time_minutes=('total_time_minutes', 'sum'),
        avg_sorting_time=('sorting_duration_minutes', 'mean'),
        avg_shelving_time=('shelving_duration_minutes', 'mean')
    )
    
    # Calculate Efficiency Metrics
    # Items per minute
    driver_stats['items_per_minute'] = driver_stats['total_items'] / driver_stats['total_time_minutes']
    
    # Handle division by zero if total_time is 0
    driver_stats['items_per_minute'] = driver_stats['items_per_minute'].replace([float('inf'), -float('inf')], 0).fillna(0)
    
    # Average items per task
    driver_stats['avg_items_per_task'] = driver_stats['total_items'] / driver_stats['total_tasks']
    
    # Sorting the result by efficiency (Items per minute) descending
    driver_stats = driver_stats.sort_values('items_per_minute', ascending=False)
    
    # Formatting for display
    display_df = driver_stats.copy()
    display_df['items_per_minute'] = display_df['items_per_minute'].round(2)
    display_df['avg_sorting_time'] = display_df['avg_sorting_time'].round(1)
    display_df['avg_shelving_time'] = display_df['avg_shelving_time'].round(1)
    display_df['avg_items_per_task'] = display_df['avg_items_per_task'].round(1)
    display_df['total_time_hours'] = (display_df['total_time_minutes'] / 60).round(1)
    
    # Select and Rename columns for clearer output
    output_cols = {
        'working_days': '工作天数',
        'total_tasks': '补货点位数',
        'total_items': '总补货量(件)',
        'items_per_minute': '效率(件/分)',
        'avg_items_per_task': '场均补货量',
        'total_time_hours': '总作业时长(小时)',
        'avg_sorting_time': '场均分拣(分)',
        'avg_shelving_time': '场均上架(分)'
    }
    
    print("\n" + "="*80)
    print("近一个月司机补货效率分析报告")
    print("="*80)
    print(display_df[output_cols.keys()].rename(columns=output_cols).to_markdown())
    print("\n注：效率 = 总补货量 / (分拣时间 + 上架时间)")
    
    # Additional Analysis: Box only efficiency (since box handling might be different from drinks)
    print("\n" + "-"*80)
    print("盒菜补货详情")
    driver_stats['box_efficiency'] = driver_stats['total_veg'] / driver_stats['total_time_minutes']
    box_display = driver_stats[['total_veg', 'box_efficiency']].copy()
    box_display['box_efficiency'] = box_display['box_efficiency'].round(2)
    box_display.columns = ['总盒菜数', '盒菜效率(盒/分)']
    print(box_display.sort_values('盒菜效率(盒/分)', ascending=False).to_markdown())

if __name__ == "__main__":
    analyze_driver_replenishment()

