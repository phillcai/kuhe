#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析指定车辆的月度补货效率指标
车辆：'YQ 441 A', 'YQ 5378 S', 'GBH 5351 M'
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Add code directory to path to import lib
sys.path.append(os.path.join(os.getcwd(), 'code'))

from lib import create_db_connection

def analyze_monthly_vehicle_stats():
    print("正在连接数据库...")
    try:
        db = create_db_connection(mysql_database='smart_cooker_sg')
    except Exception as e:
        print(f"连接数据库失败: {e}")
        return

    target_vehicles = ['YQ 441 A', 'YQ 5378 S', 'GBH 5351 M']
    vehicles_sql_list = "', '".join(target_vehicles)
    
    print(f"正在查询 {', '.join(target_vehicles)} 最近90天的补货任务数据...")
    
    sql = f"""
    WITH time_diffs AS (
        SELECT
          a.*,
          b.outset_time AS '出发时间',
          b.arrive_time AS '到达时间',
          TIMESTAMPDIFF(MINUTE, b.outset_time, b.arrive_time) AS '行驶时间',
          TIMESTAMPDIFF(MINUTE, b.arrive_time, b.finish_shelve) +  a.`货车步行至点位时长` AS '点位耗时',
          TIMESTAMPDIFF(MINUTE, b.outset_time, b.finish_shelve) +  a.`货车步行至点位时长` AS '总耗时'
        FROM
          (
            SELECT
              id,
              batch_no,
              car_number,
              point_id,
              current_point AS '当前点位',
              sorting_start_time,
              sorting_end_time AS '分拣完成时间',
              sorting_duration_minutes AS '分拣时长',
              walking_time_to_point AS '货车步行至点位时长',
              shelving_finish_time AS '点位完成上架时间',
              shelving_duration_minutes AS '点位上架时长',
              veg_box_count AS '盒菜数量',
              drink_count AS '饮料数量',
              dessert_count AS '甜品数量',
              (COALESCE(veg_box_count, 0) + COALESCE(drink_count, 0) + COALESCE(dessert_count, 0)) AS '总货品数',
              op_name
            FROM
              sorting_tasks
            WHERE
              sorting_start_time >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
              AND car_number IN ('{vehicles_sql_list}')
          ) a
          LEFT JOIN (
            SELECT
              batch_no,
              point_id,
              outset_time,
              arrive_time,
              finish_shelve
            FROM
              central_kitchen_car_task
            WHERE
              task_type = 4
              AND op_state = 3
          ) b ON a.batch_no = b.batch_no
          AND a.point_id = b.point_id
    )
    SELECT
      t.car_number,
      t.sorting_start_time,
      t.`总耗时` AS total_duration,
      t.`行驶时间` AS driving_duration,
      t.`分拣时长` AS sorting_duration,
      t.`点位上架时长` AS shelving_duration,
      t.`盒菜数量` AS veg_count,
      t.`饮料数量` AS drink_count,
      t.`甜品数量` AS dessert_count,
      t.`总货品数` AS total_items
    FROM
      time_diffs t
    ORDER BY
      t.sorting_start_time DESC
    """
    
    results = db.execute_query(sql)
    
    if not results:
        print("未查询到数据。")
        return

    df = pd.DataFrame(results)
    print(f"查询到 {len(df)} 条记录。")
    
    # Data Cleaning
    cols_to_fill = ['total_duration', 'driving_duration', 'sorting_duration', 'shelving_duration', 'veg_count', 'drink_count', 'dessert_count', 'total_items']
    for col in cols_to_fill:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Filter negative durations
    df = df[
        (df['total_duration'] >= 0) & 
        (df['driving_duration'] >= 0) &
        (df['sorting_duration'] >= 0) &
        (df['shelving_duration'] >= 0)
    ]

    # Convert sorting_start_time to Month
    df['sorting_start_time'] = pd.to_datetime(df['sorting_start_time'])
    df['month'] = df['sorting_start_time'].dt.strftime('%Y-%m')
    
    # Filter out August data
    df = df[df['month'] != '2025-08']
    
    print("\n正在按月聚合分析...")
    
    metrics = {
        'total_duration': '总耗时',
        'driving_duration': '行驶时间',
        'sorting_duration': '分拣时长',
        'shelving_duration': '点位上架时长',
        'veg_count': '平均盒菜数',
        'total_items': '平均分拣货品数'
    }
    
    monthly_stats = df.groupby('month').agg({
        'total_duration': ['mean', 'median', 'count'],
        'driving_duration': ['mean', 'median'],
        'sorting_duration': ['mean', 'median'],
        'shelving_duration': ['mean', 'median'],
        'veg_count': ['mean', 'median'],
        'total_items': ['mean', 'median']
    }).round(2)
    
    # Flatten columns
    monthly_stats.columns = ['_'.join(col).strip() for col in monthly_stats.columns.values]
    
    # Format output table
    print("\n" + "="*100)
    print("车辆月度补货效率指标统计")
    print(f"车辆: {', '.join(target_vehicles)}")
    print("="*100)
    
    # Create a unified table with all months
    months = sorted(df['month'].unique(), reverse=True)
    
    # Build the comparison table - Mean values
    print("\n【平均值】")
    mean_data = []
    
    for metric_key, metric_name in metrics.items():
        row = {'指标': metric_name}
        
        for month in months:
            mean_val = monthly_stats.loc[month, f'{metric_key}_mean']
            # 所有数值统一保留2位小数
            row[month] = round(mean_val, 2)
            
        mean_data.append(row)
    
    # Add sample count row
    sample_row = {'指标': '样本数'}
    for month in months:
        count = int(monthly_stats.loc[month, 'total_duration_count'])
        sample_row[month] = count
    mean_data.append(sample_row)
    
    mean_df = pd.DataFrame(mean_data)
    print(mean_df.to_markdown(index=False))
    
    # Save Mean CSV
    output_dir = os.path.dirname(os.path.abspath(__file__))
    mean_csv_path = os.path.join(output_dir, 'monthly_vehicle_stats_mean.csv')
    mean_df.to_csv(mean_csv_path, index=False, encoding='utf-8-sig')
    print(f"\n平均值统计已保存至: {mean_csv_path}")
    
    # Build the comparison table - Median values
    print("\n【中位数】")
    median_data = []
    
    for metric_key, metric_name in metrics.items():
        row = {'指标': metric_name}
        
        for month in months:
            median_val = monthly_stats.loc[month, f'{metric_key}_median']
            # 所有数值统一保留2位小数
            row[month] = round(median_val, 2)
            
        median_data.append(row)
    
    median_df = pd.DataFrame(median_data)
    print(median_df.to_markdown(index=False))

    # Save Median CSV
    median_csv_path = os.path.join(output_dir, 'monthly_vehicle_stats_median.csv')
    median_df.to_csv(median_csv_path, index=False, encoding='utf-8-sig')
    print(f"中位数统计已保存至: {median_csv_path}")
    
    print("\n注：时间单位为分钟，货品数单位为件/盒")


if __name__ == "__main__":
    analyze_monthly_vehicle_stats()

