#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重点分析 Yee Meng, Zhang Kai, Zhang Xiao Liang 的盒菜补货情况
按班次聚合
Yee Meng: 21:00 - 09:00
Others: 20:00 - 08:00
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Add code directory to path to import lib
sys.path.append(os.path.join(os.getcwd(), 'code'))

from lib import create_db_connection

def analyze_focused_shift_boxes():
    print("正在连接数据库...")
    try:
        db = create_db_connection(mysql_database='smart_cooker_sg')
    except Exception as e:
        print(f"连接数据库失败: {e}")
        return

    target_drivers = ['Yee Meng', 'Zhang Kai', 'Zhang Xiao Liang']
    drivers_sql_list = "', '".join(target_drivers)
    
    print(f"正在查询 {', '.join(target_drivers)} 最近30天的补货任务数据...")
    
    sql = f"""
    WITH time_diffs AS (
        SELECT
          a.*,
          b.outset_time AS '出发时间',
          b.arrive_time AS '到达时间',
          TIMESTAMPDIFF(MINUTE, b.outset_time, b.arrive_time) AS '行驶时间',
          TIMESTAMPDIFF(MINUTE, b.arrive_time, b.finish_shelve) +  a.walking_time_to_point AS '点位耗时',
          TIMESTAMPDIFF(MINUTE, b.outset_time, b.finish_shelve) +  a.walking_time_to_point AS '总耗时'
        FROM
          (
            SELECT
              id,
              batch_no,
              car_number,
              point_id,
              current_point AS '当前点位',
              previous_point AS '前一个点位',
              previous_point_finish_time AS '前一个点位完成补货(上架)时间',
              interval_minutes AS '间隔时长(当前点位开始分拣-补货完走回前一个点位)',
              distance_to_current_point AS '前一点位到当前点位的距离',
              navigation_time_to_current_point AS '导航到当前点位所需时间（分钟）',
              sorting_start_time,
              sorting_end_time AS '分拣完成时间',
              sorting_duration_minutes AS '分拣时长',
              walking_time_to_point,
              shelving_finish_time AS '点位完成上架时间',
              shelving_duration_minutes AS '点位上架时长',
              veg_box_count AS '盒菜数量',
              op_name
            FROM
              sorting_tasks
            WHERE
              sorting_start_time >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
              and sorting_start_time < CURDATE()
              AND op_name IN ('{drivers_sql_list}')
          ) a
          LEFT JOIN (
            SELECT
              batch_no,
              point_id,
              outset_time,
              arrive_time,
              finish_shelve,
              start_shelve
            FROM
              central_kitchen_car_task
            WHERE
              task_type = 4
              AND op_state = 3
          ) b ON a.batch_no = b.batch_no
          AND a.point_id = b.point_id
    )
    SELECT
      t.point_id,
      t.car_number,
      t.op_name,
      t.sorting_start_time,
      t.`盒菜数量` AS veg_box_count,
      t.`总耗时` AS point_total_time,
      t.`行驶时间` AS driving_time
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
    cols_to_fill = ['veg_box_count', 'point_total_time', 'driving_time']
    for col in cols_to_fill:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    # Define Shift Date
    df['sorting_start_time'] = pd.to_datetime(df['sorting_start_time'])
    
    # Custom shift logic:
    # Yee Meng: 21:00 - 09:00 (next day) -> shift date is the start date
    # Others: 20:00 - 08:00 (next day) -> shift date is the start date
    #
    # Generalizing:
    # If hour >= 12, it belongs to 'today's' evening shift.
    # If hour < 12, it belongs to 'yesterday's' evening shift.
    # This works for both 20:00 start and 21:00 start.
    
    df['shift_date'] = df['sorting_start_time'].apply(
        lambda x: x.date() if x.hour >= 12 else (x - pd.Timedelta(days=1)).date()
    )
    
    # Recalculate total duration using point_total_time if available
    df['total_time_minutes'] = df['point_total_time']
    
    # --- Aggregation by Driver and Shift ---
    print("\n正在按班次聚合分析...")
    
    shift_stats = df.groupby(['op_name', 'shift_date']).agg(
        points_count=('point_id', 'count'),
        total_veg_boxes=('veg_box_count', 'sum'),
        total_duration=('total_time_minutes', 'sum'),
        total_driving=('driving_time', 'sum')
    ).reset_index()
    
    # Convert duration to hours for display
    shift_stats['total_duration_hours'] = shift_stats['total_duration'] / 60
    shift_stats['total_driving_hours'] = shift_stats['total_driving'] / 60
    
    # Calculate Average Boxes per Point for each shift
    shift_stats['avg_boxes_per_point'] = shift_stats['total_veg_boxes'] / shift_stats['points_count']
    
    # --- Summary by Driver ---
    print("\n司机综合表现 (平均值):")
    driver_summary = shift_stats.groupby('op_name').agg(
        total_shifts=('shift_date', 'count'),
        avg_duration_hours=('total_duration_hours', 'mean'),
        avg_driving_hours=('total_driving_hours', 'mean'),
        avg_boxes_per_point=('avg_boxes_per_point', 'mean'),
        avg_points=('points_count', 'mean'),
        avg_total_boxes=('total_veg_boxes', 'mean')
    ).reset_index()
    
    # Sort by Duration desc
    driver_summary = driver_summary.sort_values('avg_duration_hours', ascending=False)
    
    # Formatting
    summary_cols = {
        'op_name': '司机',
        'total_shifts': '总班次',
        'avg_duration_hours': '班次平均总耗时(h)',
        'avg_driving_hours': '班次平均行驶(h)',
        'avg_boxes_per_point': '点位平均补货量(盒)',
        'avg_points': '班次平均点位数',
        'avg_total_boxes': '班次平均总补货量(盒)'
    }
    
    pd.options.display.float_format = '{:.2f}'.format
    print("\n" + "="*100)
    print("司机班次耗时与点位补货量分析")
    print("="*100)
    
    summary_df = driver_summary.rename(columns=summary_cols)
    print(summary_df.to_markdown(index=False))

    # Save Summary to CSV
    output_dir = os.path.dirname(os.path.abspath(__file__))
    summary_csv_path = os.path.join(output_dir, 'driver_shift_summary.csv')
    summary_df.to_csv(summary_csv_path, index=False, encoding='utf-8-sig')
    print(f"\n司机班次综合分析已保存至: {summary_csv_path}")
    
    # --- Detailed Shift Data ---
    print("\n" + "="*100)
    print("每日班次详情 (按日期降序)")
    print("="*100)
    
    # Formatting detailed table
    detail_cols = {
        'op_name': '司机',
        'shift_date': '班次日期',
        'total_duration_hours': '总耗时(h)',
        'total_driving_hours': '行驶(h)',
        'avg_boxes_per_point': '点均补货(盒)',
        'points_count': '点位数',
        'total_veg_boxes': '总补货(盒)'
    }
    
    # Sort by Date desc, then Driver
    shift_stats = shift_stats.sort_values(['shift_date', 'op_name'], ascending=[False, True])
    
    # Rounding for display
    display_stats = shift_stats.copy()
    float_cols = ['total_duration_hours', 'total_driving_hours', 'avg_boxes_per_point']
    for col in float_cols:
        display_stats[col] = display_stats[col].round(2)
        
    final_detail_df = display_stats[detail_cols.keys()].rename(columns=detail_cols)
    print(final_detail_df.to_markdown(index=False))
    
    # Save Details to CSV
    detail_csv_path = os.path.join(output_dir, 'driver_shift_details.csv')
    final_detail_df.to_csv(detail_csv_path, index=False, encoding='utf-8-sig')
    print(f"每日班次详情已保存至: {detail_csv_path}")

if __name__ == "__main__":
    analyze_focused_shift_boxes()

