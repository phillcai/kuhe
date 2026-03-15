#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析所有理货员最近一周的补货效率
按班次聚合（每班次 = 当天20:00 至 次日08:00）
"""

import sys
import os
import pandas as pd

# 将 code 目录加入路径以导入 lib
sys.path.append(os.path.join(os.getcwd(), 'code'))

from lib import create_db_connection


def analyze_all_staff_weekly():
    print("正在连接数据库...")
    try:
        db = create_db_connection(mysql_database='smart_cooker_sg')
    except Exception as e:
        print(f"连接数据库失败: {e}")
        return

    print("正在查询所有理货员最近7天的补货任务数据...")

    sql = """
    WITH time_diffs AS (
        SELECT
          a.*,
          b.outset_time  AS `出发时间`,
          b.arrive_time  AS `到达时间`,
          TIMESTAMPDIFF(MINUTE, b.outset_time, b.arrive_time) AS `行驶时间`,
          TIMESTAMPDIFF(MINUTE, b.arrive_time, b.finish_shelve) + a.walking_time_to_point AS `点位耗时`,
          TIMESTAMPDIFF(MINUTE, b.outset_time, b.finish_shelve) + a.walking_time_to_point AS `总耗时`
        FROM (
            SELECT
              id,
              batch_no,
              car_number,
              point_id,
              current_point          AS `当前点位`,
              previous_point         AS `前一个点位`,
              sorting_start_time,
              sorting_end_time       AS `分拣完成时间`,
              sorting_duration_minutes,
              walking_time_to_point,
              shelving_finish_time   AS `点位完成上架时间`,
              shelving_duration_minutes,
              veg_box_count,
              drink_count,
              dessert_count,
              op_name
            FROM sorting_tasks
            WHERE sorting_start_time >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
              AND op_name IS NOT NULL
              AND op_name != ''
        ) a
        LEFT JOIN (
            SELECT
              batch_no,
              point_id,
              outset_time,
              arrive_time,
              finish_shelve,
              start_shelve
            FROM central_kitchen_car_task
            WHERE task_type = 4
              AND op_state = 3
        ) b ON a.batch_no = b.batch_no AND a.point_id = b.point_id
    )
    SELECT
      op_name,
      point_id,
      car_number,
      sorting_start_time,
      sorting_duration_minutes,
      shelving_duration_minutes,
      veg_box_count,
      drink_count,
      dessert_count,
      `总耗时`    AS point_total_time,
      `行驶时间`  AS driving_time
    FROM time_diffs
    ORDER BY sorting_start_time DESC
    """

    results = db.execute_query(sql)

    if not results:
        print("未查询到数据。")
        return

    df = pd.DataFrame(results)
    print(f"查询到 {len(df)} 条记录。")

    # ---------- 数据清洗 ----------
    num_cols = ['sorting_duration_minutes', 'shelving_duration_minutes',
                'veg_box_count', 'drink_count', 'dessert_count',
                'point_total_time', 'driving_time']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 过滤负数异常记录
    initial_count = len(df)
    df = df[(df['sorting_duration_minutes'] >= 0) & (df['shelving_duration_minutes'] >= 0)]
    if len(df) < initial_count:
        print(f"⚠️ 已过滤 {initial_count - len(df)} 条时间异常记录")

    # ---------- 计算衍生字段 ----------
    df['sorting_start_time'] = pd.to_datetime(df['sorting_start_time'])
    df['total_items'] = df['veg_box_count'] + df['drink_count'] + df['dessert_count']
    # 点位本身的分拣+上架时长（分钟）
    df['local_time_minutes'] = df['sorting_duration_minutes'] + df['shelving_duration_minutes']

    # 班次日期：hour>=12 算当天班次，否则算前一天班次
    df['shift_date'] = df['sorting_start_time'].apply(
        lambda x: x.date() if x.hour >= 12 else (x - pd.Timedelta(days=1)).date()
    )

    # ---------- 全周聚合 ----------
    print("\n正在按理货员汇总全周数据...")

    overall = df.groupby('op_name').agg(
        工作班次=('shift_date', 'nunique'),
        补货点位数=('point_id', 'count'),
        总盒菜=('veg_box_count', 'sum'),
        总饮料=('drink_count', 'sum'),
        总甜品=('dessert_count', 'sum'),
        总商品=('total_items', 'sum'),
        总分拣时长_分=('sorting_duration_minutes', 'sum'),
        总上架时长_分=('shelving_duration_minutes', 'sum'),
    ).reset_index()

    overall = overall[overall['补货点位数'] > 0].copy()

    # 避免除以零
    def safe_div(a, b, decimals=3):
        return (a / b.replace(0, float('nan'))).round(decimals)

    pd.options.display.float_format = '{:.3f}'.format
    output_dir = os.path.dirname(os.path.abspath(__file__))

    # ══════════════════════════════════════════════════
    # 维度一：盒菜分拣效率
    # 指标 = 盒菜数量 / 分拣时长
    # ══════════════════════════════════════════════════
    dim1 = overall.copy()
    dim1['盒菜分拣效率_盒每分'] = safe_div(dim1['总盒菜'], dim1['总分拣时长_分'])
    dim1['场均盒菜'] = (dim1['总盒菜'] / dim1['补货点位数']).round(1)
    dim1['场均分拣时长_分'] = (dim1['总分拣时长_分'] / dim1['补货点位数']).round(1)
    dim1 = dim1.sort_values('盒菜分拣效率_盒每分', ascending=False)

    d1_cols = {
        'op_name': '理货员',
        '工作班次': '班次数',
        '补货点位数': '点位数',
        '总盒菜': '总盒菜(盒)',
        '场均盒菜': '场均盒菜(盒)',
        '总分拣时长_分': '总分拣时长(分)',
        '场均分拣时长_分': '场均分拣时长(分)',
        '盒菜分拣效率_盒每分': '盒菜分拣效率(盒/分)',
    }
    print("\n" + "=" * 100)
    print("【维度一】盒菜分拣效率  =  盒菜数 ÷ 分拣时长")
    print("=" * 100)
    d1_out = dim1[list(d1_cols.keys())].rename(columns=d1_cols)
    print(d1_out.to_markdown(index=False))
    d1_out.to_csv(os.path.join(output_dir, 'dim1_veg_sorting_efficiency.csv'),
                  index=False, encoding='utf-8-sig')

    # ══════════════════════════════════════════════════
    # 维度二：盒菜上架效率
    # 指标 = 盒菜数量 / 上架时长
    # ══════════════════════════════════════════════════
    dim2 = overall.copy()
    dim2['盒菜上架效率_盒每分'] = safe_div(dim2['总盒菜'], dim2['总上架时长_分'])
    dim2['场均盒菜'] = (dim2['总盒菜'] / dim2['补货点位数']).round(1)
    dim2['场均上架时长_分'] = (dim2['总上架时长_分'] / dim2['补货点位数']).round(1)
    dim2 = dim2.sort_values('盒菜上架效率_盒每分', ascending=False)

    d2_cols = {
        'op_name': '理货员',
        '工作班次': '班次数',
        '补货点位数': '点位数',
        '总盒菜': '总盒菜(盒)',
        '场均盒菜': '场均盒菜(盒)',
        '总上架时长_分': '总上架时长(分)',
        '场均上架时长_分': '场均上架时长(分)',
        '盒菜上架效率_盒每分': '盒菜上架效率(盒/分)',
    }
    print("\n" + "=" * 100)
    print("【维度二】盒菜上架效率  =  盒菜数 ÷ 上架时长")
    print("=" * 100)
    d2_out = dim2[list(d2_cols.keys())].rename(columns=d2_cols)
    print(d2_out.to_markdown(index=False))
    d2_out.to_csv(os.path.join(output_dir, 'dim2_veg_shelving_efficiency.csv'),
                  index=False, encoding='utf-8-sig')

    # ══════════════════════════════════════════════════
    # 维度三：全品类（盒菜+饮料+甜品）分拣 & 上架效率
    # 分拣效率 = 总商品件数 / 分拣时长
    # 上架效率 = 总商品件数 / 上架时长
    # ══════════════════════════════════════════════════
    dim3 = overall.copy()
    dim3['全品类分拣效率_件每分'] = safe_div(dim3['总商品'], dim3['总分拣时长_分'])
    dim3['全品类上架效率_件每分'] = safe_div(dim3['总商品'], dim3['总上架时长_分'])
    dim3['场均商品'] = (dim3['总商品'] / dim3['补货点位数']).round(1)
    dim3['场均分拣时长_分'] = (dim3['总分拣时长_分'] / dim3['补货点位数']).round(1)
    dim3['场均上架时长_分'] = (dim3['总上架时长_分'] / dim3['补货点位数']).round(1)
    # 按分拣效率排序
    dim3 = dim3.sort_values('全品类分拣效率_件每分', ascending=False)

    d3_cols = {
        'op_name': '理货员',
        '工作班次': '班次数',
        '补货点位数': '点位数',
        '总商品': '总商品(件)',
        '总盒菜': '其中盒菜(盒)',
        '总饮料': '其中饮料(件)',
        '总甜品': '其中甜品(件)',
        '场均商品': '场均商品(件)',
        '场均分拣时长_分': '场均分拣(分)',
        '场均上架时长_分': '场均上架(分)',
        '全品类分拣效率_件每分': '全品类分拣效率(件/分)',
        '全品类上架效率_件每分': '全品类上架效率(件/分)',
    }
    print("\n" + "=" * 110)
    print("【维度三】全品类（盒菜+饮料+甜品）分拣 & 上架效率")
    print("  分拣效率 = 总商品件数 ÷ 分拣时长")
    print("  上架效率 = 总商品件数 ÷ 上架时长")
    print("=" * 110)
    d3_out = dim3[list(d3_cols.keys())].rename(columns=d3_cols)
    print(d3_out.to_markdown(index=False))
    d3_out.to_csv(os.path.join(output_dir, 'dim3_all_items_efficiency.csv'),
                  index=False, encoding='utf-8-sig')

    print("\n说明：")
    print("  • 分拣时长：从拿货到分拣完成所用时间")
    print("  • 上架时长：从到达点位到上架完成所用时间")
    print("  • 效率越高 = 单位时间处理商品数越多")


if __name__ == "__main__":
    analyze_all_staff_weekly()
