#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补货量衰减路径细分分析：
  环节1: point_max_stock → point_forecast_amount 的损失
  环节2: 理想补货量 → point_replenish_amount 的损失
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
          a.point_history_5day_avg_cnt,
          a.point_forecast_amount,
          a.point_remain_stock,
          a.point_amount_real,
          a.point_amount_theoretical,
          a.point_replenish_amount,
          a.point_restock_type,
          a.point_is_full_restock,
          a.point_is_new,
          a.point_valid_shelf_cnt,
          a.point_sku_theoretical,
          a.point_sku_real,
          a.is_reduce_shelf,
          a.reduce_shelf_cnt,
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
    raw = query_data()
    df = pd.DataFrame(to_python(raw))
    df = df.sort_values('id', ascending=False).drop_duplicates(subset='req_task_id', keep='first')
    # 过滤 restock_type=0（无效记录）
    df = df[df['point_restock_type'] != 0].copy()
    print(f"去重+过滤后 {len(df)} 条有效记录\n")

    # 衍生指标
    df['ideal_replenish'] = (df['point_forecast_amount'] - df['point_remain_stock']).clip(lower=0)
    df['gap1_max_to_forecast'] = df['point_max_stock'] - df['point_forecast_amount']
    df['gap2_ideal_to_est'] = df['ideal_replenish'] - df['point_replenish_amount']

    # ================================================================
    # 环节1: point_max_stock → point_forecast_amount
    # ================================================================
    print("=" * 90)
    print("环节1: point_max_stock → point_forecast_amount 的损失分析")
    print("=" * 90)
    print(f"\n逻辑: forecast_amount = min(max_stock, coalesce(5day_forecast, history_avg, 50))")
    print(f"       新点位(开业≤7天): forecast_amount = max_stock")
    print(f"       全量补货点位: forecast_amount = max_stock")

    avg_max = df['point_max_stock'].mean()
    avg_fa = df['point_forecast_amount'].mean()
    avg_5day = df['point_forecast_5day_cnt'].mean()
    print(f"\n整体均值:")
    print(f"  point_max_stock:         {avg_max:.1f}")
    print(f"  point_forecast_5day_cnt: {avg_5day:.1f}")
    print(f"  point_forecast_amount:   {avg_fa:.1f}")
    print(f"  损失:                    {avg_max - avg_fa:.1f} ({(avg_max - avg_fa)/avg_max*100:.1f}%)")

    # --- 1a. 按 forecast 被限制的原因分类 ---
    print(f"\n### 1a. forecast_amount 被压低的原因分类")

    # 新点位 / 全量补货 → forecast = max_stock（无损失）
    df['is_full_or_new'] = (df['point_is_full_restock'] == 1) | (df['point_is_new'] == 1)
    full_new = df[df['is_full_or_new']]
    normal = df[~df['is_full_or_new']]

    print(f"\n  A) 新点位/全量补货（forecast = max_stock，无损失）:")
    print(f"     场次: {len(full_new)} ({len(full_new)/len(df)*100:.1f}%)")
    if len(full_new) > 0:
        print(f"     平均 max_stock: {full_new['point_max_stock'].mean():.1f}")
        print(f"     平均 forecast:  {full_new['point_forecast_amount'].mean():.1f}")

    print(f"\n  B) 普通点位（forecast = min(max_stock, 5day_prediction)）:")
    print(f"     场次: {len(normal)} ({len(normal)/len(df)*100:.1f}%)")
    print(f"     平均 max_stock: {normal['point_max_stock'].mean():.1f}")
    print(f"     平均 5day预测:  {normal['point_forecast_5day_cnt'].mean():.1f}")
    print(f"     平均 forecast:  {normal['point_forecast_amount'].mean():.1f}")

    # 在普通点位中，forecast 被 5day_prediction 限制 vs 被 max_stock 限制
    limited_by_pred = normal[normal['point_forecast_5day_cnt'] < normal['point_max_stock']]
    limited_by_max = normal[normal['point_forecast_5day_cnt'] >= normal['point_max_stock']]

    print(f"\n     B1) 5day预测 < max_stock（被预测压低）:")
    print(f"         场次: {len(limited_by_pred)} ({len(limited_by_pred)/len(normal)*100:.1f}% of 普通)")
    if len(limited_by_pred) > 0:
        print(f"         平均 max_stock: {limited_by_pred['point_max_stock'].mean():.1f}")
        print(f"         平均 5day预测:  {limited_by_pred['point_forecast_5day_cnt'].mean():.1f}")
        print(f"         平均 forecast:  {limited_by_pred['point_forecast_amount'].mean():.1f}")
        print(f"         平均损失:       {(limited_by_pred['point_max_stock'] - limited_by_pred['point_forecast_amount']).mean():.1f}")

    print(f"\n     B2) 5day预测 >= max_stock（被容量上限截断）:")
    print(f"         场次: {len(limited_by_max)} ({len(limited_by_max)/len(normal)*100:.1f}% of 普通)")
    if len(limited_by_max) > 0:
        print(f"         平均 max_stock: {limited_by_max['point_max_stock'].mean():.1f}")
        print(f"         平均 5day预测:  {limited_by_max['point_forecast_5day_cnt'].mean():.1f}")
        print(f"         平均 forecast:  {limited_by_max['point_forecast_amount'].mean():.1f}")
        print(f"         无损失（forecast = max_stock）")

    # --- 1b. 5day 预测被压低的程度分布 ---
    print(f"\n### 1b. 5day预测 vs max_stock 比率分布（仅普通点位）")
    normal_copy = normal.copy()
    normal_copy['pred_ratio'] = normal_copy['point_forecast_5day_cnt'] / normal_copy['point_max_stock']
    ratio_bins = [0, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 999]
    ratio_labels = ['<30%', '30-50%', '50-70%', '70-80%', '80-90%', '90-100%', '>100%']
    normal_copy['ratio_bin'] = pd.cut(normal_copy['pred_ratio'], bins=ratio_bins, labels=ratio_labels, right=True)

    ratio_dist = normal_copy.groupby('ratio_bin', observed=True).agg(
        场次=('req_task_id', 'count'),
        平均5day预测=('point_forecast_5day_cnt', 'mean'),
        平均max_stock=('point_max_stock', 'mean'),
        平均forecast=('point_forecast_amount', 'mean'),
        平均实际补货=('actual_replenish', 'mean'),
    ).round(1)
    ratio_dist['占比'] = (ratio_dist['场次'] / len(normal_copy) * 100).round(1).astype(str) + '%'
    print(ratio_dist.to_string())

    # --- 1c. 按 max_stock 水平分组看损失 ---
    print(f"\n### 1c. 按 max_stock 分组看损失")
    max_groups = normal.groupby('point_max_stock').agg(
        场次=('req_task_id', 'count'),
        平均5day预测=('point_forecast_5day_cnt', 'mean'),
        平均forecast=('point_forecast_amount', 'mean'),
        平均损失=('gap1_max_to_forecast', 'mean'),
        平均实际补货=('actual_replenish', 'mean'),
    ).round(1)
    print(max_groups.to_string())

    # --- 1d. 按点位维度看哪些点位预测偏低 ---
    print(f"\n### 1d. 预测偏低的点位 TOP15（按 forecast/max_stock 比率升序）")
    point_stats = normal.groupby('req_point_id').agg(
        场次=('req_task_id', 'count'),
        平均max_stock=('point_max_stock', 'mean'),
        平均5day预测=('point_forecast_5day_cnt', 'mean'),
        平均forecast=('point_forecast_amount', 'mean'),
        平均剩余库存=('point_remain_stock', 'mean'),
        平均实际补货=('actual_replenish', 'mean'),
    ).round(1)
    point_stats['预测/容量比'] = (point_stats['平均forecast'] / point_stats['平均max_stock']).round(2)
    point_stats = point_stats[point_stats['场次'] >= 3]  # 至少3场
    point_stats = point_stats.sort_values('预测/容量比').head(15)
    print(point_stats.to_string())

    # ================================================================
    # 环节2: 理想补货量 → point_replenish_amount
    # ================================================================
    print("\n\n" + "=" * 90)
    print("环节2: 理想补货量 → point_replenish_amount 的损失分析")
    print("=" * 90)

    # 理想补货量 = forecast_amount - remain_stock (>=0)
    # point_replenish_amount 考虑了：至少补20规则、货道配平、CK库存等

    avg_ideal = df['ideal_replenish'].mean()
    avg_est = df['point_replenish_amount'].mean()
    avg_theoretical = df['point_amount_theoretical'].mean()
    avg_real = df['point_amount_real'].mean()

    print(f"\n逻辑:")
    print(f"  理想补货量 = forecast_amount - remain_stock（不考虑任何约束）")
    print(f"  point_amount_theoretical = 理想情况算出来的补货量（考虑配比）")
    print(f"  point_amount_real = 考虑货道后算出来的补货量（货道配平后的目标库存）")
    print(f"  point_replenish_amount = point_amount_real - remain_stock（最终需要补的量）")

    print(f"\n整体均值:")
    print(f"  理想补货量(forecast-remain):           {avg_ideal:.1f}")
    print(f"  point_amount_theoretical(理论补货量):   {avg_theoretical:.1f}")
    print(f"  point_amount_real(货道配平后目标库存):  {avg_real:.1f}")
    print(f"  point_replenish_amount(预估补货量):     {avg_est:.1f}")
    print(f"  差异(理想 - 预估):                      {avg_ideal - avg_est:.1f}")

    # --- 2a. 差异方向分类 ---
    print(f"\n### 2a. 理想补货量 vs 预估补货量 差异分类")
    df['gap2'] = df['ideal_replenish'] - df['point_replenish_amount']

    much_more = df[df['gap2'] > 10]  # 理想 >> 预估（被削减了）
    slightly_more = df[(df['gap2'] > 0) & (df['gap2'] <= 10)]
    equal = df[df['gap2'] == 0]
    less = df[df['gap2'] < 0]  # 预估 > 理想（至少补20规则提升了）

    print(f"  理想 > 预估 超过10盒（被大幅削减）: {len(much_more)} 场 ({len(much_more)/len(df)*100:.1f}%)")
    print(f"  理想 > 预估 1-10盒（小幅削减）:     {len(slightly_more)} 场 ({len(slightly_more)/len(df)*100:.1f}%)")
    print(f"  理想 = 预估（完全一致）:             {len(equal)} 场 ({len(equal)/len(df)*100:.1f}%)")
    print(f"  理想 < 预估（被至少补20规则提升）:   {len(less)} 场 ({len(less)/len(df)*100:.1f}%)")

    # --- 2b. 被削减的场次分析 ---
    print(f"\n### 2b. 理想补货量被削减(gap>0)的原因拆解")
    cut_df = df[df['gap2'] > 0].copy()
    if len(cut_df) > 0:
        print(f"  共 {len(cut_df)} 场，平均被削减: {cut_df['gap2'].mean():.1f} 盒")

        # 货道裁剪
        shelf_reduced = cut_df[cut_df['is_reduce_shelf'] == 1]
        print(f"\n  a) 货道裁剪 (is_reduce_shelf=1):")
        print(f"     场次: {len(shelf_reduced)} ({len(shelf_reduced)/len(cut_df)*100:.1f}% of 被削减)")
        if len(shelf_reduced) > 0:
            print(f"     平均裁剪货道数: {shelf_reduced['reduce_shelf_cnt'].mean():.1f}")
            print(f"     平均理想补货: {shelf_reduced['ideal_replenish'].mean():.1f}, 平均预估补货: {shelf_reduced['point_replenish_amount'].mean():.1f}")

        # 无货道裁剪但仍被削减
        no_shelf_reduce = cut_df[cut_df['is_reduce_shelf'] == 0]
        print(f"\n  b) 无货道裁剪但仍被削减:")
        print(f"     场次: {len(no_shelf_reduce)} ({len(no_shelf_reduce)/len(cut_df)*100:.1f}% of 被削减)")
        if len(no_shelf_reduce) > 0:
            print(f"     平均理想补货: {no_shelf_reduce['ideal_replenish'].mean():.1f}, 平均预估补货: {no_shelf_reduce['point_replenish_amount'].mean():.1f}")
            print(f"     平均gap: {no_shelf_reduce['gap2'].mean():.1f}")
            print(f"     可能原因: 商品配比计算后按3的倍数取整、CK库存不足等")

    # --- 2c. 被提升的场次分析（至少补20规则）---
    print(f"\n### 2c. 预估 > 理想（至少补20规则生效）")
    boost_df = df[df['gap2'] < 0].copy()
    if len(boost_df) > 0:
        print(f"  共 {len(boost_df)} 场，平均被提升: {abs(boost_df['gap2'].mean()):.1f} 盒")
        print(f"  这些场次特征:")
        print(f"    平均 forecast_amount: {boost_df['point_forecast_amount'].mean():.1f}")
        print(f"    平均 remain_stock:    {boost_df['point_remain_stock'].mean():.1f}")
        print(f"    平均 理想补货量:      {boost_df['ideal_replenish'].mean():.1f}")
        print(f"    平均 预估补货量:      {boost_df['point_replenish_amount'].mean():.1f}")
        print(f"    说明: 这些点位理想补货量<20, 但至少补20规则将其提升到 remain+20 的水平")

    # --- 2d. 货道配平的影响 ---
    print(f"\n### 2d. 货道配平的整体影响")
    print(f"  point_amount_theoretical(理论):   {avg_theoretical:.1f}")
    print(f"  point_amount_real(配平后):         {avg_real:.1f}")
    print(f"  差异:                              {avg_real - avg_theoretical:.1f}")

    # 有货道裁剪的记录
    shelf_cut_all = df[df['is_reduce_shelf'] == 1]
    print(f"\n  有货道裁剪的场次: {len(shelf_cut_all)} ({len(shelf_cut_all)/len(df)*100:.1f}%)")
    if len(shelf_cut_all) > 0:
        print(f"    平均裁剪货道数:     {shelf_cut_all['reduce_shelf_cnt'].mean():.1f}")
        print(f"    平均有效货道数:     {shelf_cut_all['point_valid_shelf_cnt'].mean():.1f}")
        print(f"    平均理论SKU数:      {shelf_cut_all['point_sku_theoretical'].mean():.1f}")
        print(f"    平均实际SKU数:      {shelf_cut_all['point_sku_real'].mean():.1f}")
        print(f"    平均理想补货:       {shelf_cut_all['ideal_replenish'].mean():.1f}")
        print(f"    平均预估补货:       {shelf_cut_all['point_replenish_amount'].mean():.1f}")

    # --- 2e. 按 gap 大小看分布 ---
    print(f"\n### 2e. 理想-预估 差值分布")
    gap_bins = [-999, -20, -10, -5, 0, 5, 10, 20, 999]
    gap_labels = ['<-20', '-20~-10', '-10~-5', '-5~0', '0~5', '5~10', '10~20', '>20']
    df['gap2_bin'] = pd.cut(df['gap2'], bins=gap_bins, labels=gap_labels, right=True)
    gap_dist = df.groupby('gap2_bin', observed=True).agg(
        场次=('req_task_id', 'count'),
        平均理想补货=('ideal_replenish', 'mean'),
        平均预估补货=('point_replenish_amount', 'mean'),
        平均实际补货=('actual_replenish', 'mean'),
    ).round(1)
    gap_dist['占比'] = (gap_dist['场次'] / len(df) * 100).round(1).astype(str) + '%'
    print(gap_dist.to_string())

    # ================================================================
    # 综合量化：两个环节对目标57的影响
    # ================================================================
    print("\n\n" + "=" * 90)
    print("综合量化：两个环节对目标57的贡献潜力")
    print("=" * 90)

    avg_actual = df['actual_replenish'].mean()
    print(f"\n当前: 平均实际补货 {avg_actual:.1f}, 目标 57, 缺口 {57 - avg_actual:.1f}")

    # 模拟1: 如果 forecast_amount 全部提高到 max_stock
    df['sim1_ideal'] = (df['point_max_stock'] - df['point_remain_stock']).clip(lower=0)
    sim1_gain = df['sim1_ideal'].mean() - avg_ideal
    print(f"\n模拟1: 若 forecast_amount = max_stock（取消预测限制）")
    print(f"  理想补货量: {avg_ideal:.1f} → {df['sim1_ideal'].mean():.1f}, 增加 {sim1_gain:.1f}")
    print(f"  预期实际补货量: ~{avg_actual + sim1_gain:.1f}")

    # 模拟2: 如果剩余库存降低50%
    df['sim2_ideal'] = (df['point_forecast_amount'] - df['point_remain_stock'] * 0.5).clip(lower=0)
    sim2_gain = df['sim2_ideal'].mean() - avg_ideal
    print(f"\n模拟2: 若剩余库存降低50%")
    print(f"  理想补货量: {avg_ideal:.1f} → {df['sim2_ideal'].mean():.1f}, 增加 {sim2_gain:.1f}")

    # 模拟3: 如果 forecast 提高到 max_stock 的 85%（保守方案）
    df['sim3_forecast'] = np.maximum(df['point_forecast_amount'], df['point_max_stock'] * 0.85)
    df['sim3_ideal'] = (df['sim3_forecast'] - df['point_remain_stock']).clip(lower=0)
    sim3_gain = df['sim3_ideal'].mean() - avg_ideal
    print(f"\n模拟3: 若 forecast_amount 下限 = 85% * max_stock（温和方案）")
    print(f"  理想补货量: {avg_ideal:.1f} → {df['sim3_ideal'].mean():.1f}, 增加 {sim3_gain:.1f}")
    print(f"  预期实际补货量: ~{avg_actual + sim3_gain:.1f}")


if __name__ == '__main__':
    main()
