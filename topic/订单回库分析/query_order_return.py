#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订单回库查询工具
输入订单号，查询该订单下盒菜商品是否有回库信息（central_kitchen_commodity_again）。

数据通过 Metabase API 查询，逻辑参考 Dashboard 128（订单跟踪）：
- Card 1513：订单基础信息（关联分拣单号）
- Card 1514：回库商品信息
"""

import argparse
import json
import os
import urllib.request
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
load_dotenv(Path(__file__).parents[2] / '.env')

# Metabase 配置
METABASE_URL = os.environ.get('METABASE_URL', 'https://metabase.cookhere.com')
METABASE_API_KEY = os.environ['METABASE_API_KEY']
# DB=2: sg_readonly（central_kitchen_commodity_again 仅在此库上存在）
# DB=35: smart_cooker_sg 主库
DATABASE_ID = 2


def metabase_query(sql, database_id=DATABASE_ID):
    """
    通过 Metabase API 执行 SQL 查询

    Args:
        sql: SQL 查询语句
        database_id: Metabase 数据库 ID

    Returns:
        list[dict]: 查询结果列表
    """
    url = f"{METABASE_URL.rstrip('/')}/api/dataset"
    payload = json.dumps({
        'database': database_id,
        'type': 'native',
        'native': {'query': sql},
    }).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': METABASE_API_KEY,
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    cols = [c['name'] for c in data['data']['cols']]
    rows = data['data']['rows']
    return [dict(zip(cols, row)) for row in rows]


def get_order_products(order_no):
    """查询订单下的盒菜商品（commodity_type=1）"""
    sql = f"""
        SELECT
            op.order_no,
            op.commodity_id,
            op.commodity_name,
            op.save_container_id,
            op.save_shelf_id,
            op.create_time AS create_time
        FROM order_product op
        JOIN commodity c ON c.id = op.commodity_id
        WHERE op.order_no = '{order_no}'
          AND c.commodity_type = 1
    """
    return metabase_query(sql)


def get_order_picking_info(order_no):
    """
    查询订单中每个商品对应的分拣单号和点位信息。
    逻辑来自 Dashboard 128 Card 1513。
    """
    sql = f"""
        SELECT
            op.order_no            AS order_no,
            op.commodity_id        AS commodity_id,
            op.commodity_name      AS commodity_name,
            ids.point_id           AS point_id,
            p.point_name           AS point_name,
            op.save_container_id   AS cabinet_id,
            op.save_shelf_id       AS shelf_id,
            op.create_time         AS order_time,
            bak.day                AS shelving_date,
            bak.update_time        AS shelving_time,
            cct.batch_no           AS batch_no,
            cct.car_id             AS car_id,
            cct.op_name            AS op_name
        FROM order_product op
        JOIN inventory_device_shelf ids
            ON ids.cabinet_id = op.save_container_id
            AND ids.shelf_id = op.save_shelf_id
            AND ids.commodity_id = op.commodity_id
        JOIN point p
            ON p.id = ids.point_id
        JOIN inventory_device_shelf_bak bak
            ON bak.point_id = ids.point_id
            AND bak.cabinet_id = op.save_container_id
            AND bak.shelf_id = op.save_shelf_id
            AND bak.commodity_id = op.commodity_id
            AND bak.amount > 0
            AND bak.day <= DATE(op.create_time)
        JOIN inventory_device_shelf_bak bak_prev
            ON bak_prev.point_id = bak.point_id
            AND bak_prev.cabinet_id = bak.cabinet_id
            AND bak_prev.shelf_id = bak.shelf_id
            AND bak_prev.commodity_id = bak.commodity_id
            AND bak_prev.day = DATE_SUB(bak.day, INTERVAL 1 DAY)
            AND bak_prev.amount = 0
        JOIN central_kitchen_car_task cct
            ON cct.point_id = ids.point_id
            AND cct.batch_no REGEXP '^[0-9]{{10}}$'
            AND DATE(cct.create_time) = bak.day
        WHERE op.order_no = '{order_no}'
        ORDER BY op.commodity_id, bak.day DESC
    """
    return metabase_query(sql)


def get_return_records(batch_no, commodity_id):
    """
    查询指定分拣单号和商品ID的回库记录。
    逻辑来自 Dashboard 128 Card 1514。
    """
    sql = f"""
        SELECT *
        FROM central_kitchen_commodity_again
        WHERE next_picking_no = '{batch_no}'
          AND commodity_id = {commodity_id}
    """
    return metabase_query(sql)


def _fallback_picking_info(products):
    """
    降级方案：当 inventory_device_shelf 关联失败时（层架配置已变更），
    通过 inventory_device_shelf_bak 历史记录找到点位，再关联分拣单号。
    """
    results = []
    for p in products:
        order_date = str(p['create_time'])[:10]
        sql = f"""
            SELECT
                '{p['commodity_name']}' AS commodity_name,
                bak.commodity_id,
                bak.point_id,
                pt.point_name,
                bak.cabinet_id,
                bak.shelf_id,
                bak.day AS shelving_date,
                bak.update_time AS shelving_time,
                cct.batch_no,
                cct.car_id,
                cct.op_name
            FROM inventory_device_shelf_bak bak
            JOIN point pt ON pt.id = bak.point_id
            JOIN inventory_device_shelf_bak bak_prev
                ON bak_prev.point_id = bak.point_id
                AND bak_prev.cabinet_id = bak.cabinet_id
                AND bak_prev.shelf_id = bak.shelf_id
                AND bak_prev.commodity_id = bak.commodity_id
                AND bak_prev.day = DATE_SUB(bak.day, INTERVAL 1 DAY)
                AND bak_prev.amount = 0
            JOIN central_kitchen_car_task cct
                ON cct.point_id = bak.point_id
                AND cct.batch_no REGEXP '^[0-9]{{10}}$'
                AND DATE(cct.create_time) = bak.day
            WHERE bak.cabinet_id = {p['save_container_id']}
              AND bak.shelf_id = {p['save_shelf_id']}
              AND bak.commodity_id = {p['commodity_id']}
              AND bak.amount > 0
              AND bak.day <= '{order_date}'
            ORDER BY bak.day DESC
            LIMIT 1
        """
        rows = metabase_query(sql)
        results.extend(rows)
    return results


def query_order_return(order_no):
    """
    主查询逻辑：输入订单号，查询该订单盒菜是否有回库信息
    """
    # 第一步：查询订单商品
    print(f"\n查询订单 {order_no} 的商品列表...")
    products = get_order_products(order_no)
    if not products:
        print(f"未找到订单 {order_no}，请检查订单号是否正确")
        return

    print(f"找到 {len(products)} 个商品：")
    for p in products:
        print(f"  - {p['commodity_name']} (ID={p['commodity_id']})")

    # 第二步：关联查询分拣单号
    print(f"\n关联查询分拣配送信息...")
    picking_info = get_order_picking_info(order_no)

    if not picking_info:
        print("未能通过 inventory_device_shelf 关联（层架配置可能已变更）")
        print("尝试通过 inventory_device_shelf_bak 历史记录查找点位和分拣单...")
        picking_info = _fallback_picking_info(products)

    if not picking_info:
        print("未能关联到分拣配送信息，无法查询回库记录")
        return

    # 去重：每个 commodity_id 取最近的一条分拣记录
    seen = {}
    for info in picking_info:
        cid = info['commodity_id']
        if cid not in seen:
            seen[cid] = info

    print(f"成功关联 {len(seen)} 个商品的分拣信息：")
    for cid, info in seen.items():
        print(f"  - {info['commodity_name']} (ID={cid}) -> "
              f"点位:{info['point_name']} 分拣单:{info['batch_no']} "
              f"上架日期:{info['shelving_date']}")

    # 第三步：查询回库记录
    print(f"\n查询回库记录...")
    all_return_records = []

    for cid, info in seen.items():
        records = get_return_records(info['batch_no'], cid)
        if records:
            for r in records:
                r['commodity_name'] = info['commodity_name']
                r['point_name'] = info['point_name']
                r['batch_no_matched'] = info['batch_no']
            all_return_records.extend(records)

    # 第四步：展示结果
    if all_return_records:
        print(f"\n该订单有 {len(all_return_records)} 条回库记录：\n")
        df = pd.DataFrame(all_return_records)
        priority_cols = [
            'commodity_name', 'commodity_id', 'point_name', 'batch_no_matched',
            'next_picking_no', 'next_point_id', 'next_shelf_id',
            'qty', 'create_time',
        ]
        display_cols = [c for c in priority_cols if c in df.columns]
        other_cols = [c for c in df.columns if c not in display_cols]
        df = df[display_cols + other_cols]
        _print_df(df)
    else:
        print(f"\n该订单下所有商品均无回库记录")


def _print_df(df):
    """格式化打印 DataFrame"""
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 30)
    try:
        print(df.to_markdown(index=False))
    except ImportError:
        print(df.to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description='查询订单商品的回库信息')
    parser.add_argument('order_no', help='订单号')
    args = parser.parse_args()

    query_order_return(args.order_no)


if __name__ == '__main__':
    main()
