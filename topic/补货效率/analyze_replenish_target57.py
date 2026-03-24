#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析最近14天补货数据，诊断实际补货量达到57需要解决的问题
参考 card=861 口径，数据来源：point_commodity_fenjian_log + sorting_tasks
"""

import sys
import os

code_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../code'))
sys.path.insert(0, code_dir)

from lib import create_db_connection
import pandas as pd
import numpy as np
from decimal import Decimal


def query_data():
    """查询最近14天的补货数据"""
    db = create_db_connection(mysql_database='smart_cooker_sg')

    sql = """
        SELECT
          a.id,
          a.req_task_id,
          a.req_car_id,
          a.req_point_id,
          DATE(a.create_time) as dt,
          a.point_max_stock,
          a.point_forecast_5day_cnt,
          a.point_forecast_amount,
          a.point_remain_stock,
          a.point_amount_real,
          a.point_replenish_amount,
          a.point_restock_type,
          a.point_is_full_restock,
          a.point_is_new,
          s.veg_box_count as actual_replenish
        FROM
          point_commodity_fenjian_log a
          LEFT JOIN sorting_tasks s ON a.req_task_id = s.task_id
        WHERE
          a.status = 1
          AND a.req_task_id != 0
          AND a.create_time >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
          AND a.create_time < CURDATE()
        ORDER BY a.req_task_id, a.id DESC
    """

    results = db.execute_query(sql)
    print(f"查询到 {len(results)} 条原始记录")
    return results


def to_python(data):
    """转换数据类型"""
    converted = []
    for row in data:
        new_row = {}
        for k, v in row.items():
            if isinstance(v, Decimal):
                new_row[k] = float(v)
            elif isinstance(v, (np.integer, np.floating)):
                new_row[k] = v.item()
            else:
                new_row[k] = v
        converted.append(new_row)
    return converted


def main():
    TARGET = 57  # 目标实际补货量

    # 1. 取数
    raw = query_data()
    df = pd.DataFrame(to_python(raw))

    # 2. 按 req_task_id 去重，保留 id 最大的一条
    df = df.sort_values('id', ascending=False).drop_duplicates(subset='req_task_id', keep='first')
    print(f"去重后 {len(df)} 条记录")

    # 3. 计算衍生指标
    df['ideal_replenish'] = (df['point_forecast_amount'] - df['point_remain_stock']).clip(lower=0)
    df['gap_to_target'] = TARGET - df['actual_replenish']

    print("\n" + "=" * 80)
    print(f"最近14天补货数据分析 —— 目标：实际补货量达到 {TARGET}")
    print("=" * 80)

    # ============================================================
    # A. 整体概览
    # ============================================================
    print("\n## A. 整体概览（每日平均）")
    daily = df.groupby('dt').agg(
        补货场次=('req_task_id', 'count'),
        平均_point_max_stock=('point_max_stock', 'mean'),
        平均_5day预测=('point_forecast_5day_cnt', 'mean'),
        平均_forecast_amount=('point_forecast_amount', 'mean'),
        平均_剩余库存=('point_remain_stock', 'mean'),
        平均_理想补货量=('ideal_replenish', 'mean'),
        平均_预估补货量=('point_replenish_amount', 'mean'),
        平均_补货后库存=('point_amount_real', 'mean'),
        平均_实际补货量=('actual_replenish', 'mean'),
    ).round(1)

    print(daily.to_string())

    print(f"\n14天汇总均值:")
    print(f"  平均实际补货量:   {df['actual_replenish'].mean():.1f}")
    print(f"  中位实际补货量:   {df['actual_replenish'].median():.1f}")
    print(f"  平均理想补货量:   {df['ideal_replenish'].mean():.1f}")
    print(f"  平均预估补货量:   {df['point_replenish_amount'].mean():.1f}")
    print(f"  平均剩余库存:     {df['point_remain_stock'].mean():.1f}")
    print(f"  平均forecast_amount: {df['point_forecast_amount'].mean():.1f}")
    print(f"  平均point_max_stock: {df['point_max_stock'].mean():.1f}")
    print(f"  距离目标{TARGET}的缺口: {TARGET - df['actual_replenish'].mean():.1f}")

    # ============================================================
    # B. 补货量分布
    # ============================================================
    print("\n## B. 实际补货量分布")
    bins = [0, 20, 30, 40, 50, 57, 70, 90, 120]
    labels = ['0-20', '21-30', '31-40', '41-50', '51-57', '58-70', '71-90', '91+']
    df['actual_bin'] = pd.cut(df['actual_replenish'], bins=bins, labels=labels, right=True)
    dist = df['actual_bin'].value_counts().sort_index()
    pct = (dist / len(df) * 100).round(1)

    for b, c, p in zip(dist.index, dist.values, pct.values):
        marker = " <-- 目标线" if b == '51-57' else ""
        print(f"  {b:>8s}: {c:>4d} 场 ({p:>5.1f}%){marker}")

    below_target = (df['actual_replenish'] < TARGET).sum()
    above_target = (df['actual_replenish'] >= TARGET).sum()
    print(f"\n  < {TARGET}: {below_target} 场 ({below_target/len(df)*100:.1f}%)")
    print(f"  >= {TARGET}: {above_target} 场 ({above_target/len(df)*100:.1f}%)")

    # ============================================================
    # C. 各环节损耗分析（补货量从理想到实际的流失）
    # ============================================================
    print("\n## C. 各环节损耗分析（补货量从理想到实际的衰减路径）")

    # 路径：point_max_stock -> forecast_amount -> 理想补货量 -> 预估补货量 -> 实际补货量
    avg_max = df['point_max_stock'].mean()
    avg_forecast = df['point_forecast_amount'].mean()
    avg_remain = df['point_remain_stock'].mean()
    avg_ideal = df['ideal_replenish'].mean()
    avg_replenish_est = df['point_replenish_amount'].mean()
    avg_amount_real = df['point_amount_real'].mean()
    avg_actual = df['actual_replenish'].mean()

    print(f"  1) point_max_stock(容量上限):        {avg_max:.1f}")
    print(f"  2) point_forecast_amount(目标库存):   {avg_forecast:.1f}  (受预测/max_stock取min影响，损失: {avg_max - avg_forecast:.1f})")
    print(f"  3) point_remain_stock(当前库存):      {avg_remain:.1f}")
    print(f"  4) 理想补货量(2-3):                   {avg_ideal:.1f}")
    print(f"  5) point_replenish_amount(预估补货量): {avg_replenish_est:.1f}  (考虑至少补20等规则后，差异: {avg_replenish_est - avg_ideal:.1f})")
    print(f"  6) point_amount_real(补货后库存):      {avg_amount_real:.1f}")
    print(f"  7) actual_replenish(实际补货量):       {avg_actual:.1f}  (实际 vs 预估差距: {avg_actual - avg_replenish_est:.1f})")

    # ============================================================
    # D. 实际 < 预估 的原因分析
    # ============================================================
    print("\n## D. 实际补货 vs 预估补货对比")
    df['actual_vs_est'] = df['actual_replenish'] - df['point_replenish_amount']

    understock = df[df['actual_vs_est'] < -5]
    overstock = df[df['actual_vs_est'] > 5]
    normal = df[df['actual_vs_est'].between(-5, 5)]

    print(f"  实际 < 预估 (差>5盒): {len(understock)} 场 ({len(understock)/len(df)*100:.1f}%) — 平均差距: {understock['actual_vs_est'].mean():.1f}")
    print(f"  基本一致 (差±5盒):    {len(normal)} 场 ({len(normal)/len(df)*100:.1f}%)")
    print(f"  实际 > 预估 (差>5盒): {len(overstock)} 场 ({len(overstock)/len(df)*100:.1f}%) — 平均差距: {overstock['actual_vs_est'].mean():.1f}" if len(overstock) > 0 else "  实际 > 预估 (差>5盒): 0 场")

    # ============================================================
    # E. 按 restock_type 分析
    # ============================================================
    print("\n## E. 按补货类型(point_restock_type)分析")
    type_labels = {0: '未知', 1: '正常', 2: 'SKU不匹配', 3: '库存不足', 4: '低于最小量', 5: '部分缺货'}
    type_stats = df.groupby('point_restock_type').agg(
        场次=('req_task_id', 'count'),
        平均实际补货=('actual_replenish', 'mean'),
        平均预估补货=('point_replenish_amount', 'mean'),
        平均理想补货=('ideal_replenish', 'mean'),
    ).round(1)
    type_stats.index = type_stats.index.map(lambda x: f"{x}-{type_labels.get(x, '未知')}")
    print(type_stats.to_string())

    # ============================================================
    # F. 高剩余库存分析（剩余库存高 → 补货空间小）
    # ============================================================
    print("\n## F. 剩余库存分布（库存越高，补货空间越小）")
    remain_bins = [0, 10, 20, 30, 40, 50, 999]
    remain_labels = ['0-10', '11-20', '21-30', '31-40', '41-50', '51+']
    df['remain_bin'] = pd.cut(df['point_remain_stock'], bins=remain_bins, labels=remain_labels, right=True)
    remain_dist = df.groupby('remain_bin', observed=True).agg(
        场次=('req_task_id', 'count'),
        平均实际补货=('actual_replenish', 'mean'),
        平均理想补货=('ideal_replenish', 'mean'),
    ).round(1)
    remain_dist['占比'] = (remain_dist['场次'] / len(df) * 100).round(1).astype(str) + '%'
    print(remain_dist.to_string())

    # ============================================================
    # G. forecast_amount 分布（目标库存低 → 理想补货量小）
    # ============================================================
    print("\n## G. point_forecast_amount 分布（目标库存水平）")
    fa_bins = [0, 40, 60, 80, 96, 108, 999]
    fa_labels = ['0-40', '41-60', '61-80', '81-96', '97-108', '108+']
    df['fa_bin'] = pd.cut(df['point_forecast_amount'], bins=fa_bins, labels=fa_labels, right=True)
    fa_dist = df.groupby('fa_bin', observed=True).agg(
        场次=('req_task_id', 'count'),
        平均实际补货=('actual_replenish', 'mean'),
        平均forecast_amount=('point_forecast_amount', 'mean'),
        平均剩余库存=('point_remain_stock', 'mean'),
    ).round(1)
    fa_dist['占比'] = (fa_dist['场次'] / len(df) * 100).round(1).astype(str) + '%'
    print(fa_dist.to_string())

    # ============================================================
    # H. 按车辆分析（正常车 vs 虚拟车）
    # ============================================================
    print("\n## H. 按车辆类型分析")
    NORMAL_CAR_IDS = [2, 14, 15]
    df['car_type'] = df['req_car_id'].apply(lambda x: '正常车' if x in NORMAL_CAR_IDS else '虚拟车')
    car_stats = df.groupby('car_type').agg(
        场次=('req_task_id', 'count'),
        平均实际补货=('actual_replenish', 'mean'),
        平均预估补货=('point_replenish_amount', 'mean'),
        平均理想补货=('ideal_replenish', 'mean'),
        平均剩余库存=('point_remain_stock', 'mean'),
    ).round(1)
    print(car_stats.to_string())

    # ============================================================
    # I. 问题诊断总结
    # ============================================================
    print("\n" + "=" * 80)
    print(f"## 问题诊断总结：实际补货量达到 {TARGET} 需要解决的问题")
    print("=" * 80)

    gap = TARGET - avg_actual
    print(f"\n当前平均实际补货量: {avg_actual:.1f}, 目标: {TARGET}, 缺口: {gap:.1f}")

    # 问题1: 剩余库存高
    high_remain = df[df['point_remain_stock'] > 30]
    print(f"\n问题1: 剩余库存偏高")
    print(f"  - 剩余库存>30的场次: {len(high_remain)} 场 ({len(high_remain)/len(df)*100:.1f}%)")
    print(f"  - 这些场次平均剩余: {high_remain['point_remain_stock'].mean():.1f}, 平均实际补货: {high_remain['actual_replenish'].mean():.1f}")
    print(f"  - 如果剩余库存降到20以下，理论可增加补货量: {(high_remain['point_remain_stock'].mean() - 20) * len(high_remain) / len(df):.1f} 盒/场")

    # 问题2: forecast_amount 低于 max_stock
    low_forecast = df[df['point_forecast_amount'] < df['point_max_stock'] * 0.8]
    print(f"\n问题2: 目标库存(forecast_amount)远低于容量上限")
    print(f"  - forecast < 80% max_stock 的场次: {len(low_forecast)} 场 ({len(low_forecast)/len(df)*100:.1f}%)")
    print(f"  - 这些场次平均forecast: {low_forecast['point_forecast_amount'].mean():.1f}, 平均max_stock: {low_forecast['point_max_stock'].mean():.1f}")

    # 问题3: 实际低于预估
    shortfall = df[df['actual_replenish'] < df['point_replenish_amount'] - 5]
    print(f"\n问题3: 实际补货低于预估补货量")
    print(f"  - 实际 < 预估-5 的场次: {len(shortfall)} 场 ({len(shortfall)/len(df)*100:.1f}%)")
    if len(shortfall) > 0:
        print(f"  - 平均缺口: {(shortfall['point_replenish_amount'] - shortfall['actual_replenish']).mean():.1f} 盒")
        print(f"  - 主要原因: 车上库存不足、SKU不匹配、分拣遗漏等")

    # 问题4: 虚拟车效率
    if '虚拟车' in car_stats.index:
        vc = car_stats.loc['虚拟车']
        nc = car_stats.loc['正常车'] if '正常车' in car_stats.index else None
        if nc is not None:
            print(f"\n问题4: 虚拟车 vs 正常车效率差异")
            print(f"  - 正常车平均实际补货: {nc['平均实际补货']:.1f}")
            print(f"  - 虚拟车平均实际补货: {vc['平均实际补货']:.1f}")
            print(f"  - 差距: {nc['平均实际补货'] - vc['平均实际补货']:.1f}")


if __name__ == '__main__':
    main()
