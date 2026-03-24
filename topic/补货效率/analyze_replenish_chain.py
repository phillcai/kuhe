#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补货链路对比分析
===============

目的：
  分析"容量上限 → 实际补货量"全链路中各环节的损耗，定位补货量不足的瓶颈。
  按 5day 预测是否低于容量上限分为两组对比，揭示不同场景下的损耗差异。

数据口径（参考 Metabase card=861）：
  - 主表: point_commodity_fenjian_log（每次分拣请求时系统记录的点位级快照）
  - 关联: sorting_tasks（分拣任务表，含实际补货量 veg_box_count）
  - 关联条件: fenjian_log.req_task_id = sorting_tasks.task_id
  - 去重规则: 同一 req_task_id 有多条记录（系统重试），只保留 id 最大的一条
  - 过滤: status=1（成功）、req_task_id!=0、actual_replenish>0

链路定义：
  ① point_max_stock        — 点位物理容量上限（由柜体类型决定：108/96/72）
  ② point_forecast_5day_cnt — 未来 5 天预测销量（来自 report.t_point_hour_forecast_sale）
  ③ point_forecast_amount   — 目标库存 = min(①, ②)
                               新点位(开业≤7天)或全量补货点位: ③ = ①
                               其他: ③ = min(①, coalesce(②, 历史均值, 50))
  ④ point_remain_stock      — 补货前点位当前剩余库存
  ⑤ 理想补货量              — = max(③ - ④, 0)，不考虑任何约束的纯数学差值
  ⑥ point_replenish_amount  — 预估补货量，在 ⑤ 基础上经过以下规则调整：
                               - 商品配比权重分配（按 dish_score 比例拆分到各 SKU）
                               - 大点位(>60盒) SKU 数量按 3 的倍数取整
                               - 去到的点位至少补 20 盒（remain + 20 兜底）
                               - 受 CK 车上实际库存限制（某 SKU 车上没货则分配为 0）
  ⑦ actual_replenish        — 实际补货量 = sorting_tasks.veg_box_count（理货员实际上架数）

损耗归因：
  ①→③: 预测压低目标库存（5day预测 < max_stock 时产生）
  ④:    剩余库存占用（库存越高，可补空间越小）
  ⑤→⑥: 配比取整 / CK缺货 / 至少补20规则等系统规则损耗
  ⑥→⑦: 执行损耗（理货员实际操作与系统预估的偏差）

分组逻辑：
  - "被预测压低"组: point_forecast_5day_cnt < point_max_stock
    这些场次因为预测销量低于容量，forecast_amount 被预测值拉低
  - "无预测损失"组: point_forecast_5day_cnt >= point_max_stock
    这些场次预测销量已超容量，forecast_amount = max_stock，无预测损失

用法：
  uv run python topic/补货效率/analyze_replenish_chain.py
  修改 main() 中 query_data(days=14) 的参数可调整分析天数
"""

import sys
import os
from decimal import Decimal

code_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../code'))
sys.path.insert(0, code_dir)

from lib import create_db_connection


def query_data(days=14):
    """
    查询最近N天的补货数据，按 req_task_id 去重保留最新一条

    数据来源:
      - point_commodity_fenjian_log: 分拣算法每次为点位生成补货方案时写入的日志
        同一个 req_task_id 可能因系统重试产生多条记录，只保留 id 最大的一条
      - sorting_tasks: 分拣任务表，veg_box_count 为理货员实际上架的盒菜数量

    过滤条件:
      - status=1: 只取算法执行成功的记录
      - req_task_id!=0: 排除无关联任务的孤立记录
      - actual_replenish>0: 排除未实际补货的记录（如任务取消、空跑等）
    """
    db = create_db_connection(mysql_database='smart_cooker_sg')
    sql = f"""
        SELECT
          a.id,
          a.req_task_id,
          a.point_max_stock,
          a.point_forecast_5day_cnt,
          a.point_forecast_amount,
          a.point_remain_stock,
          a.point_amount_real,
          a.point_replenish_amount,
          s.veg_box_count AS actual_replenish
        FROM point_commodity_fenjian_log a
        LEFT JOIN sorting_tasks s ON a.req_task_id = s.task_id
        WHERE a.status = 1
          AND a.req_task_id != 0
          AND a.create_time >= DATE_SUB(CURDATE(), INTERVAL {days} DAY)
          AND a.create_time < CURDATE()
        ORDER BY a.req_task_id, a.id DESC
    """
    rows = db.execute_query(sql)
    print(f"查询到 {len(rows)} 条原始记录")

    # 按 req_task_id 去重，保留 id 最大的一条（最新的算法结果）
    seen = {}
    for r in rows:
        tid = r['req_task_id']
        if tid not in seen or r['id'] > seen[tid]['id']:
            seen[tid] = r
    data = list(seen.values())
    print(f"去重后 {len(data)} 条记录")

    # 过滤掉实际补货量为 0 或 NULL 的记录
    data = [r for r in data if r['actual_replenish'] and float(r['actual_replenish']) > 0]
    print(f"排除补货量=0后 {len(data)} 条有效记录")

    return data


def calc_chain(subset):
    """
    计算一组数据的链路各环节均值

    返回 dict:
      n              — 样本数
      max_stock      — ① 平均容量上限
      forecast_5day  — ② 平均5天预测销量
      forecast_amount — ③ 平均目标库存
      remain_stock   — ④ 平均剩余库存
      ideal          — ⑤ 平均理想补货量 = avg(max(③-④, 0))
      replenish_est  — ⑥ 平均预估补货量
      actual         — ⑦ 平均实际补货量
    """
    n = len(subset)
    if n == 0:
        return None

    def avg(field):
        return sum(
            float(r[field]) if isinstance(r[field], Decimal) else r[field]
            for r in subset
        ) / n

    max_stock = avg('point_max_stock')
    forecast_5day = avg('point_forecast_5day_cnt')
    forecast_amount = avg('point_forecast_amount')
    remain_stock = avg('point_remain_stock')
    # 理想补货量按逐条 clip(0) 后取均值，避免负值拉低
    ideal = sum(
        max(float(r['point_forecast_amount']) - float(r['point_remain_stock']), 0)
        for r in subset
    ) / n
    replenish_est = avg('point_replenish_amount')
    actual = avg('actual_replenish')

    return {
        'n': n,
        'max_stock': max_stock,
        'forecast_5day': forecast_5day,
        'forecast_amount': forecast_amount,
        'remain_stock': remain_stock,
        'ideal': ideal,
        'replenish_est': replenish_est,
        'actual': actual,
    }


def print_chain(label, chain, total_n):
    """打印单组链路数据，含各环节均值和环节间损失"""
    c = chain
    print(f"\n{'=' * 70}")
    print(f"{label}：{c['n']} 场（占总体 {c['n']/total_n*100:.1f}%）")
    print(f"{'=' * 70}")
    print(f"① point_max_stock（容量上限）:             {c['max_stock']:.1f}")
    print(f"② point_forecast_5day_cnt（5天预测销量）:   {c['forecast_5day']:.1f}")
    print(f"③ point_forecast_amount（目标库存）:        {c['forecast_amount']:.1f}"
          f"   = min(①,②)  损失: {c['max_stock'] - c['forecast_amount']:.1f}")
    print(f"④ point_remain_stock（当前剩余库存）:       {c['remain_stock']:.1f}")
    print(f"⑤ 理想补货量（③ - ④）:                     {c['ideal']:.1f}")
    print(f"⑥ point_replenish_amount（预估补货量）:     {c['replenish_est']:.1f}"
          f"   损失: {c['ideal'] - c['replenish_est']:.1f}")
    print(f"⑦ actual_replenish（实际补货量）:           {c['actual']:.1f}"
          f"   损失: {c['replenish_est'] - c['actual']:.1f}")


def main():
    data = query_data(days=14)
    total_n = len(data)

    # 分组：5day预测 < max_stock（被预测压低） vs >= max_stock（无预测损失）
    below = [r for r in data if float(r['point_forecast_5day_cnt']) < float(r['point_max_stock'])]
    above = [r for r in data if float(r['point_forecast_5day_cnt']) >= float(r['point_max_stock'])]

    chain_all = calc_chain(data)
    chain_below = calc_chain(below)
    chain_above = calc_chain(above)

    print_chain("整体", chain_all, total_n)
    print_chain("5day预测 < 容量上限（被预测压低）", chain_below, total_n)
    print_chain("5day预测 >= 容量上限（无预测损失）", chain_above, total_n)

    # 总损失归因（将 ①→⑦ 的总损失拆分到各环节）
    print(f"\n{'=' * 70}")
    print("总损失归因（整体）")
    print(f"{'=' * 70}")
    c = chain_all
    total_loss = c['max_stock'] - c['actual']
    loss_predict = c['max_stock'] - c['forecast_amount']  # ①→③
    loss_remain = c['remain_stock']                        # ④
    loss_rule = c['ideal'] - c['replenish_est']            # ⑤→⑥
    loss_exec = c['replenish_est'] - c['actual']           # ⑥→⑦

    print(f"  总损失 ①→⑦:           {total_loss:.1f}")
    print(f"    ①→③ 预测压低目标库存: {loss_predict:.1f} ({loss_predict/total_loss*100:.0f}%)")
    print(f"    ④   剩余库存占用:      {loss_remain:.1f} ({loss_remain/total_loss*100:.0f}%)")
    print(f"    ⑤→⑥ 配比/取整/规则:   {loss_rule:.1f} ({loss_rule/total_loss*100:.0f}%)")
    print(f"    ⑥→⑦ 执行损耗:         {loss_exec:.1f} ({loss_exec/total_loss*100:.0f}%)")


if __name__ == '__main__':
    main()
